"""Redis cache wrapper for the application."""
import json
import redis
from typing import Any, Optional
from datetime import timedelta


class RedisCache:
    """Redis cache wrapper with JSON serialization."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, password: Optional[str] = None):
        """Initialize Redis connection."""
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password if password else None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
    def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            return self.client.ping()
        except redis.ConnectionError:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL in seconds."""
        try:
            serialized = json.dumps(value)
            return self.client.setex(key, ttl, serialized)
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0
