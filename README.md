# Financial News Intelligence Pipeline

## Overview

**Financial News Intelligence Pipeline** is a production-ready Python system that extracts structured financial intelligence from unstructured news articles using NLP and Generative AI. It automates the process of identifying key financial events, companies, sentiment, and metrics from financial news sources.

This system mimics how financial intelligence firms (like S&P Global, Refinitiv, Bloomberg) process vast volumes of news to extract actionable insights for traders, analysts, and investment firms.

---

## Problem Statement

Financial professionals need to monitor news from hundreds of sources daily to identify:
- **Key Company Events**: Earnings reports, mergers, acquisitions, lawsuits, regulatory changes
- **Market Sentiment**: Positive/negative developments affecting stock prices
- **Financial Metrics**: Revenue, profit, growth rates, losses mentioned in articles
- **Industry Trends**: Sector-wide patterns and risks

**Manual processing is inefficient.** This system automates the entire pipeline:
1. Fetch news from multiple RSS feeds
2. Preprocess and normalize text
3. Extract entities using NLP (spaCy)
4. Leverage Generative AI to structure unstructured data
5. Store in queryable database
6. Expose via REST API

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEWS SOURCES (RSS FEEDS)                     │
│  Reuters | Yahoo Finance | CNBC | Bloomberg | Seeking Alpha    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  NEWS INGESTION      │
          │  (fetch_news.py)     │
          │  - Parse RSS feeds   │
          │  - Extract metadata  │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ TEXT PREPROCESSING   │
          │ (preprocess.py)      │
          │ - Normalize text     │
          │ - Remove noise       │
          │ - Chunk long texts   │
          └──────────┬───────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
  ┌─────────────────┐   ┌──────────────────┐
  │ NLP EXTRACTION  │   │ LLM EXTRACTION   │
  │ (spaCy NER)     │   │ (Gemini/OpenAI)  │
  │ - Organizations │   │ - Structured JSON│
  │ - Monetary      │   │ - Event type     │
  │ - Dates         │   │ - Sentiment      │
  │ - Percentages   │   │ - Metrics        │
  └────────┬────────┘   └────────┬─────────┘
           │                     │
           └──────────┬──────────┘
                      │
                      ▼
          ┌──────────────────────┐
          │   DATABASE STORAGE   │
          │  (PostgreSQL + ORM)  │
          │  - Articles table    │
          │  - Events table      │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │    REST API LAYER    │
          │   (FastAPI)          │
          │  - /ingest           │
          │  - /process          │
          │  - /events           │
          │  - /summary          │
          └──────────────────────┘
```

---

## Tech Stack Justification

| Component | Technology | Why |
|-----------|-----------|-----|
| **Web Framework** | FastAPI | Async, auto-docs, production-ready, minimal overhead |
| **NLP Library** | spaCy | Industry-standard, fast, pre-trained models for NER |
| **LLM** | Google Gemini / OpenAI | Structured extraction, JSON compliance, reliable APIs |
| **Database** | PostgreSQL | ACID compliance, JSON support, scalable |
| **ORM** | SQLAlchemy | Type-safe, flexible, industry-standard |
| **Text Parsing** | BeautifulSoup + feedparser | Robust HTML/RSS parsing |
| **Async/Retry** | Tenacity | Production-grade retry logic with exponential backoff |

---

## Project Structure

```
financial-news-intelligence/
├── ingestion/
│   └── fetch_news.py           # RSS feed fetching
├── nlp/
│   ├── preprocess.py           # Text normalization, chunking
│   └── extract_entities.py     # spaCy NER extraction
├── genai/
│   └── llm_extraction.py       # LLM-based structured extraction
├── db/
│   ├── models.py               # SQLAlchemy ORM models
│   └── database.py             # Connection management
├── api/
│   └── main.py                 # FastAPI application
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

---

## Database Schema

### Articles Table
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source VARCHAR(200) NOT NULL,
    url VARCHAR(500) UNIQUE NOT NULL,
    publication_date TIMESTAMP,
    content TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    processed INTEGER DEFAULT 0  -- 0=pending, 1=processed
);
```

### Extracted Events Table
```sql
CREATE TABLE extracted_events (
    id INTEGER PRIMARY KEY,
    article_id INTEGER FOREIGN KEY,
    company VARCHAR(300),
    sector VARCHAR(200),
    event_type VARCHAR(100),     -- earnings, merger, acquisition, etc.
    sentiment VARCHAR(50),        -- positive, neutral, negative
    confidence_score FLOAT,
    key_metrics JSONB,            -- {revenue, profit, growth, loss}
    extracted_entities JSONB,     -- spaCy NER results
    llm_extraction JSONB,         -- Raw LLM response
    extracted_at TIMESTAMP DEFAULT NOW()
);
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- PostgreSQL 12+
- pip or conda

### 1. Clone Repository
```bash
cd financial-news-intelligence
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your credentials:
# - DATABASE_URL: PostgreSQL connection string
# - GENAI_API_KEY: Your Gemini or OpenAI API key
# - GENAI_MODEL: gemini-pro or gpt-3.5-turbo
```

### 5. Create PostgreSQL Database
```bash
createdb financial_news
# Or use your preferred PostgreSQL client
```

### 6. Initialize Database (Automatic on app startup)
Tables will be created automatically when the app starts.

---

## Running the Application

### Start FastAPI Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Usage

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Ingest News Articles
```bash
curl -X POST http://localhost:8000/ingest
```

**Response**:
```json
{
  "status": "success",
  "total_fetched": 45,
  "saved": 12,
  "timestamp": "2024-01-16T10:30:00"
}
```

### 3. Process Articles (Extract Intelligence)
```bash
curl -X POST "http://localhost:8000/process?limit=10"
```

**Response**:
```json
{
  "status": "success",
  "processed": 8,
  "timestamp": "2024-01-16T10:35:00"
}
```

### 4. Query Events by Company
```bash
curl "http://localhost:8000/events?company=Apple&sentiment=positive"
```

**Response**:
```json
[
  {
    "id": 1,
    "article_id": 5,
    "company": "Apple Inc",
    "sector": "Technology",
    "event_type": "earnings",
    "sentiment": "positive",
    "confidence_score": 0.92,
    "key_metrics": {
      "revenue": "$123.5B",
      "growth_percent": "8.2%"
    },
    "extracted_at": "2024-01-16T10:35:00"
  }
]
```

### 5. Query Events by Sentiment
```bash
curl "http://localhost:8000/events?sentiment=negative&limit=10"
```

### 6. Get Event Type Summary
```bash
curl http://localhost:8000/events?event_type=merger
```

### 7. Get System Statistics
```bash
curl http://localhost:8000/stats
```

**Response**:
```json
{
  "total_articles": 150,
  "processed_articles": 120,
  "pending_articles": 30,
  "total_events": 110,
  "timestamp": "2024-01-16T10:40:00"
}
```

### 8. Get Analytics Summary
```bash
curl http://localhost:8000/summary
```

**Response**:
```json
{
  "total_events": 110,
  "by_sentiment": {
    "positive": 45,
    "neutral": 40,
    "negative": 25
  },
  "by_event_type": {
    "earnings": 35,
    "merger": 20,
    "acquisition": 15,
    "regulation": 12,
    "lawsuit": 8,
    "expansion": 10,
    "downgrade": 6,
    "upgrade": 4
  },
  "top_companies": [
    "Apple Inc",
    "Microsoft Corporation",
    "Tesla Inc",
    "Amazon.com Inc",
    "Nvidia Corporation"
  ]
}
```

### 9. Get Articles
```bash
curl "http://localhost:8000/articles?source=reuters_business&processed=1"
```

### 10. Get Specific Article
```bash
curl http://localhost:8000/articles/5
```

---

## Sample Input & Output

### Input: Raw News Article
```
Title: "Apple Reports Record Q4 Earnings, Stock Surges"

Source: reuters_business

Content: "Apple Inc. reported record quarterly earnings of $123.5 billion, 
up 8.2% from last year. CEO Tim Cook announced expansion plans into 
the Indian market. The company faces potential regulatory scrutiny in 
Europe but remains bullish on iPhone 15 sales."
```

### LLM Output (Structured Extraction)
```json
{
  "company": "Apple Inc",
  "sector": "Technology",
  "event_type": "earnings",
  "sentiment": "positive",
  "confidence_score": 0.95,
  "key_metrics": {
    "revenue": "$123.5B",
    "growth_percent": "8.2%"
  },
  "summary": "Apple reports record earnings with 8.2% YoY growth and announces Indian expansion."
}
```

### spaCy NER Output (Entity Extraction)
```json
{
  "entities": {
    "organizations": [
      {
        "text": "Apple Inc",
        "label": "ORG",
        "start": 0,
        "end": 9
      }
    ],
    "money": [
      {
        "text": "$123.5 billion",
        "label": "MONEY",
        "start": 40,
        "end": 54
      }
    ],
    "percent": [
      {
        "text": "8.2%",
        "label": "PERCENT",
        "start": 60,
        "end": 64
      }
    ]
  },
  "metrics": {
    "monetary_values": ["$123.5 billion"],
    "percentages": ["8.2%"]
  }
}
```

---

## Production Considerations

### 1. Scalability
- Use async FastAPI for concurrent request handling
- Implement job queues (Celery + Redis) for background processing
- Use PostgreSQL connection pooling (PgBouncer)

### 2. Monitoring & Logging
```python
# Logs all extraction pipeline steps
# Monitor with tools like ELK, Datadog, or CloudWatch
```

### 3. API Authentication
Add token-based authentication:
```python
from fastapi.security import HTTPBearer
security = HTTPBearer()
```

### 4. Rate Limiting
```bash
pip install slowapi
# Prevent abuse of LLM API calls
```

### 5. Caching
Use Redis for frequently accessed queries
```bash
pip install redis
```

### 6. Error Handling
- LLM API failures → graceful degradation
- Database connection issues → retry with backoff (implemented)
- Invalid JSON responses → logged and skipped

---

## Portfolio & Interview Talking Points

### Why This Project Stands Out:

1. **Real-world Problem**: Financial intelligence extraction is used by firms managing $100M+ in assets
2. **Full Stack**: Data ingestion → NLP → Generative AI → Database → API
3. **Production Quality**: Error handling, retries, logging, validation
4. **Scalable Design**: Async operations, modular architecture, ORM patterns
5. **Multiple AI Models**: Supports both Gemini and OpenAI (easy to extend)
6. **Structured Output**: Enforced JSON schema with validation

### Interview Discussion Topics:

- **Trade-offs**: Why spaCy + LLM (NER precision + structured extraction flexibility)
- **Scaling**: How to handle 10,000 articles/day (distributed processing, async queues)
- **Reliability**: Retry logic, error handling for API failures
- **Business Value**: Real-time detection of market-moving events
- **Future Enhancements**: Multi-language support, sentiment scoring refinement, custom NER models

---

## Troubleshooting

### PostgreSQL Connection Error
```
Error: could not connect to server
Solution: Ensure PostgreSQL is running and DATABASE_URL is correct
```

### spaCy Model Not Found
```
Solution: python -m spacy download en_core_web_sm
```

### LLM API Key Issues
```
Solution: Check GENAI_API_KEY in .env and ensure account has API access
```

### JSON Parsing Errors from LLM
```
Solution: LLMExtractor includes fallback logic; check logs for response format
```

---

## Contributing

To extend this system:

1. **Add new RSS feeds**: Update `NewsFetcher.FEEDS`
2. **Custom NER models**: Replace spacy model in `EntityExtractor`
3. **New LLM models**: Add to `LLMExtractor._init_*` methods
4. **Additional metrics**: Extend `ExtractedEvent` model and extraction prompt

---

## License

MIT License - Use freely for portfolio, commercial, and educational purposes.

---

## Contact & Support

For questions or improvements, refer to the code documentation or open an issue.

**Built with:** Python 3.10+ | FastAPI | spaCy | PostgreSQL | Gemini/OpenAI

---

*Last Updated: December 2025*
