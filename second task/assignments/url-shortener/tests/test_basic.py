import pytest
import json
from app.main import app
from app.models import url_store

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Clear the URL store before each test
        url_store._urls.clear()
        yield client

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'URL Shortener API'

def test_api_health(client):
    """Test the API health endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert 'message' in data

def test_shorten_url_success(client):
    """Test successful URL shortening."""
    test_url = "https://www.example.com/very/long/url"
    response = client.post('/api/shorten',
                          data=json.dumps({'url': test_url}),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    assert 'short_code' in data
    assert 'short_url' in data
    assert len(data['short_code']) == 6
    assert data['short_url'].endswith(data['short_code'])

def test_shorten_url_invalid_json(client):
    """Test URL shortening with invalid JSON."""
    response = client.post('/api/shorten',
                          data='invalid json',
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_shorten_url_missing_content_type(client):
    """Test URL shortening without JSON content type."""
    response = client.post('/api/shorten',
                          data='{"url": "https://example.com"}')
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Content-Type' in data['error']

def test_shorten_url_missing_url_field(client):
    """Test URL shortening without URL field."""
    response = client.post('/api/shorten',
                          data=json.dumps({'not_url': 'https://example.com'}),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'url' in data['error']

def test_shorten_url_invalid_url(client):
    """Test URL shortening with invalid URL."""
    invalid_urls = [
        'not-a-url',
        'ftp://example.com',
        'javascript:alert(1)',
        '',
        'http://',
        'https://'
    ]
    
    for invalid_url in invalid_urls:
        response = client.post('/api/shorten',
                              data=json.dumps({'url': invalid_url}),
                              content_type='application/json')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid URL' in data['error']

def test_redirect_success(client):
    """Test successful URL redirection."""
    # First, shorten a URL
    test_url = "https://www.example.com/test"
    response = client.post('/api/shorten',
                          data=json.dumps({'url': test_url}),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    short_code = data['short_code']
    
    # Then, test the redirect
    response = client.get(f'/{short_code}')
    assert response.status_code == 302
    assert response.location == test_url

def test_redirect_not_found(client):
    """Test redirect with non-existent short code."""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'not found' in data['error'].lower()

def test_redirect_invalid_format(client):
    """Test redirect with invalid short code format."""
    invalid_codes = ['abc', 'abcdefg', 'abc!@#']
    
    for invalid_code in invalid_codes:
        response = client.get(f'/{invalid_code}')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

def test_redirect_empty_string_edge_case(client):
    """Test that empty string routes to health check, not redirect handler."""
    # Empty string should route to health check (this is Flask's natural behavior)
    response = client.get('/')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_stats_success(client):
    """Test successful stats retrieval."""
    # First, shorten a URL
    test_url = "https://www.example.com/stats-test"
    response = client.post('/api/shorten',
                          data=json.dumps({'url': test_url}),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = response.get_json()
    short_code = data['short_code']
    
    # Get initial stats
    response = client.get(f'/api/stats/{short_code}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['url'] == test_url
    assert data['clicks'] == 0
    assert 'created_at' in data
    
    # Access the URL to increment clicks
    client.get(f'/{short_code}')
    
    # Check updated stats
    response = client.get(f'/api/stats/{short_code}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['clicks'] == 1

def test_stats_not_found(client):
    """Test stats for non-existent short code."""
    response = client.get('/api/stats/nonexistent')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert 'not found' in data['error'].lower()

def test_stats_invalid_format(client):
    """Test stats with invalid short code format."""
    response = client.get('/api/stats/abc')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data

def test_click_counting_accuracy(client):
    """Test that click counting is accurate with multiple accesses."""
    # Shorten a URL
    test_url = "https://www.example.com/click-test"
    response = client.post('/api/shorten',
                          data=json.dumps({'url': test_url}),
                          content_type='application/json')
    
    short_code = response.get_json()['short_code']
    
    # Access the URL multiple times
    access_count = 5
    for _ in range(access_count):
        response = client.get(f'/{short_code}')
        assert response.status_code == 302
    
    # Check final click count
    response = client.get(f'/api/stats/{short_code}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['clicks'] == access_count

def test_concurrent_url_shortening(client):
    """Test that multiple URLs can be shortened without conflicts."""
    test_urls = [
        "https://www.example1.com",
        "https://www.example2.com", 
        "https://www.example3.com",
        "https://www.example4.com",
        "https://www.example5.com"
    ]
    
    short_codes = []
    
    # Shorten multiple URLs
    for url in test_urls:
        response = client.post('/api/shorten',
                              data=json.dumps({'url': url}),
                              content_type='application/json')
        
        assert response.status_code == 201
        data = response.get_json()
        short_codes.append(data['short_code'])
    
    # Verify all short codes are unique
    assert len(short_codes) == len(set(short_codes))
    
    # Verify all URLs can be accessed
    for i, short_code in enumerate(short_codes):
        response = client.get(f'/{short_code}')
        assert response.status_code == 302
        assert response.location == test_urls[i]

def test_error_handling_edge_cases(client):
    """Test various edge cases and error conditions."""
    # Test empty request body
    response = client.post('/api/shorten',
                          data='',
                          content_type='application/json')
    assert response.status_code == 400
    
    # Test null URL
    response = client.post('/api/shorten',
                          data=json.dumps({'url': None}),
                          content_type='application/json')
    assert response.status_code == 400
    
    # Test very long URL (should still work)
    long_url = "https://www.example.com/" + "a" * 1000
    response = client.post('/api/shorten',
                          data=json.dumps({'url': long_url}),
                          content_type='application/json')
    assert response.status_code == 201

def test_url_validation_comprehensive(client):
    """Test comprehensive URL validation."""
    # Valid URLs that should work
    valid_urls = [
        "https://www.example.com",
        "http://example.com",
        "https://subdomain.example.com/path?query=value",
        "http://localhost:3000",
        "https://192.168.1.1:8080/path"
    ]
    
    for url in valid_urls:
        response = client.post('/api/shorten',
                              data=json.dumps({'url': url}),
                              content_type='application/json')
        assert response.status_code == 201, f"Valid URL failed: {url}"
    
    # Invalid URLs that should fail
    invalid_urls = [
        "not-a-url",
        "ftp://example.com",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "http://",
        "https://",
        "://example.com"
    ]
    
    for url in invalid_urls:
        response = client.post('/api/shorten',
                              data=json.dumps({'url': url}),
                              content_type='application/json')
        assert response.status_code == 400, f"Invalid URL should have failed: {url}"