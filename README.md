# Dual-Engine Twitter Sentiment Analysis

A dual-engine sentiment analysis API that compares a **TextBlob lexicon baseline** against a **Gemini 2.0 Flash LLM** with structured JSON output, per-sample confidence scoring, and a built-in benchmarking endpoint.

---

## What this project does and why

Most sentiment analysis tools give you a single answer with no way to evaluate how reliable it is. This project runs two fundamentally different engines on the same input — a classical lexicon-based approach (TextBlob) and an LLM with reasoning (Gemini 2.0 Flash) — and returns both results side-by-side along with whether they agree and how far apart their scores are.

The `/benchmark` endpoint then runs both engines against a labeled ground-truth dataset and reports accuracy, agreement rate, and per-sample correctness for each method. This turns a simple sentiment classifier into a small evaluation framework — the same design pattern used in LLM benchmarking pipelines.

```
Input text
    │
    ├──► TextBlob engine ──► { label, polarity_score, confidence, reasoning }
    │                                         │
    └──► Gemini LLM engine ──► { label, polarity_score, confidence, reasoning }
                                              │
                          compare_methods() ──┘
                                │
                    { agreement: bool, polarity_delta: float,
                      textblob: {...}, llm: {...} }
```

The `confidence` field means different things per engine: for TextBlob it is the subjectivity score (a proxy for how opinion-laden the text is); for Gemini it is the model's own self-reported certainty, grounded in its reasoning field.

---

## Features

| Feature | Description |
|---|---|
| Dual sentiment engines | TextBlob (lexicon) + Gemini LLM side-by-side |
| Structured JSON output | Every response follows a consistent schema with label, polarity, confidence, and reasoning |
| Method comparison | `agreement` flag and `polarity_delta` show where the two engines diverge |
| Benchmarking endpoint | `/benchmark` runs both engines on a labeled dataset and reports accuracy per method |
| Graceful error handling | Falls back cleanly when the Gemini API is unavailable or quota is exceeded |
| Text cleaning | Automatic emoji removal and text normalisation via `clean-text` |

---

## Output schema (per tweet)

```json
{
  "text": "i love this product!",
  "textblob": {
    "label": "POSITIVE",
    "polarity_score": 0.625,
    "confidence": 0.6,
    "reasoning": "TextBlob lexicon-based polarity score."
  },
  "llm": {
    "label": "POSITIVE",
    "polarity_score": 0.85,
    "confidence": 0.95,
    "reasoning": "Tweet expresses clear enthusiasm and satisfaction."
  },
  "agreement": true,
  "polarity_delta": 0.225
}
```

---

## Benchmark output schema

```json
{
  "summary": {
    "total_samples": 10,
    "textblob_accuracy": 0.7,
    "llm_accuracy": 0.9,
    "winner": "LLM",
    "agreement_rate": 0.8
  },
  "per_sample_report": [
    {
      "text": "I absolutely love this product...",
      "ground_truth": "POSITIVE",
      "textblob": { "predicted": "POSITIVE", "correct": true, "polarity": 0.625, "confidence": 0.6 },
      "llm":      { "predicted": "POSITIVE", "correct": true, "polarity": 0.85,  "confidence": 0.95, "reasoning": "..." }
    }
  ]
}
```

---

## Setup

### 1. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Gemini API key
Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey), then:
```bash
export GEMINI_API_KEY="your_key_here"
```

### 4. Run the app
```bash
python3 app.py
```

The server starts at **http://127.0.0.1:5555**.

---

## Endpoints

### `POST /single`
Analyse a single piece of text:
```bash
curl -X POST http://127.0.0.1:5555/single \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this so much!"}'
```

### `POST /analysis`
Analyse a batch of tweets. Returns per-tweet comparison + aggregate labels from both methods:
```bash
curl -X POST http://127.0.0.1:5555/analysis \
  -H "Content-Type: application/json" \
  -d '{"tweets": ["Great product!", "Terrible service."]}'
```

### `GET /benchmark`
Runs both engines on a 10-sample labeled dataset and returns accuracy, agreement rate, and per-sample correctness:
```bash
curl http://127.0.0.1:5555/benchmark
```

### `GET /health`
Returns status and model info:
```bash
curl http://127.0.0.1:5555/health
```

---

## Dependencies

- **Flask** — web framework
- **TextBlob** — lexicon-based sentiment analysis baseline
- **Google Generative AI** — Gemini 2.0 Flash for LLM-based sentiment
- **NumPy** — aggregate polarity calculations
- **clean-text** — text preprocessing and emoji removal
- **Tweepy** — Twitter API client (optional, for future live tweet fetching)

---

## Notes

- The app uses **Gemini 2.0 Flash** (`gemini-2.0-flash`). The free tier has daily rate limits — if exceeded, LLM results fall back gracefully with an error message while TextBlob results continue working.
- On macOS, port 5000 is occupied by AirPlay Receiver. The app runs on **port 5555** by default.
- Always use a virtual environment (`.venv`) to avoid dependency conflicts.

---

## Relevance to AI Systems Research Topics

| Topic | How this project demonstrates it |
|---|---|
| **SignalBench** | `/benchmark` endpoint computes per-method accuracy against a labeled dataset; confidence scoring and per-sample correctness flags mirror structured evaluation pipelines |
| **GreenQuery** | LLM-based classification with schema-constrained JSON responses; structured output with `label`, `polarity_score`, `confidence`, and `reasoning` fields enforced via system prompt |
| **NanoCaesura** | Dual-engine NLP comparison pipeline; divergence analysis (`polarity_delta`, `agreement`) between a classical and neural method on identical inputs |
