from flask import Flask, jsonify, request, redirect
import logging
from .models import url_store
from .utils import validate_url, generate_short_code, is_valid_short_code

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "URL Shortener API"
    })

@app.route('/api/health')
def api_health():
    return jsonify({
        "status": "ok",
        "message": "URL Shortener API is running"
    })

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    """
    Shorten a URL endpoint.
    
    Expected JSON payload:
    {
        "url": "https://www.example.com/very/long/url"
    }
    
    Returns:
    {
        "short_code": "abc123",
        "short_url": "http://localhost:5000/abc123"
    }
    """
    logger.info("POST /api/shorten - Request received")
    
    try:
        # Validate request content type
        if not request.is_json:
            logger.warning("Request is not JSON")
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400
        
        try:
            data = request.get_json()
        except Exception as e:
            logger.warning(f"Invalid JSON in request: {str(e)}")
            return jsonify({
                "error": "Invalid JSON format"
            }), 400
        
        # Validate request data
        if not data:
            logger.warning("Empty request body")
            return jsonify({
                "error": "Request body is required"
            }), 400
        
        if 'url' not in data:
            logger.warning("Missing 'url' field in request")
            return jsonify({
                "error": "Missing 'url' field in request body"
            }), 400
        
        original_url = data['url']
        
        # Validate URL
        if not validate_url(original_url):
            logger.warning(f"Invalid URL provided: {original_url}")
            return jsonify({
                "error": "Invalid URL format"
            }), 400
        
        # Generate short code with collision handling
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                existing_codes = url_store.get_existing_codes()
                short_code = generate_short_code(existing_codes=existing_codes)
                
                # Try to add the URL mapping
                if url_store.add_url(short_code, original_url):
                    short_url = f"{request.host_url}{short_code}"
                    
                    logger.info(f"Successfully shortened URL: {original_url} -> {short_code}")
                    return jsonify({
                        "short_code": short_code,
                        "short_url": short_url
                    }), 201
                
                # If add_url returns False, there was a collision, try again
                logger.warning(f"Short code collision on attempt {attempt + 1}")
                
            except Exception as e:
                logger.error(f"Error generating short code on attempt {attempt + 1}: {str(e)}")
                continue
        
        # If we get here, we failed to generate a unique code
        logger.error("Failed to generate unique short code after multiple attempts")
        return jsonify({
            "error": "Unable to generate short code, please try again"
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error in shorten_url: {str(e)}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.route('/<path:short_code>')
def redirect_url(short_code):
    """
    Redirect to the original URL using the short code.
    
    Args:
        short_code (str): The short code to redirect
        
    Returns:
        Redirect response or 404 if not found
    """
    logger.info(f"GET /{short_code} - Redirect request received")
    
    try:
        # Handle empty string case explicitly
        if not short_code or short_code.strip() == '':
            logger.warning("Empty short code provided")
            return jsonify({
                "error": "Invalid short code format"
            }), 404
        
        # Get the original URL first
        original_url = url_store.get_url(short_code)
        
        if not original_url:
            # Check if it's a format issue or just not found
            if not is_valid_short_code(short_code):
                logger.warning(f"Invalid short code format: {short_code}")
                return jsonify({
                    "error": "Invalid short code format"
                }), 404
            else:
                logger.warning(f"Short code not found: {short_code}")
                return jsonify({
                    "error": "Short code not found"
                }), 404
        
        # Increment click count
        if not url_store.increment_clicks(short_code):
            logger.error(f"Failed to increment clicks for {short_code}")
            # Don't fail the redirect, just log the error
        
        logger.info(f"Redirecting {short_code} to {original_url}")
        return redirect(original_url, code=302)
        
    except Exception as e:
        logger.error(f"Unexpected error in redirect_url: {str(e)}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.route('/api/stats/<short_code>')
def get_stats(short_code):
    """
    Get analytics for a short code.
    
    Args:
        short_code (str): The short code to get stats for
        
    Returns:
    {
        "url": "https://www.example.com/very/long/url",
        "clicks": 5,
        "created_at": "2024-01-01T10:00:00"
    }
    """
    logger.info(f"GET /api/stats/{short_code} - Stats request received")
    
    try:
        # Handle empty string case explicitly
        if not short_code or short_code.strip() == '':
            logger.warning("Empty short code provided for stats")
            return jsonify({
                "error": "Invalid short code format"
            }), 404
        
        # Get stats first
        stats = url_store.get_stats(short_code)
        
        if not stats:
            # Check if it's a format issue or just not found
            if not is_valid_short_code(short_code):
                logger.warning(f"Invalid short code format: {short_code}")
                return jsonify({
                    "error": "Invalid short code format"
                }), 404
            else:
                logger.warning(f"Stats requested for non-existent code: {short_code}")
                return jsonify({
                    "error": "Short code not found"
                }), 404
        
        # Return stats (excluding last_accessed for API cleanliness)
        response_data = {
            "url": stats['url'],
            "clicks": stats['clicks'],
            "created_at": stats['created_at']
        }
        
        logger.info(f"Returning stats for {short_code}: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_stats: {str(e)}")
        return jsonify({
            "error": "Internal server error"
        }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({
        "error": "Method not allowed"
    }), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)