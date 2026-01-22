"""GigaChat token manager for automatic token refresh"""
import logging
import httpx
import time
import threading
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GigaChatTokenManager:
    """Manages GigaChat access tokens with automatic refresh"""
    
    # Class-level cache: auth_key -> (token, expires_at)
    _token_cache: dict[str, tuple[str, datetime]] = {}
    _lock = threading.Lock()
    
    # Token expires in 30 minutes, but refresh 5 minutes before
    TOKEN_LIFETIME = timedelta(minutes=30)
    REFRESH_BEFORE = timedelta(minutes=5)
    
    @classmethod
    def get_token(cls, auth_key: str, base_url: Optional[str] = None, verify_ssl: bool = False) -> str:
        """
        Get a valid access token for GigaChat.
        Automatically refreshes if expired or about to expire.
        
        Args:
            auth_key: GigaChat authorization key (Basic auth)
            base_url: Optional custom base URL for OAuth endpoint
            verify_ssl: Whether to verify SSL certificates (default: False for GigaChat)
            
        Returns:
            Access token string
        """
        if not auth_key:
            raise ValueError("auth_key is required for GigaChat")
        
        with cls._lock:
            # Check if we have a valid cached token
            if auth_key in cls._token_cache:
                token, expires_at = cls._token_cache[auth_key]
                now = datetime.utcnow()
                
                # If token is still valid (with refresh margin), return it
                if expires_at > now + cls.REFRESH_BEFORE:
                    logger.debug(f"Using cached GigaChat token (expires at {expires_at})")
                    return token
                else:
                    logger.info(f"GigaChat token expired or expiring soon (expires at {expires_at}), refreshing...")
            
            # Get new token
            token = cls._fetch_new_token(auth_key, base_url, verify_ssl)
            
            # Cache it
            expires_at = datetime.utcnow() + cls.TOKEN_LIFETIME
            cls._token_cache[auth_key] = (token, expires_at)
            logger.info(f"Obtained new GigaChat token (expires at {expires_at})")
            
            return token
    
    @classmethod
    def _fetch_new_token(cls, auth_key: str, base_url: Optional[str] = None, verify_ssl: bool = False) -> str:
        """
        Fetch a new access token from GigaChat OAuth endpoint
        
        Args:
            auth_key: Authorization key for Basic auth
            base_url: Optional custom base URL
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            Access token string
        """
        # Default OAuth endpoint
        oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        
        # If custom base_url provided, try to construct OAuth URL
        if base_url:
            # If base_url is like "https://gigachat.devices.sberbank.ru/api/v1"
            # OAuth endpoint is usually at "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            # But we'll try to use the provided base_url's domain if possible
            pass  # For now, use default OAuth URL
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Authorization": f"Basic {auth_key}",
            "RqUID": cls._generate_rquid()
        }
        
        data = {
            "scope": "GIGACHAT_API_PERS"
        }
        
        try:
            logger.info(f"Requesting new GigaChat token from {oauth_url}")
            response = httpx.post(
                oauth_url,
                headers=headers,
                data=data,
                timeout=10.0,
                verify=verify_ssl  # GigaChat often uses self-signed certificates
            )
            
            if response.status_code != 200:
                error_text = response.text[:500] if response.text else "No error message"
                raise ValueError(
                    f"Failed to get GigaChat token: HTTP {response.status_code} - {error_text}"
                )
            
            result = response.json()
            
            # GigaChat returns token in 'access_token' field
            if "access_token" not in result:
                raise ValueError(f"Invalid GigaChat response: no access_token field. Response: {result}")
            
            token = result["access_token"]
            logger.info("Successfully obtained GigaChat access token")
            return token
            
        except httpx.TimeoutException:
            raise ValueError("Timeout while requesting GigaChat token")
        except httpx.RequestError as e:
            raise ValueError(f"Error requesting GigaChat token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting GigaChat token: {e}")
            raise
    
    @staticmethod
    def _generate_rquid() -> str:
        """Generate a RqUID (Request UID) for GigaChat API"""
        import uuid
        return str(uuid.uuid4())
    
    @classmethod
    def clear_cache(cls, auth_key: Optional[str] = None):
        """Clear token cache for a specific auth_key or all"""
        with cls._lock:
            if auth_key:
                cls._token_cache.pop(auth_key, None)
                logger.info(f"Cleared token cache for auth_key")
            else:
                cls._token_cache.clear()
                logger.info("Cleared all token cache")

