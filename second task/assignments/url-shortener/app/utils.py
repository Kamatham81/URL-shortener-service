import re
import string
import random
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_url(url):
    """
    Validate if the provided URL is valid and safe to redirect to.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    logger.info(f"Validating URL: {url}")
    
    if not url or not isinstance(url, str):
        logger.warning(f"Invalid URL type or empty: {url}")
        return False
    
    # Basic URL pattern validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        logger.warning(f"URL failed pattern validation: {url}")
        return False
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            logger.warning(f"URL missing scheme or netloc: {url}")
            return False
        
        # Additional safety checks
        if parsed.scheme not in ['http', 'https']:
            logger.warning(f"Invalid URL scheme: {parsed.scheme}")
            return False
            
        logger.info(f"URL validation successful: {url}")
        return True
        
    except Exception as e:
        logger.error(f"URL validation error for {url}: {str(e)}")
        return False

def generate_short_code(length=6, existing_codes=None):
    """
    Generate a random short code for URL shortening.
    
    Args:
        length (int): Length of the short code (default: 6)
        existing_codes (set): Set of existing codes to avoid collisions
        
    Returns:
        str: Generated short code
    """
    if existing_codes is None:
        existing_codes = set()
    
    # Use alphanumeric characters (excluding confusing ones like 0, O, l, I)
    chars = string.ascii_letters + string.digits
    safe_chars = ''.join(c for c in chars if c not in '0Ol1I')
    
    max_attempts = 100  # Prevent infinite loops
    attempt = 0
    
    while attempt < max_attempts:
        code = ''.join(random.choice(safe_chars) for _ in range(length))
        
        if code not in existing_codes:
            logger.info(f"Generated unique short code: {code} (attempt {attempt + 1})")
            return code
        
        attempt += 1
        logger.warning(f"Short code collision detected: {code} (attempt {attempt})")
    
    # If we can't generate a unique code, raise an exception
    logger.error(f"Failed to generate unique short code after {max_attempts} attempts")
    raise Exception("Unable to generate unique short code")

def is_valid_short_code(code):
    """
    Validate if a short code has the expected format.
    
    Args:
        code (str): The short code to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not code or not isinstance(code, str):
        return False
    
    # Check length and characters - be more lenient for user-provided codes
    # Only reject obviously invalid formats (too short, contains special chars)
    if len(code) < 3:  # Too short to be a reasonable short code
        return False
    
    # Check if contains only safe characters (alphanumeric)
    return code.isalnum()