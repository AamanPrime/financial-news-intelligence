from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from db.database import init_database, get_db
from db.models import Article, ExtractedEvent
from ingestion.fetch_news import NewsFetcher
from nlp.preprocess import TextPreprocessor
from nlp.extract_entities import EntityExtractor
from genai.llm_extraction import LLMExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial News Intelligence API",
    description="Extract structured financial intelligence from news articles",
    version="1.0.0"
)


# Pydantic Models for API responses
class KeyMetrics(BaseModel):
    revenue: Optional[str] = None
    profit: Optional[str] = None
    growth_percent: Optional[str] = None
    loss: Optional[str] = None


class ExtractedEventResponse(BaseModel):
    id: int
    article_id: int
    company: Optional[str]
    sector: Optional[str]
    event_type: Optional[str]
    sentiment: Optional[str]
    confidence_score: Optional[float]
    key_metrics: Optional[dict]
    extracted_at: datetime

    class Config:
        from_attributes = True


class ArticleResponse(BaseModel):
    id: int
    title: str
    source: str
    url: str
    publication_date: Optional[datetime]
    fetched_at: datetime
    processed: int
    extracted_events: List[ExtractedEventResponse] = []

    class Config:
        from_attributes = True


class EventSummary(BaseModel):
    total_events: int
    by_sentiment: dict
    by_event_type: dict
    top_companies: List[str]


# Initialize components
@app.on_event("startup")
async def startup_event():
    """Initialize database and log startup"""
    init_database()
    logger.info("Database initialized")


# API Endpoints

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow()}


@app.post("/ingest", tags=["Ingestion"])
async def ingest_news(db: Session = Depends(get_db)):
    """
    Fetch and ingest news articles from RSS feeds
    """
    try:
        fetcher = NewsFetcher()
        articles = fetcher.fetch_from_feeds(limit=10)
        
        saved_count = 0
        for article in articles:
            # Check if article already exists
            existing = db.query(Article).filter(Article.url == article.url).first()
            if not existing:
                db_article = Article(
                    title=article.title,
                    source=article.source,
                    url=article.url,
                    content=article.content,
                    publication_date=article.publication_date,
                    processed=0
                )
                db.add(db_article)
                saved_count += 1
        
        db.commit()
        logger.info(f"Ingested {saved_count} new articles")
        
        return {
            "status": "success",
            "total_fetched": len(articles),
            "saved": saved_count,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process", tags=["Processing"])
async def process_articles(limit: int = 10, db: Session = Depends(get_db)):
    """
    Process unprocessed articles through NLP and LLM extraction pipeline
    """
    try:
        # Get unprocessed articles
        articles = db.query(Article).filter(Article.processed == 0).limit(limit).all()
        
        if not articles:
            return {"status": "success", "processed": 0, "message": "No unprocessed articles"}
        
        entity_extractor = EntityExtractor()
        llm_extractor = LLMExtractor()
        processed_count = 0
        
        for article in articles:
            try:
                # Preprocess text
                chunks = TextPreprocessor.preprocess_pipeline(article.content)
                main_chunk = chunks[0] if chunks else article.content
                
                # Extract entities
                entities = entity_extractor.get_entity_summary(main_chunk)
                
                # Extract with LLM
                llm_result = llm_extractor.extract(main_chunk)
                
                if llm_result:
                    # Save extracted event
                    event = ExtractedEvent(
                        article_id=article.id,
                        company=llm_result.get("company"),
                        sector=llm_result.get("sector"),
                        event_type=llm_result.get("event_type"),
                        sentiment=llm_result.get("sentiment"),
                        confidence_score=llm_result.get("confidence_score"),
                        key_metrics=llm_result.get("key_metrics"),
                        extracted_entities=entities,
                        llm_extraction=llm_result
                    )
                    db.add(event)
                
                # Mark article as processed
                article.processed = 1
                db.commit()
                processed_count += 1
                logger.info(f"Processed article {article.id}: {article.title[:50]}")
                
            except Exception as e:
                logger.error(f"Error processing article {article.id}: {e}")
                article.processed = 1  # Mark as processed even on error
                db.commit()
                continue
        
        return {
            "status": "success",
            "processed": processed_count,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/events", response_model=List[ExtractedEventResponse], tags=["Queries"])
async def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    company: Optional[str] = None,
    sentiment: Optional[str] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get extracted events with optional filtering
    
    Query Parameters:
    - skip: Number of events to skip (pagination)
    - limit: Number of events to return (max 100)
    - company: Filter by company name
    - sentiment: Filter by sentiment (positive, neutral, negative)
    - event_type: Filter by event type
    """
    try:
        query = db.query(ExtractedEvent)
        
        # Apply filters
        if company:
            query = query.filter(ExtractedEvent.company.ilike(f"%{company}%"))
        if sentiment:
            query = query.filter(ExtractedEvent.sentiment == sentiment.lower())
        if event_type:
            query = query.filter(ExtractedEvent.event_type == event_type.lower())
        
        # Order by most recent first
        query = query.order_by(desc(ExtractedEvent.extracted_at))
        
        total = query.count()
        events = query.offset(skip).limit(limit).all()
        
        return events
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles", response_model=List[ArticleResponse], tags=["Queries"])
async def get_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    processed: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Get articles with optional filtering
    
    Query Parameters:
    - skip: Number of articles to skip (pagination)
    - limit: Number of articles to return (max 100)
    - source: Filter by source
    - processed: Filter by processing status (0=pending, 1=processed)
    """
    try:
        query = db.query(Article)
        
        if source:
            query = query.filter(Article.source == source)
        if processed is not None:
            query = query.filter(Article.processed == processed)
        
        query = query.order_by(desc(Article.fetched_at))
        
        total = query.count()
        articles = query.offset(skip).limit(limit).all()
        
        return articles
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles/{article_id}", response_model=ArticleResponse, tags=["Queries"])
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a specific article with its extracted events"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.get("/summary", response_model=EventSummary, tags=["Analytics"])
async def get_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics of extracted events
    """
    try:
        events = db.query(ExtractedEvent).all()
        
        # Count by sentiment
        by_sentiment = {}
        for sentiment in ["positive", "neutral", "negative"]:
            count = db.query(ExtractedEvent).filter(
                ExtractedEvent.sentiment == sentiment
            ).count()
            by_sentiment[sentiment] = count
        
        # Count by event type
        by_event_type = {}
        event_types = db.query(ExtractedEvent.event_type).distinct().all()
        for (et,) in event_types:
            if et:
                count = db.query(ExtractedEvent).filter(
                    ExtractedEvent.event_type == et
                ).count()
                by_event_type[et] = count
        
        # Top companies
        top_companies = []
        companies = db.query(ExtractedEvent.company).filter(
            ExtractedEvent.company.isnot(None)
        ).distinct().all()
        company_counts = []
        for (company,) in companies:
            count = db.query(ExtractedEvent).filter(
                ExtractedEvent.company == company
            ).count()
            company_counts.append((company, count))
        
        company_counts.sort(key=lambda x: x[1], reverse=True)
        top_companies = [c[0] for c in company_counts[:10]]
        
        return EventSummary(
            total_events=len(events),
            by_sentiment=by_sentiment,
            by_event_type=by_event_type,
            top_companies=top_companies
        )
    except Exception as e:
        logger.error(f"Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", tags=["Analytics"])
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics"""
    try:
        total_articles = db.query(Article).count()
        processed_articles = db.query(Article).filter(Article.processed == 1).count()
        total_events = db.query(ExtractedEvent).count()
        
        return {
            "total_articles": total_articles,
            "processed_articles": processed_articles,
            "pending_articles": total_articles - processed_articles,
            "total_events": total_events,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
