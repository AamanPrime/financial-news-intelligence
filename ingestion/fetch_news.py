import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsArticle:
    def __init__(self, title: str, source: str, url: str, content: str, publication_date=None):
        self.title = title
        self.source = source
        self.url = url
        self.content = content
        self.publication_date = publication_date or datetime.utcnow()


class NewsFetcher:
    """Fetch financial news from multiple RSS feeds"""
    
    # Financial news RSS feeds
    FEEDS = {
        "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
        "yahoo_finance": "https://feeds.finance.yahoo.com/rss/2.0/headline",
        "cnbc": "https://feeds.cnbc.com/cnbc/financialnews/",
        "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
        "seeking_alpha": "https://seekingalpha.com/feed.xml"
    }
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    @classmethod
    def fetch_from_feeds(cls, limit: int = 50) -> List[NewsArticle]:
        """
        Fetch news articles from RSS feeds
        
        Args:
            limit: Maximum number of articles to fetch per feed
            
        Returns:
            List of NewsArticle objects
        """
        articles = []
        
        for source_name, feed_url in cls.FEEDS.items():
            try:
                logger.info(f"Fetching from {source_name}: {feed_url}")
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:limit]:
                    try:
                        title = entry.get("title", "")
                        url = entry.get("link", "")
                        published = entry.get("published", "")
                        
                        # Extract content from summary or description
                        content = entry.get("summary", "") or entry.get("description", "")
                        
                        # Parse publication date
                        pub_date = None
                        if published:
                            try:
                                from dateutil import parser
                                pub_date = parser.parse(published)
                            except:
                                pub_date = datetime.utcnow()
                        
                        if title and url and content:
                            article = NewsArticle(
                                title=title,
                                source=source_name,
                                url=url,
                                content=content,
                                publication_date=pub_date
                            )
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing entry from {source_name}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                continue
        
        logger.info(f"Total articles fetched: {len(articles)}")
        return articles

    @staticmethod
    def fetch_article_full_text(url: str) -> str:
        """
        Fetch full article text from URL using BeautifulSoup
        
        Args:
            url: Article URL
            
        Returns:
            Full article text
        """
        try:
            response = requests.get(url, headers=NewsFetcher.HEADERS, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator=" ")
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)
            
            return text[:5000]  # Limit to 5000 chars
        except Exception as e:
            logger.warning(f"Could not fetch full text from {url}: {e}")
            return ""
