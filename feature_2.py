from flask import Flask, request, jsonify, make_response
from functools import wraps
import time
import hashlib
import os
import jwt
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')

# Plan pricing configuration
PLANS = {
    'free': {
        'requests_per_minute': 10,
        'requests_per_day': 100,
        'api_keys': 1,
        'price': 0
    },
    'starter': {
        'requests_per_minute': 60,
        'requests_per_day': 1000,
        'api_keys': 5,
        'price': 9.99
    },
    'professional': {
        'requests_per_minute': 300,
        'requests_per_day': 10000,
        'api_keys': 20,
        'price': 29.99
    },
    'enterprise': {
        'requests_per_minute': 1000,
        'requests_per_day': 100000,
        'api_keys': 100,
        'price': 99.99
    }
}

# In-memory storage for API keys and rate limiting
api_keys = {}
rate_limits = {}

def generate_api_key(user_id, plan='free'):
    """Generate a new API key for a user"""
    timestamp = datetime.now().isoformat()
    raw_key = f"{user_id}:{plan}:{timestamp}:{os.urandom(16).hex()}"
    api_key = hashlib.sha256(raw_key.encode()).hexdigest()[:32]
    
    api_keys[api_key] = {
        'user_id': user_id,
        'plan': plan,
        'created_at': datetime.now(),
        'last_used': None,
        'is_active': True
    }
    
    return api_key

def validate_api_key(api_key):
    """Validate if API key exists and is active"""
    if api_key not in api_keys:
        return False
    if not api_keys[api_key]['is_active']:
        return False
    return True

def get_plan_limits(api_key):
    """Get rate limits for the plan associated with API key"""
    if api_key not in api_keys:
        return None
    plan_name = api_keys[api_key]['plan']
    return PLANS.get(plan_name)

def check_rate_limit(api_key):
    """Check if the request is within rate limits"""
    if api_key not in rate_limits:
        rate_limits[api_key] = {
            'minute': [],
            'day': []
        }
    
    current_time = time.time()
    limits = rate_limits[api_key]
    plan_limits = get_plan_limits(api_key)
    
    if not plan_limits:
        return False, "Invalid plan configuration"
    
    # Clean old entries
    limits['minute'] = [t for t in limits['minute'] if current_time - t < 60]
    limits['day'] = [t for t in limits['day'] if current_time - t < 86400]
    
    # Check limits
    if len(limits['minute']) >= plan_limits['requests_per_minute']:
        return False, f"Rate limit exceeded. Max {plan_limits['requests_per_minute']} requests per minute"
    
    if len(limits['day']) >= plan_limits['requests_per_day']:
        return False, f"Daily limit exceeded. Max {plan_limits['requests_per_day']} requests per day"
    
    # Update rate limits
    limits['minute'].append(current_time)
    limits['day'].append(current_time)
    
    return True, "OK"

def require_api_key(f):
    """Decorator to require valid API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
        
        if not validate_api_key(api_key):
            return jsonify({'error': 'Invalid or inactive API key'}), 401
        
        # Check rate limit
        allowed, message = check_rate_limit(api_key)
        if not allowed:
            return jsonify({'error': message}), 429
        
        # Update last used timestamp
        api_keys[api_key]['last_used'] = datetime.now()
        
        return f(*args, **kwargs)
    
    return decorated

@app.route('/api/v1/keys/generate', methods=['POST'])
def create_api_key():
    """Endpoint to generate new API key"""
    data = request.get_json()
    
    if not data or 'user_id' not in data:
        return jsonify({'error': 'user_id is required'}), 400
    
    user_id = data['user_id']
    plan = data.get('plan', 'free')
    
    if plan not in PLANS:
        return jsonify({'error': f'Invalid plan. Available plans: {", ".join(PLANS.keys())}'}), 400
    
    # Check if user already has max keys for their plan
    user_keys = [k for k, v in api_keys.items() if v['user_id'] == user_id and v['is_active']]
    if len(user_keys) >= PLANS[plan]['api_keys']:
        return jsonify({'error': f'Maximum number of API keys ({PLANS[plan]["api_keys"]}) reached for plan {plan}'}), 400
    
    api_key = generate_api_key(user_id, plan)
    
    return jsonify({
        'api_key': api_key,
        'plan': plan,
        'user_id': user_id,
        'created_at': datetime.now().isoformat()
    }), 201

@app.route('/api/v1/keys/revoke', methods=['POST'])
def revoke_api_key():
    """Endpoint to revoke an API key"""
    data = request.get_json()
    
    if not data or 'api_key' not in data:
        return jsonify({'error': 'api_key is required'}), 400
    
    api_key = data['api_key']
    
    if api_key not in api_keys:
        return jsonify({'error': 'API key not found'}), 404
    
    api_keys[api_key]['is_active'] = False
    
    return jsonify({'message': 'API key revoked successfully'}), 200

@app.route('/api/v1/keys/list', methods=['GET'])
@require_api_key
def list_api_keys():
    """Endpoint to list all API keys for the authenticated user"""
    api_key = request.headers.get('X-API-Key')
    user_id = api_keys[api_key]['user_id']
    
    user_keys = []
    for key, data in api_keys.items():
        if data['user_id'] == user_id:
            user_keys.append({
                'api_key': key,
                'plan': data['plan'],
                'created_at': data['created_at'].isoformat(),
                'last_used': data['last_used'].isoformat() if data['last_used'] else None,
                'is_active': data['is_active']
            })
    
    return jsonify({'api_keys': user_keys}), 200

@app.route('/api/v1/plans', methods=['GET'])
def get_plans():
    """Endpoint to get available plans and their limits"""
    plans_info = {}
    for plan_name, plan_data in PLANS.items():
        plans_info[plan_name] = {
            'requests_per_minute': plan_data['requests_per_minute'],
            'requests_per_day': plan_data['requests_per_day'],
            'api_keys': plan_data['api_keys'],
            'price': plan_data['price']
        }
    
    return jsonify({'plans': plans_info}), 200

@app.route('/api/v1/rate-limit-status', methods=['GET'])
@require_api_key
def get_rate_limit_status():
    """Get current rate limit status for the API key"""
    api_key = request.headers.get('X-API-Key')
    
    if api_key not in rate_limits:
        current_minute = 0
        current_day = 0
    else:
        current_time = time.time()
        limits = rate_limits[api_key]
        current_minute = len([t for t in limits['minute'] if current_time - t < 60])
        current_day = len([t for t in limits['day'] if current_time - t < 86400])
    
    plan_limits = get_plan_limits(api_key)
    
    return jsonify({
        'current_minute_requests': current_minute,
        'max_minute_requests': plan_limits['requests_per_minute'],
        'current_day_requests': current_day,
        'max_day_requests': plan_limits['requests_per_day'],
        'plan': api_keys[api_key]['plan']
    }), 200

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Create some demo API keys for testing
    demo_user = 'demo_user'
    demo_key = generate_api_key(demo_user, 'free')
    print(f"Demo API Key: {demo_key}")
    print(f"Available plans: {', '.join(PLANS.keys())}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)