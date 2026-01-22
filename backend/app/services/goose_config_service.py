"""
Service for managing Goose configuration
Automatically updates Goose config when LLM provider changes
"""
import logging
import os
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


class GooseConfigService:
    """Service for managing Goose configuration"""
    
    @staticmethod
    def update_goose_config(provider_name: str, provider_model: str, 
                           base_url: Optional[str] = None, 
                           api_key: Optional[str] = None) -> bool:
        """
        Update Goose configuration file when provider changes
        
        Args:
            provider_name: Name of the LLM provider (ollama, openai, anthropic, etc.)
            provider_model: Model name
            base_url: Base URL for the provider (for ollama, vllm)
            api_key: API key (for openai, anthropic)
            
        Returns:
            True if config was updated successfully, False otherwise
        """
        try:
            # Use HTTP endpoint to trigger config reload in Goose container
            # This is more reliable than docker exec from inside container
            goose_url = os.getenv('GOOSE_API_URL', 'http://goose:8080')
            try:
                response = httpx.get(
                    f"{goose_url}/reload-config",
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info(f"Goose config updated successfully for provider {provider_name}")
                    return True
                else:
                    logger.warning(f"Failed to update Goose config: HTTP {response.status_code}")
                    return False
            except httpx.ConnectError:
                logger.warning("Could not connect to Goose service, config will be updated on next container restart")
                return False
            except httpx.TimeoutException:
                logger.warning("Timeout connecting to Goose service")
                return False
                
        except Exception as e:
            logger.warning(f"Error updating Goose config (non-critical): {e}")
            # Don't fail the request if Goose config update fails
            return False
    
    @staticmethod
    def trigger_config_update() -> bool:
        """
        Trigger Goose config update (reads from database)
        This is called when provider is updated in backend
        """
        return GooseConfigService.update_goose_config("", "")
