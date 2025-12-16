from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/financial_news")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
    url = Column(String(500), unique=True, nullable=False)
    publication_date = Column(DateTime, nullable=True)
    content = Column(Text, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Integer, default=0)  # 0 = pending, 1 = processed

    # Relationship
    extracted_events = relationship("ExtractedEvent", back_populates="article", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}', source='{self.source}')>"


class ExtractedEvent(Base):
    __tablename__ = "extracted_events"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    company = Column(String(300), nullable=True, index=True)
    sector = Column(String(200), nullable=True)
    event_type = Column(String(100), nullable=True, index=True)  # earnings, merger, acquisition, lawsuit, downgrade, expansion, regulation
    sentiment = Column(String(50), nullable=True)  # positive, neutral, negative
    confidence_score = Column(Float, nullable=True)
    key_metrics = Column(JSON, nullable=True)  # {"revenue": "1.2B", "growth": "5.3%"}
    extracted_entities = Column(JSON, nullable=True)  # spaCy NER results
    llm_extraction = Column(JSON, nullable=True)  # Raw LLM response
    extracted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    article = relationship("Article", back_populates="extracted_events")

    def __repr__(self):
        return f"<ExtractedEvent(id={self.id}, company='{self.company}', event_type='{self.event_type}')>"


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
