import json
import time
import numpy as np
from textblob import TextBlob
from flask import Flask, jsonify, request
import google.generativeai as genai
from cleantext import clean

# ── Config ────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static")
import os
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# ── JSON schema returned by the LLM ──────────────────────────────────────────
SENTIMENT_SCHEMA = {
    "label":         "POSITIVE | NEGATIVE | NEUTRAL",
    "polarity_score": "float between -1.0 and 1.0",
    "confidence":    "float between 0.0 and 1.0",
    "reasoning":     "one-sentence explanation"
}

SYSTEM_PROMPT = f"""
You are a sentiment analysis engine. For every tweet you receive, respond ONLY
with a valid JSON object that strictly follows this schema (no extra keys, no
markdown fences):

{json.dumps(SENTIMENT_SCHEMA, indent=2)}

Rules:
- label must be exactly one of: POSITIVE, NEGATIVE, NEUTRAL
- polarity_score: -1.0 (most negative) to +1.0 (most positive)
- confidence: how certain you are (0.0–1.0)
- reasoning: ≤ 20 words explaining your decision
"""

# ── Helper: TextBlob baseline ─────────────────────────────────────────────────
def textblob_sentiment(text: str) -> dict:
    blob = TextBlob(text)
    pol  = blob.sentiment.polarity
    subj = blob.sentiment.subjectivity
    if pol > 0.05:
        label = "POSITIVE"
    elif pol < -0.05:
        label = "NEGATIVE"
    else:
        label = "NEUTRAL"
    return {
        "label":          label,
        "polarity_score": round(pol,  4),
        "subjectivity":   round(subj, 4),
        "confidence":     round(subj, 4),   # subjectivity used as proxy confidence
        "reasoning":      "TextBlob lexicon-based polarity score."
    }

# ── Helper: Gemini LLM sentiment ─────────────────────────────────────────────
def llm_sentiment(text: str) -> dict:
    prompt   = f"{SYSTEM_PROMPT}\n\nTweet: {text}"
    try:
        response = gemini_model.generate_content(prompt)
        raw      = response.text.strip()
    except Exception as e:
        # Graceful fallback for API errors (quota, network, etc.)
        return {
            "label":          "NEUTRAL",
            "polarity_score": 0.0,
            "confidence":     0.0,
            "reasoning":      f"API error: {str(e)[:120]}"
        }

    
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
        # Validate required keys
        for key in ("label", "polarity_score", "confidence", "reasoning"):
            if key not in result:
                raise ValueError(f"Missing key: {key}")
        result["label"] = result["label"].upper()
        if result["label"] not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            result["label"] = "NEUTRAL"
        return result
    except (json.JSONDecodeError, ValueError) as e:
        # Graceful fallback
        return {
            "label":          "NEUTRAL",
            "polarity_score": 0.0,
            "confidence":     0.0,
            "reasoning":      f"Parse error: {str(e)}. Raw: {raw[:80]}"
        }

# ── Helper: compare both methods ─────────────────────────────────────────────
def compare_methods(text: str) -> dict:
    tb  = textblob_sentiment(text)
    llm = llm_sentiment(text)

    agree  = tb["label"] == llm["label"]
    delta  = round(abs(tb["polarity_score"] - llm["polarity_score"]), 4)

    return {
        "text":      text,
        "textblob":  tb,
        "llm":       llm,
        "agreement": agree,
        "polarity_delta": delta
    }

# ── Labeled mini-dataset for benchmarking ────────────────────────────────────
BENCHMARK_DATASET = [
    {"text": "I absolutely love this product, it changed my life!",   "ground_truth": "POSITIVE"},
    {"text": "This is the worst experience I have ever had.",          "ground_truth": "NEGATIVE"},
    {"text": "The package arrived today.",                             "ground_truth": "NEUTRAL"},
    {"text": "Fantastic service, will definitely recommend to others.","ground_truth": "POSITIVE"},
    {"text": "Terrible customer support, nobody helped me.",           "ground_truth": "NEGATIVE"},
    {"text": "The meeting is scheduled for 3 pm.",                     "ground_truth": "NEUTRAL"},
    {"text": "Such a beautiful day, feeling grateful!",                "ground_truth": "POSITIVE"},
    {"text": "I hate waiting in long queues for no reason.",           "ground_truth": "NEGATIVE"},
    {"text": "The report has been submitted.",                         "ground_truth": "NEUTRAL"},
    {"text": "Amazing performance by the team today!",                 "ground_truth": "POSITIVE"},
]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/analysis", methods=["POST"])
def tweet_analysis():
    """
    Original endpoint, upgraded:
    - Accepts tweet text directly (Twitter API optional)
    - Returns both TextBlob and LLM results side-by-side
    - Structured JSON output
    """
    if request.method != "POST":
        return jsonify({"error": "POST only"}), 405

    data  = request.get_json(silent=True) or {}
    texts = data.get("tweets", [])

    # Fallback: accept form data with a single 'ques' field (original interface)
    if not texts and request.form.get("ques"):
        texts = [request.form["ques"]]

    if not texts:
        return jsonify({"error": "Provide 'tweets' list in JSON body or 'ques' in form."}), 400

    results = []
    polarities_tb  = []
    polarities_llm = []

    for raw_text in texts:
        cleaned = clean(raw_text, no_emoji=True)
        comparison = compare_methods(cleaned)
        results.append(comparison)
        polarities_tb.append(comparison["textblob"]["polarity_score"])
        polarities_llm.append(comparison["llm"]["polarity_score"])

    # Aggregate
    def aggregate_label(scores):
        mean = np.mean(scores)
        if mean > 0.05:   return "POSITIVE"
        elif mean < -0.05: return "NEGATIVE"
        return "NEUTRAL"

    response = {
        "tweet_count":         len(results),
        "results":             results,
        "aggregate": {
            "textblob": {
                "mean_polarity":   round(float(np.mean(polarities_tb)), 4),
                "overall_label":   aggregate_label(polarities_tb)
            },
            "llm": {
                "mean_polarity":   round(float(np.mean(polarities_llm)), 4),
                "overall_label":   aggregate_label(polarities_llm)
            }
        }
    }
    return jsonify(response)


@app.route("/benchmark", methods=["GET"])
def benchmark():
    """
    Benchmarking endpoint:
    Runs both TextBlob and LLM on the labeled dataset,
    computes accuracy for each method, and returns a full report.
    """
    report = []
    tb_correct  = 0
    llm_correct = 0
    total       = len(BENCHMARK_DATASET)

    for item in BENCHMARK_DATASET:
        text         = item["text"]
        ground_truth = item["ground_truth"]

        tb_result  = textblob_sentiment(text)
        llm_result = llm_sentiment(text)

        tb_match  = tb_result["label"]  == ground_truth
        llm_match = llm_result["label"] == ground_truth
        tb_correct  += int(tb_match)
        llm_correct += int(llm_match)

        report.append({
            "text":         text,
            "ground_truth": ground_truth,
            "textblob": {
                "predicted": tb_result["label"],
                "correct":   tb_match,
                "polarity":  tb_result["polarity_score"],
                "confidence":tb_result["confidence"]
            },
            "llm": {
                "predicted": llm_result["label"],
                "correct":   llm_match,
                "polarity":  llm_result["polarity_score"],
                "confidence":llm_result["confidence"],
                "reasoning": llm_result["reasoning"]
            }
        })

        time.sleep(0.3)   # avoid Gemini rate limit on free tier

    summary = {
        "total_samples":    total,
        "textblob_accuracy": round(tb_correct  / total, 4),
        "llm_accuracy":      round(llm_correct / total, 4),
        "winner":            "LLM" if llm_correct >= tb_correct else "TextBlob",
        "agreement_rate":    round(
            sum(1 for r in report
                if r["textblob"]["predicted"] == r["llm"]["predicted"]) / total,
            4
        )
    }

    return jsonify({"summary": summary, "per_sample_report": report})


@app.route("/single", methods=["POST"])
def single_analysis():
    """
    Lightweight single-text endpoint.
    Body: { "text": "your tweet here" }
    Returns full structured comparison.
    """
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Provide 'text' field in JSON body."}), 400

    cleaned = clean(text, no_emoji=True)
    result  = compare_methods(cleaned)
    return jsonify(result)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": "gemini-2.0-flash", "baseline": "textblob"})


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5555, use_reloader=False)
