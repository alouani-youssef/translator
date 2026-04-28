# 🚀 LLM JSON Translation & Context-Aware Pipeline

A high-performance **LLM-powered translation system** for structured JSON files with intelligent context enrichment, batching, caching, and parallel processing.

---

# 🧠 Overview

This project translates JSON content into a target language while preserving:

- SEO structure
- Tone and writing style
- Business context
- Glossary rules
- Named entities (brands, products, etc.)

It is designed for:

- SaaS localization pipelines
- Marketing content translation
- Large-scale JSON content migration
- SEO-optimized multilingual websites

---

# ⚙️ Core Features

## ✅ Context-Aware Translation

Each file is enriched with:

- Automatic summary (LLM-generated + cached)
- Content type detection (rule-based)
- Intent classification
- Keyword extraction
- Glossary enforcement
- Entity preservation

---

## ⚡ Batch Translation Engine

- Translates multiple strings per LLM call
- Reduces cost and latency significantly
- Maintains JSON structure integrity

---

## 🧠 Redis Caching Layer

Caches expensive operations:

- File summaries
- Translated strings
- (optional) full context

Example keys:

- summary:{file_name}
- tr:{text_hash}
- ctx:{file_hash}

---

## 🚀 Parallel Processing

- ThreadPoolExecutor-based execution
- Configurable worker count
- High throughput file processing

---

## 🤖 Multi-LLM Support (Ollama)

Supports multiple models:

- Translation model
- Summarization model
- (optional) validation / scoring models

---

# 🏗️ System Architecture

```
Input JSON Files
        ↓
File Handler (Thread Pool)
        ↓
Context Builder
   ├── Summary (LLM + cache)
   ├── Keywords (rule-based)
   ├── Intent detection
        ↓
Redis Cache Layer
        ↓
JSON Walker (string extraction)
        ↓
Batch Translator (Ollama LLM)
        ↓
Reconstruction Engine
        ↓
Output JSON Files
```

---

# 📦 Project Structure

```
lib/
│
├── main.py
├── config.py
│
├── file.py
├── json.py
├── translator.py
│
├── context/
│   ├── builder.py
│   ├── summary.py
│   ├── enrichment.py
│
├── redis_client.py
├── llm_client.py
```

---

# ⚙️ Configuration

Environment-based configuration via `Config`:

```python
INPUT_FOLDER = "./input"
OUTPUT_FOLDER = "./output"

TRANSLATION_LLM = "mistral"
SUMMARIZE_LLM = "llama3"

TARGET_LANGUAGE = "French"
SOURCE_LANGUAGE = "English"

MAX_WORKERS = 4

REDIS_URL = "redis://localhost:6379/0"

TRANSLATION_LLM_URL = "http://localhost:11434"
SUMMARIZE_LLM_URL = "http://localhost:11434"
```
