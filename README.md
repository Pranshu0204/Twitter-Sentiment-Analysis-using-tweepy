# Twitter Sentiment Analysis

A dual-engine sentiment analysis API that compares a **TextBlob lexicon baseline** against a **Gemini 2.0 Flash LLM** with structured JSON output and a built-in benchmarking endpoint.

## Features

| Feature | Description |
|---|---|
| Dual sentiment engines | TextBlob (lexicon) + Gemini LLM side-by-side |
| Structured JSON output | Every response follows a consistent schema with label, polarity, confidence, and reasoning |
| Benchmarking | Built-in `/benchmark` endpoint with accuracy metrics on a labeled dataset |
| Graceful error handling | Falls back cleanly when the Gemini API is unavailable or quota is exceeded |
| Text cleaning | Automatic emoji removal and text normalization via `clean-text` |

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

## Endpoints

### `POST /single`

Analyse a single piece of text:

```bash
curl -X POST http://127.0.0.1:5555/single \
  -H "Content-Type: application/json" \
  -d '{"text": "I love this so much!"}'
```

### `POST /analysis`

Analyse a batch of tweets:

```bash
curl -X POST http://127.0.0.1:5555/analysis \
  -H "Content-Type: application/json" \
  -d '{"tweets": ["Great product!", "Terrible service."]}'
```

Returns per-tweet comparison + aggregate labels from both methods.

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

## Dependencies

- **Flask** — web framework
- **TextBlob** — lexicon-based sentiment analysis baseline
- **Google Generative AI** — Gemini 2.0 Flash for LLM-based sentiment
- **NumPy** — aggregate polarity calculations
- **clean-text** — text preprocessing and emoji removal
- **Tweepy** — Twitter API client (optional, for future live tweet fetching)

## Notes

- The app uses **Gemini 2.0 Flash** (`gemini-2.0-flash`). The free tier has daily rate limits — if exceeded, the LLM results will gracefully fall back with an error message while TextBlob results continue working.
- On macOS, port 5000 is used by AirPlay Receiver. The app runs on **port 5555** by default.
- Always use a virtual environment (`.venv`) to avoid Python version conflicts.
