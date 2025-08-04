import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class URLStore:
    """
    Thread-safe in-memory storage for URL mappings and analytics.
    """
    
    def __init__(self):
        self._urls = {}  # short_code -> url_data
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        logger.info("URLStore initialized")
    
    def add_url(self, short_code: str, original_url: str) -> bool:
        """
        Add a new URL mapping.
        
        Args:
            short_code (str): The short code
            original_url (str): The original URL
            
        Returns:
            bool: True if added successfully, False if code already exists
        """
        with self._lock:
            if short_code in self._urls:
                logger.warning(f"Attempted to add existing short code: {short_code}")
                return False
            
            url_data = {
                'url': original_url,
                'clicks': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_accessed': None
            }
            
            self._urls[short_code] = url_data
            logger.info(f"Added URL mapping: {short_code} -> {original_url}")
            return True
    
    def get_url(self, short_code: str) -> Optional[str]:
        """
        Get the original URL for a short code.
        
        Args:
            short_code (str): The short code
            
        Returns:
            str: The original URL, or None if not found
        """
        with self._lock:
            url_data = self._urls.get(short_code)
            if url_data:
                logger.info(f"Retrieved URL for {short_code}: {url_data['url']}")
                return url_data['url']
            
            logger.warning(f"Short code not found: {short_code}")
            return None
    
    def increment_clicks(self, short_code: str) -> bool:
        """
        Increment the click count for a short code.
        
        Args:
            short_code (str): The short code
            
        Returns:
            bool: True if incremented, False if code doesn't exist
        """
        with self._lock:
            if short_code not in self._urls:
                logger.warning(f"Attempted to increment clicks for non-existent code: {short_code}")
                return False
            
            self._urls[short_code]['clicks'] += 1
            self._urls[short_code]['last_accessed'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Incremented clicks for {short_code}: {self._urls[short_code]['clicks']}")
            return True
    
    def get_stats(self, short_code: str) -> Optional[Dict]:
        """
        Get analytics data for a short code.
        
        Args:
            short_code (str): The short code
            
        Returns:
            dict: Analytics data, or None if not found
        """
        with self._lock:
            url_data = self._urls.get(short_code)
            if url_data:
                stats = {
                    'url': url_data['url'],
                    'clicks': url_data['clicks'],
                    'created_at': url_data['created_at'],
                    'last_accessed': url_data['last_accessed']
                }
                logger.info(f"Retrieved stats for {short_code}: {stats}")
                return stats
            
            logger.warning(f"Stats requested for non-existent code: {short_code}")
            return None
    
    def get_existing_codes(self) -> set:
        """
        Get all existing short codes.
        
        Returns:
            set: Set of existing short codes
        """
        with self._lock:
            codes = set(self._urls.keys())
            logger.debug(f"Retrieved {len(codes)} existing codes")
            return codes
    
    def get_total_urls(self) -> int:
        """
        Get the total number of stored URLs.
        
        Returns:
            int: Total number of URLs
        """
        with self._lock:
            count = len(self._urls)
            logger.debug(f"Total URLs stored: {count}")
            return count

# Global instance - in a production environment, this would be replaced
# with a proper database or distributed cache
url_store = URLStore()