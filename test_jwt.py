import jwt
import datetime

# Test JWT token generation and verification
JWT_SECRET = "test_secret"
token_payload = {
    "email": "test@example.com",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
}

try:
    # Encode the token
    token = jwt.encode(token_payload, JWT_SECRET, algorithm="HS256")
    print(f"✅ Token generated successfully: {token}")
    
    # Decode the token
    decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    print(f"✅ Token decoded successfully: {decoded}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"JWT module contents: {dir(jwt)}")
