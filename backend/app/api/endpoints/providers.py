"""API endpoints for LLM provider management"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import httpx
import json
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.llm_provider import LLMProvider
from app.api.models.schemas import (
    LLMProviderCreate,
    LLMProviderUpdate,
    LLMProviderResponse, 
    ProviderModelsResponse,
    ModelInfo
)
from app.services.goose_config_service import GooseConfigService

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("/current", response_model=LLMProviderResponse)
def get_current_provider(db: Session = Depends(get_db)):
    """Get current default provider being used for indexing"""
    provider = db.query(LLMProvider).filter(
        LLMProvider.is_default == True,
        LLMProvider.is_active == True
    ).first()
    
    if not provider:
        # Return a default response indicating no provider is set
        raise HTTPException(status_code=404, detail="No default provider configured")
    
    return LLMProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        base_url=provider.base_url,
        api_key=None,
        model=provider.model,
        is_active=provider.is_active,
        is_default=provider.is_default,
        config=provider.config or {},
        created_at=getattr(provider, 'created_at', None),
        updated_at=getattr(provider, 'updated_at', None)
    )


@router.get("/", response_model=List[LLMProviderResponse])
def list_providers(
    include_keys: bool = Query(False, description="Include API keys in response"),
    db: Session = Depends(get_db)
):
    """List all LLM providers"""
    providers = db.query(LLMProvider).all()
    results = []
    for provider in providers:
        data = LLMProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            base_url=provider.base_url,
            api_key=provider.api_key if include_keys else None,
            model=provider.model,
            is_active=provider.is_active,
            is_default=provider.is_default,
            config=provider.config or {},
            created_at=getattr(provider, 'created_at', None),
            updated_at=getattr(provider, 'updated_at', None)
        )
        results.append(data)
    return results


@router.post("/", response_model=LLMProviderResponse, status_code=201)
def create_provider(
    provider: LLMProviderCreate,
    db: Session = Depends(get_db)
):
    """Create a new LLM provider"""
    # Check if provider with same name exists
    existing = db.query(LLMProvider).filter(LLMProvider.name == provider.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Provider '{provider.name}' already exists")
    
    # If this is set as default, unset other defaults
    if provider.is_default:
        db.query(LLMProvider).update({LLMProvider.is_default: False})
    
    db_provider = LLMProvider(
        name=provider.name,
        display_name=provider.display_name,
        base_url=provider.base_url,
        api_key=provider.api_key,
        model=provider.model,
        is_active=provider.is_active,
        is_default=provider.is_default,
        config=provider.config
    )
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    
    # Update Goose config if this is the default provider
    if db_provider.is_default and db_provider.is_active:
        try:
            GooseConfigService.trigger_config_update()
        except Exception as e:
            # Log but don't fail the request
            logger.warning(f"Failed to update Goose config: {e}")
    
    return LLMProviderResponse(
        id=db_provider.id,
        name=db_provider.name,
        display_name=db_provider.display_name,
        base_url=db_provider.base_url,
        api_key=None,  # Don't return key
        model=db_provider.model,
        is_active=db_provider.is_active,
        is_default=db_provider.is_default,
        config=db_provider.config or {},
        created_at=getattr(db_provider, 'created_at', None),
        updated_at=getattr(db_provider, 'updated_at', None)
    )


@router.get("/{provider_id}", response_model=LLMProviderResponse)
def get_provider(
    provider_id: int,
    include_key: bool = Query(False, description="Include API key"),
    db: Session = Depends(get_db)
):
    """Get provider by ID"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return LLMProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        base_url=provider.base_url,
        api_key=provider.api_key if include_key else None,
        model=provider.model,
        is_active=provider.is_active,
        is_default=provider.is_default,
        config=provider.config or {},
        created_at=getattr(provider, 'created_at', None),
        updated_at=getattr(provider, 'updated_at', None)
    )


@router.patch("/{provider_id}", response_model=LLMProviderResponse)
def update_provider(
    provider_id: int,
    provider_update: LLMProviderUpdate,
    db: Session = Depends(get_db)
):
    """Update provider"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Update only provided fields
    update_data = provider_update.dict(exclude_unset=True)
    
    if 'display_name' in update_data:
        provider.display_name = update_data['display_name']
    if 'base_url' in update_data:
        provider.base_url = update_data['base_url']
    if 'api_key' in update_data and update_data['api_key']:  # Only update if provided and not empty
        provider.api_key = update_data['api_key']
    if 'is_active' in update_data:
        provider.is_active = update_data['is_active']
    if 'is_default' in update_data:
        if update_data['is_default']:
            # Unset other defaults
            db.query(LLMProvider).filter(LLMProvider.id != provider_id).update({LLMProvider.is_default: False})
        provider.is_default = update_data['is_default']
    if 'model' in update_data:
        provider.model = update_data['model']
    if 'config' in update_data:
        # Merge config instead of replacing completely
        if provider.config:
            provider.config.update(update_data['config'])
        else:
            provider.config = update_data['config']
    
    provider.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(provider)
    
    # Update Goose config if this is the default provider
    if provider.is_default and provider.is_active:
        try:
            GooseConfigService.trigger_config_update()
        except Exception as e:
            # Log but don't fail the request
            logger.warning(f"Failed to update Goose config: {e}")
    
    return LLMProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        base_url=provider.base_url,
        api_key=None,
        model=provider.model,
        is_active=provider.is_active,
        is_default=provider.is_default,
        config=provider.config or {},
            created_at=getattr(provider, 'created_at', None),
            updated_at=getattr(provider, 'updated_at', None)
    )


@router.delete("/{provider_id}", status_code=204)
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """Delete provider"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    db.delete(provider)
    db.commit()
    return None


@router.get("/{provider_id}/models", response_model=ProviderModelsResponse)
def get_provider_models(provider_id: int, db: Session = Depends(get_db)):
    """Get available models for a provider"""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    models = []
    available = False
    error = None
    
    try:
        # Support both "ollama" and "ollama-goose" providers
        if provider.name == "ollama" or provider.name == "ollama-goose":
            base_url = provider.base_url or "http://host.docker.internal:11434"
            response = httpx.get(f"{base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = [
                    ModelInfo(id=model["name"], name=model["name"], provider=provider.name)
                    for model in data.get("models", [])
                ]
                available = True
            else:
                error = f"Ollama returned status {response.status_code}"
        
        elif provider.name == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=provider.api_key)
            response = client.models.list()
            models = [
                ModelInfo(id=model.id, name=model.id, provider="openai")
                for model in response.data
                if "gpt" in model.id.lower() or "o1" in model.id.lower()
            ]
            available = True
        
        elif provider.name == "gigachat":
            # GigaChat API - try to get models
            try:
                from app.services.gigachat_token_manager import GigaChatTokenManager
                
                base_url = provider.base_url or "https://gigachat.devices.sberbank.ru/api/v1"
                
                # Get auth_key from config for token generation
                auth_key = None
                if provider.config and "auth_key" in provider.config:
                    auth_key = provider.config["auth_key"]
                elif provider.api_key:
                    # Fallback to api_key if no auth_key in config
                    auth_key = provider.api_key
                
                if not auth_key:
                    raise ValueError("GigaChat requires auth_key in config or api_key")
                
                # Check SSL verification setting (default to False for GigaChat)
                verify_ssl = False
                if provider.config and "verify_ssl" in provider.config:
                    verify_ssl = provider.config["verify_ssl"]
                
                # Get access token
                access_token = GigaChatTokenManager.get_token(auth_key, base_url, verify_ssl=verify_ssl)
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
                # GigaChat often uses self-signed certificates, so disable SSL verification by default
                response = httpx.get(f"{base_url}/models", headers=headers, timeout=10.0, verify=verify_ssl)
                if response.status_code == 200:
                    data = response.json()
                    models = [
                        ModelInfo(id=model.get("id", ""), name=model.get("name", ""), provider="gigachat")
                        for model in data.get("data", [])
                    ]
                    available = True
                else:
                    # Return default GigaChat models if API fails
                    models = [
                        ModelInfo(id="GigaChat-Pro", name="GigaChat Pro", provider="gigachat"),
                        ModelInfo(id="GigaChat-Max", name="GigaChat Max", provider="gigachat"),
                    ]
                    error = f"GigaChat API returned status {response.status_code}, using default models"
            except Exception as e:
                # Return default models on error
                models = [
                    ModelInfo(id="GigaChat-Pro", name="GigaChat Pro", provider="gigachat"),
                    ModelInfo(id="GigaChat-Max", name="GigaChat Max", provider="gigachat"),
                ]
                error = f"Error connecting to GigaChat: {str(e)}"
        
        elif provider.name == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=provider.api_key)
            # Anthropic doesn't have a models list endpoint, return known models
            models = [
                ModelInfo(id="claude-3-opus-20240229", name="Claude 3 Opus", provider="anthropic"),
                ModelInfo(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet", provider="anthropic"),
                ModelInfo(id="claude-3-haiku-20240307", name="Claude 3 Haiku", provider="anthropic"),
            ]
            available = True
        
        elif provider.name == "vllm":
            # vLLM uses OpenAI-compatible API, try to get models
            try:
                base_url = provider.base_url or "http://localhost:8000"
                # Remove trailing slash and ensure we have the base URL
                base_url = base_url.rstrip('/')
                
                # Try different approaches to get models
                # Method 1: Try OpenAI client
                try:
                    from openai import OpenAI
                    client = OpenAI(
                        base_url=f"{base_url}/v1",
                        api_key="vllm"
                    )
                    response = client.models.list()
                    if response.data:
                        models = [
                            ModelInfo(id=model.id, name=model.id, provider="vllm")
                            for model in response.data
                        ]
                        available = True
                    else:
                        raise ValueError("No models in response")
                except Exception as client_error:
                    # Method 2: Try direct HTTP request
                    # httpx is already imported at the top of the file
                    headers = {}
                    if provider.api_key:
                        headers["Authorization"] = f"Bearer {provider.api_key}"
                    else:
                        headers["Authorization"] = "Bearer vllm"
                    
                    response = httpx.get(
                        f"{base_url}/v1/models",
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data and data["data"]:
                            models = [
                                ModelInfo(id=model.get("id", ""), name=model.get("id", ""), provider="vllm")
                                for model in data["data"]
                            ]
                            available = True
                        else:
                            raise ValueError("No models in response data")
                    else:
                        raise ValueError(f"HTTP {response.status_code}: {response.text}")
                        
            except Exception as e:
                # If API fails, return common vLLM model names based on what's typically used
                models = [
                    ModelInfo(id="Qwen/Qwen2.5-Coder-7B-Instruct", name="Qwen2.5 Coder 7B (Recommended)", provider="vllm"),
                    ModelInfo(id="deepseek-ai/DeepSeek-Coder-6.7B-Instruct", name="DeepSeek Coder 6.7B", provider="vllm"),
                    ModelInfo(id="mistralai/Mistral-7B-Instruct-v0.3", name="Mistral 7B Instruct", provider="vllm"),
                    ModelInfo(id="meta-llama/Llama-2-7b-chat-hf", name="Llama 2 7B Chat", provider="vllm"),
                    ModelInfo(id="Qwen/Qwen2.5-3B-Instruct", name="Qwen2.5 3B (Lightweight)", provider="vllm"),
                ]
                error = f"Could not fetch models from vLLM: {str(e)}. Showing common models instead."
                # Still mark as available since we're providing fallback models
                available = True
        
    except httpx.ConnectError as e:
        error = f"Connection error: {str(e)}"
    except httpx.TimeoutException:
        error = "Connection timeout"
    except Exception as e:
        error = f"Error: {str(e)}"
    
    return ProviderModelsResponse(
        provider=provider.name,
        models=models,
        available=available,
        error=error
    )

