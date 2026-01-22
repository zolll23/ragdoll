import json
import logging
import re
import os
from datetime import datetime
from typing import Optional, Dict, List
from openai import OpenAI
import anthropic
import httpx
from app.api.models.schemas import CodeAnalysisResult
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.llm_provider import LLMProvider
from app.services.gigachat_token_manager import GigaChatTokenManager
from app.analyzers.static_metrics import StaticMetricsAnalyzer

logger = logging.getLogger(__name__)


class RateLimitException(Exception):
    """Exception raised when rate limit is hit - can be retried with delay"""
    pass

def _create_ollama_http_client():
    """Create httpx client with timeout for Ollama"""
    return httpx.Client(
        timeout=httpx.Timeout(300.0, connect=10.0),  # 5 min timeout for slow models, 10s connect
        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
    )


class CodeAnalyzer:
    """AI Agent for code analysis with support for multiple LLM providers"""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.model = model or settings.LLM_MODEL
        self.client = None
        self.db_provider = None
        self.static_analyzer = StaticMetricsAnalyzer()
        
        self._init_client()
    
    def _init_client(self):
        """Initialize LLM client based on provider"""
        # Try to get default provider from database first
        db = SessionLocal()
        try:
            # First try to get default provider
            db_provider = db.query(LLMProvider).filter(
                LLMProvider.is_default == True,
                LLMProvider.is_active == True
            ).first()
            
            # If no default, try by name
            if not db_provider and self.provider:
                db_provider = db.query(LLMProvider).filter(
                    LLMProvider.name == self.provider,
                    LLMProvider.is_active == True
                ).first()
            
            if db_provider:
                # Use provider from database
                self.db_provider = db_provider
                self.provider = db_provider.name
                # Use model from provider if available
                if db_provider.model:
                    self.model = db_provider.model
                    logger.info(f"Using model from provider: {self.model}")
                elif not self.model or self.model == settings.LLM_MODEL:
                    # Fallback to settings if no model set in provider
                    self.model = settings.LLM_MODEL
                    logger.info(f"Using model from settings: {self.model}")
                self._init_client_from_db_provider(db_provider)
                logger.info(f"Using provider from DB: {db_provider.name} (URL: {db_provider.base_url}) with model: {self.model}")
                return
        finally:
            db.close()
        
        # Fallback to settings
        if self.provider == "openai":
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
            self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "ollama":
            # Ollama uses OpenAI-compatible API
            http_client = _create_ollama_http_client()
            self.client = OpenAI(
                base_url=f"{settings.OLLAMA_URL}/v1",
                api_key="ollama",  # Ollama doesn't require real API key
                http_client=http_client
            )
            # For Ollama, we might need to adjust model name
            if not self.model or self.model == "gpt-4-turbo-preview":
                self.model = "qwen3:latest"
        elif self.provider == "vllm":
            # vLLM uses OpenAI-compatible API
            vllm_url = getattr(settings, 'VLLM_URL', 'http://localhost:8000')
            http_client = _create_ollama_http_client()  # Same timeout settings work for vLLM
            self.client = OpenAI(
                base_url=f"{vllm_url}/v1",
                api_key="vllm",  # vLLM doesn't require real API key
                http_client=http_client
            )
            logger.info(f"Using vLLM at {vllm_url}")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _init_client_from_db_provider(self, provider: LLMProvider):
        """Initialize client from database provider"""
        # Model is already set in _init_client before calling this method
        if provider.name == "openai":
            self.client = OpenAI(api_key=provider.api_key)
        elif provider.name == "anthropic":
            self.client = anthropic.Anthropic(api_key=provider.api_key)
        elif provider.name == "ollama":
            base_url = provider.base_url or settings.OLLAMA_URL
            logger.info(f"Connecting to Ollama at: {base_url}")
            # Create new httpx client for this instance (thread-safe)
            http_client = _create_ollama_http_client()
            self.client = OpenAI(
                base_url=f"{base_url}/v1",
                api_key="ollama",
                http_client=http_client
            )
            # For Ollama, use provider model or fallback
            if provider.model:
                self.model = provider.model
            elif not self.model or self.model == "gpt-4-turbo-preview":
                self.model = "qwen3:latest"
            logger.info(f"Using Ollama model: {self.model}")
        elif provider.name == "gigachat":
            # GigaChat uses OpenAI-compatible API with token-based auth
            base_url = provider.base_url or "https://gigachat.devices.sberbank.ru/api/v1"
            
            # Get auth_key from config (for token generation) or use api_key directly
            auth_key = None
            if provider.config and "auth_key" in provider.config:
                auth_key = provider.config["auth_key"]
            elif provider.api_key:
                # If api_key is provided but no auth_key in config, assume api_key is the auth_key
                auth_key = provider.api_key
            
            if not auth_key:
                raise ValueError("GigaChat requires auth_key in config or api_key for token generation")
            
            # Get access token (will be automatically refreshed when needed)
            # Check if SSL verification should be disabled (GigaChat often uses self-signed certs)
            verify_ssl = True
            if provider.config and "verify_ssl" in provider.config:
                verify_ssl = provider.config["verify_ssl"]
            elif provider.config and "verify_ssl" not in provider.config:
                # Default to False for GigaChat (they often use self-signed certificates)
                verify_ssl = False
            
            try:
                access_token = GigaChatTokenManager.get_token(auth_key, base_url, verify_ssl=verify_ssl)
                logger.info("Obtained GigaChat access token")
            except Exception as e:
                logger.error(f"Failed to get GigaChat token: {e}")
                raise ValueError(f"Failed to authenticate with GigaChat: {e}")
            
            # Create OpenAI client with Bearer token
            # Note: GigaChat API endpoint should be /api/v1, not /api/v1/chat/completions
            # Create http_client with SSL verification settings for GigaChat
            http_client = httpx.Client(
                timeout=httpx.Timeout(120.0, connect=10.0),  # 2 min timeout, 10s connect
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                verify=verify_ssl  # Use SSL verification setting
            )
            self.client = OpenAI(
                base_url=base_url,
                api_key=access_token,
                http_client=http_client
            )
            logger.info(f"Initialized GigaChat client with base_url: {base_url}, verify_ssl: {verify_ssl}")
        elif provider.name == "vllm":
            # vLLM uses OpenAI-compatible API
            base_url = provider.base_url or "http://localhost:8000"
            logger.info(f"Connecting to vLLM at: {base_url}")
            # Create new httpx client for this instance (thread-safe)
            http_client = _create_ollama_http_client()  # Same timeout settings work for vLLM
            self.client = OpenAI(
                base_url=f"{base_url}/v1",
                api_key="vllm",  # vLLM doesn't require real API key
                http_client=http_client
            )
            # Use provider model if available
            if provider.model:
                self.model = provider.model
            logger.info(f"Using vLLM model: {self.model}")
        else:
            raise ValueError(f"Unknown provider: {provider.name}")
        
        logger.info(f"Initialized {provider.name} with model: {self.model}")
    
    def _log_prompt_to_file(self, prompt: str, entity_name: str, entity_type: str, language: str, provider: str, model: str):
        """Log prompt to file if enabled"""
        if not settings.LOG_PROMPTS_TO_FILE:
            return
        
        try:
            # Ensure log directory exists
            log_file = settings.LOG_PROMPTS_FILE_PATH
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Write prompt with metadata
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Entity: {entity_name} ({entity_type})\n")
                f.write(f"Language: {language}\n")
                f.write(f"Provider: {provider}\n")
                f.write(f"Model: {model}\n")
                f.write(f"{'='*80}\n")
                f.write(f"PROMPT:\n{prompt}\n")
                f.write(f"{'='*80}\n\n")
        except Exception as e:
            logger.warning(f"Failed to log prompt to file: {e}")
    
    def _log_failed_analysis(self, error: Exception, entity_name: str, entity_type: str, language: str, 
                            provider: str, model: str, prompt: Optional[str] = None, attempt: int = 1):
        """Log failed analysis to file if enabled"""
        if not settings.LOG_FAILED_ANALYSES_TO_FILE:
            return
        
        try:
            # Ensure log directory exists
            log_file = settings.LOG_FAILED_ANALYSES_FILE_PATH
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            # Determine error type and details
            error_type = type(error).__name__
            error_msg = str(error)
            
            # Classify error
            error_category = "unknown"
            if "rate limit" in error_msg.lower() or "429" in error_msg or isinstance(error, RateLimitException):
                error_category = "rate_limit"
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                error_category = "timeout"
            elif "connection" in error_msg.lower() or "unreachable" in error_msg.lower() or "refused" in error_msg.lower():
                error_category = "connection_error"
            elif "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg:
                error_category = "server_error"
            elif "context" in error_msg.lower() or "token" in error_msg.lower() or "length" in error_msg.lower():
                error_category = "context_window_exceeded"
            elif "json" in error_msg.lower() or "parse" in error_msg.lower():
                error_category = "invalid_response"
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                error_category = "authentication_error"
            
            # Write error details
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Entity: {entity_name} ({entity_type})\n")
                f.write(f"Language: {language}\n")
                f.write(f"Provider: {provider}\n")
                f.write(f"Model: {model}\n")
                f.write(f"Attempt: {attempt}\n")
                f.write(f"Error Category: {error_category}\n")
                f.write(f"Error Type: {error_type}\n")
                f.write(f"Error Message: {error_msg}\n")
                f.write(f"{'='*80}\n")
                if prompt:
                    f.write(f"PROMPT (first 2000 chars):\n{prompt[:2000]}\n")
                    if len(prompt) > 2000:
                        f.write(f"... (truncated, total length: {len(prompt)} chars)\n")
                f.write(f"{'='*80}\n\n")
        except Exception as e:
            logger.warning(f"Failed to log failed analysis to file: {e}")
    
    def analyze_code(
        self,
        code: str,
        language: str,
        entity_type: str,
        entity_name: str,
        context: Optional[str] = None,
        ui_language: str = "EN",
        dependencies: Optional[List[str]] = None
    ) -> tuple[CodeAnalysisResult, int]:
        """Analyze code and return structured result with token usage
        
        Args:
            code: Source code to analyze
            language: 'python' or 'php'
            entity_type: 'class', 'method', 'function', etc.
            entity_name: Name of the entity
            context: Optional context (dependencies, parent classes, etc.)
            ui_language: 'EN' or 'RU'
            dependencies: List of dependency names for coupling calculation
            
        Returns:
            tuple: (CodeAnalysisResult, tokens_used)
        """
        
        # First, compute static metrics (no LLM needed)
        static_metrics = self.static_analyzer.analyze(
            code=code,
            language=language,
            entity_type=entity_type,
            dependencies=dependencies or []
        )
        
        logger.debug(f"Computed static metrics for {entity_name}: LOC={static_metrics['lines_of_code']}, "
                    f"Cyclomatic={static_metrics['cyclomatic_complexity']}, "
                    f"Security issues={len(static_metrics['security_issues'])}")
        
        # Build prompt including static metrics for LLM context
        prompt = self._build_prompt(code, language, entity_type, entity_name, context, ui_language, static_metrics)
        
        # Log prompt to file if enabled
        self._log_prompt_to_file(prompt, entity_name, entity_type, language, self.provider, self.model)
        
        tokens_used = 0
        
        try:
            # Get provider from DB to check type
            db = SessionLocal()
            try:
                db_provider = db.query(LLMProvider).filter(
                    LLMProvider.name == self.provider,
                    LLMProvider.is_active == True
                ).first()
            finally:
                db.close()
            
            # Use db_provider from instance if available
            if not db_provider and hasattr(self, 'db_provider'):
                db_provider = self.db_provider
            
            if self.provider == "anthropic" or (db_provider and db_provider.name == "anthropic"):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text
                # Anthropic provides usage info
                if hasattr(response, 'usage'):
                    tokens_used = response.usage.input_tokens + response.usage.output_tokens
                else:
                    # Estimate: ~4 characters per token
                    tokens_used = len(prompt) // 4 + len(result_text) // 4
            else:  # OpenAI, Ollama, vLLM, or GigaChat (all use OpenAI-compatible API)
                # Timeout is handled by http_client for Ollama/vLLM
                logger.info(f"Sending request to LLM ({self.provider}/{self.model})...")
                try:
                    # For Ollama and vLLM, don't use response_format as it may not be supported
                    # Instead, include JSON format instruction in the prompt
                    create_kwargs = {
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    }
                    # Only use response_format for OpenAI and GigaChat (not Ollama/vLLM)
                    if self.provider not in ["ollama", "vllm"]:
                        create_kwargs["response_format"] = {"type": "json_object"}
                    
                    # For Ollama, we need to pass options differently
                    # OpenAI client doesn't support 'options' or 'extra_body' directly
                    # We'll need to modify the HTTP request after creation or use a workaround
                    # For now, we'll skip the options parameter to avoid errors
                    # The double BOS token warning is not critical and won't break functionality
                    # if self.provider == "ollama":
                    #     # Note: OpenAI client doesn't support extra_body or options directly
                    #     # We would need to modify the HTTP client or use a different approach
                    #     # For now, we'll skip this to avoid errors
                    #     pass
                    
                    # For GigaChat, refresh token if needed before request
                    if self.provider == "gigachat" and hasattr(self, 'db_provider') and self.db_provider:
                        auth_key = None
                        if self.db_provider.config and "auth_key" in self.db_provider.config:
                            auth_key = self.db_provider.config["auth_key"]
                        elif self.db_provider.api_key:
                            auth_key = self.db_provider.api_key
                        
                        if auth_key:
                            try:
                                # Check SSL verification setting
                                verify_ssl = True
                                if self.db_provider.config and "verify_ssl" in self.db_provider.config:
                                    verify_ssl = self.db_provider.config["verify_ssl"]
                                else:
                                    verify_ssl = False  # Default for GigaChat
                                
                                # Refresh token if needed (get_token handles caching and refresh)
                                access_token = GigaChatTokenManager.get_token(auth_key, self.db_provider.base_url, verify_ssl=verify_ssl)
                                
                                # Recreate client with new token and http_client
                                # This ensures http_client is properly configured
                                base_url = self.db_provider.base_url or "https://gigachat.devices.sberbank.ru/api/v1"
                                http_client = httpx.Client(
                                    timeout=httpx.Timeout(120.0, connect=10.0),
                                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                                    verify=verify_ssl
                                )
                                self.client = OpenAI(
                                    base_url=base_url,
                                    api_key=access_token,
                                    http_client=http_client
                                )
                                logger.debug(f"Refreshed GigaChat client with new token")
                            except Exception as e:
                                logger.warning(f"Failed to refresh GigaChat token before request: {e}")
                    
                    response = self.client.chat.completions.create(**create_kwargs)
                    logger.info(f"Received response from LLM ({self.provider}/{self.model})")
                    result_text = response.choices[0].message.content
                    
                    # Get token usage from response
                    if hasattr(response, 'usage') and response.usage:
                        tokens_used = response.usage.total_tokens
                    else:
                        # Estimate: ~4 characters per token (rough approximation)
                        tokens_used = len(prompt) // 4 + len(result_text) // 4
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    # Check for rate limiting (429)
                    is_rate_limit = (
                        error_type == "RateLimitError" or
                        "429" in error_msg or
                        "rate limit" in error_msg.lower() or
                        "too many requests" in error_msg.lower()
                    )
                    
                    # Check for server errors (500, 502, 503, 504)
                    is_server_error = (
                        "500" in error_msg or
                        "502" in error_msg or
                        "503" in error_msg or
                        "504" in error_msg or
                        "internal server error" in error_msg.lower() or
                        "bad gateway" in error_msg.lower() or
                        "service unavailable" in error_msg.lower() or
                        "gateway timeout" in error_msg.lower()
                    )
                    
                    if is_rate_limit:
                        logger.warning(f"Rate limit hit for {self.provider}. This is a retryable error.")
                        # Log failed analysis before raising
                        self._log_failed_analysis(e, entity_name, entity_type, language, self.provider, self.model, prompt)
                        # Raise a specific exception that can be caught and retried with delay
                        raise RateLimitException(f"Rate limit exceeded: {error_msg}") from e
                    
                    if is_server_error:
                        logger.error(f"Server error from {self.provider} ({self.model}): {error_type}: {error_msg}")
                        logger.error(f"This might be due to:")
                        logger.error(f"  - Insufficient memory for model {self.model}")
                        logger.error(f"  - Model not loaded or crashed")
                        logger.error(f"  - Request too large or timeout")
                        logger.error(f"  - Ollama server issues")
                        # Log failed analysis before raising
                        self._log_failed_analysis(e, entity_name, entity_type, language, self.provider, self.model, prompt)
                        # For server errors, we should retry with delay
                        raise RateLimitException(f"Server error from {self.provider}: {error_msg}") from e
                    
                    logger.error(f"LLM request failed: {error_type}: {error_msg}")
                    # Log failed analysis
                    self._log_failed_analysis(e, entity_name, entity_type, language, self.provider, self.model, prompt)
                    raise
            
            # Parse JSON and validate with Pydantic
            # For Ollama/vLLM, response might contain reasoning or other text before JSON
            if self.provider in ["ollama", "vllm"]:
                # Try to extract JSON from response (might have reasoning or other text)
                result_text = self._extract_json_from_ollama_response(result_text)
            
            # Try to fix common JSON issues before parsing
            result_text = self._fix_json_response(result_text)
            
            # Try to parse JSON with retry logic for JSON errors
            max_json_retries = 3
            json_retry_count = 0
            result_dict = None
            last_json_error = None
            
            while json_retry_count <= max_json_retries:
                try:
                    result_dict = json.loads(result_text)
                    break  # Success, exit retry loop
                except json.JSONDecodeError as json_error:
                    last_json_error = json_error
                    error_msg = str(json_error)
                    
                    if json_retry_count == 0:
                        # First retry: try aggressive fix for escape sequences
                        logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying aggressive fix: {json_error}")
                        result_text = self._fix_json_response_aggressive(result_text)
                    elif json_retry_count == 1:
                        # Second retry: try fixing unterminated strings specifically
                        logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying to fix unterminated strings: {json_error}")
                        if "Unterminated string" in error_msg or "Expecting" in error_msg:
                            result_text = self._fix_unterminated_strings(result_text)
                            result_text = self._fix_missing_commas(result_text)
                        result_text = self._fix_json_response_aggressive(result_text)
                    elif json_retry_count == 2:
                        # Third retry: try fixing missing commas specifically
                        logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying to fix missing commas: {json_error}")
                        result_text = self._fix_missing_commas(result_text)
                        result_text = self._fix_unterminated_strings(result_text)
                        result_text = self._fix_json_response_aggressive(result_text)
                    else:
                        # Final attempt: try all fixes in sequence
                        logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying all fixes: {json_error}")
                        result_text = self._fix_unterminated_strings(result_text)
                        result_text = self._fix_missing_commas(result_text)
                        result_text = self._fix_json_response_aggressive(result_text)
                    
                    json_retry_count += 1
            
            if result_dict is None:
                # All retries failed
                logger.error(f"JSON parse failed after {max_json_retries + 1} attempts: {last_json_error}")
                logger.error(f"Response was: {result_text[:1000]}")
                raise ValueError(f"Invalid JSON response from LLM after {max_json_retries + 1} fix attempts: {last_json_error}")
            
            # Ensure code_fingerprint is present (LLM might not return it)
            # Check if it's missing or empty
            code_fingerprint = result_dict.get('code_fingerprint', '').strip()
            if not code_fingerprint:
                # Generate a simple fingerprint from code if missing
                # Normalize code: remove comments, normalize whitespace
                normalized = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)  # Remove single-line comments
                normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)  # Remove multi-line comments
                normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
                normalized = normalized.strip()
                code_fingerprint = normalized[:500] if normalized else code[:500]  # Limit length, fallback to raw code
                result_dict['code_fingerprint'] = code_fingerprint
            
            # Merge static metrics into LLM result
            result_dict.update({
                'lines_of_code': static_metrics['lines_of_code'],
                'cyclomatic_complexity': static_metrics['cyclomatic_complexity'],
                'cognitive_complexity': static_metrics['cognitive_complexity'],
                'max_nesting_depth': static_metrics['max_nesting_depth'],
                'parameter_count': static_metrics['parameter_count'],
                'coupling_score': static_metrics['coupling_score'],
                'cohesion_score': static_metrics['cohesion_score'],
                'afferent_coupling': static_metrics['afferent_coupling'],
                'efferent_coupling': static_metrics['efferent_coupling'],
                'n_plus_one_queries': static_metrics['n_plus_one_queries'],
                'space_complexity': static_metrics['space_complexity'],
                'hot_path_detected': static_metrics['hot_path_detected'],
                'security_issues': static_metrics['security_issues'],
                'hardcoded_secrets': static_metrics['hardcoded_secrets'],
                'insecure_dependencies': static_metrics['insecure_dependencies'],
                'is_god_object': static_metrics['is_god_object'],
                'feature_envy_score': static_metrics['feature_envy_score'],
                'data_clumps': static_metrics['data_clumps'],
                'long_parameter_list': static_metrics['long_parameter_list'],
            })
            
            return CodeAnalysisResult(**result_dict), tokens_used
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {result_text[:500]}")
            
            # Try multiple extraction strategies
            extracted_json = None
            
            # Strategy 1: Extract from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                extracted_json = json_match.group(1)
            
            # Strategy 2: Find first { ... } block (for Ollama reasoning responses)
            if not extracted_json:
                json_match = re.search(r'(\{.*\})', result_text, re.DOTALL)
                if json_match:
                    extracted_json = json_match.group(1)
            
            # Strategy 3: Find JSON after common prefixes
            if not extracted_json:
                # Remove common prefixes like "<think>" or reasoning text
                cleaned = re.sub(r'^[^{]*', '', result_text, flags=re.DOTALL)
                json_match = re.search(r'(\{.*\})', cleaned, re.DOTALL)
                if json_match:
                    extracted_json = json_match.group(1)
            
            if extracted_json:
                try:
                    fixed_json = self._fix_json_response(extracted_json)
                    
                    # Try to parse with retry logic
                    max_json_retries = 3
                    json_retry_count = 0
                    result_dict = None
                    last_json_error = None
                    
                    while json_retry_count <= max_json_retries:
                        try:
                            result_dict = json.loads(fixed_json)
                            break  # Success, exit retry loop
                        except json.JSONDecodeError as json_error2:
                            last_json_error = json_error2
                            error_msg = str(json_error2)
                            
                            if json_retry_count == 0:
                                # First retry: try aggressive fix
                                logger.warning(f"JSON parse failed after standard fix (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying aggressive: {json_error2}")
                                fixed_json = self._fix_json_response_aggressive(extracted_json)
                            elif json_retry_count == 1:
                                # Second retry: try fixing unterminated strings
                                logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying to fix unterminated strings: {json_error2}")
                                if "Unterminated string" in error_msg or "Expecting" in error_msg:
                                    fixed_json = self._fix_unterminated_strings(extracted_json)
                                    fixed_json = self._fix_missing_commas(fixed_json)
                                fixed_json = self._fix_json_response_aggressive(fixed_json)
                            elif json_retry_count == 2:
                                # Third retry: try fixing missing commas
                                logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying to fix missing commas: {json_error2}")
                                fixed_json = self._fix_missing_commas(extracted_json)
                                fixed_json = self._fix_unterminated_strings(fixed_json)
                                fixed_json = self._fix_json_response_aggressive(fixed_json)
                            else:
                                # Final attempt: try all fixes
                                logger.warning(f"JSON parse failed (attempt {json_retry_count + 1}/{max_json_retries + 1}), trying all fixes: {json_error2}")
                                fixed_json = self._fix_unterminated_strings(extracted_json)
                                fixed_json = self._fix_missing_commas(fixed_json)
                                fixed_json = self._fix_json_response_aggressive(fixed_json)
                            
                            json_retry_count += 1
                    
                    if result_dict is None:
                        # All retries failed
                        logger.error(f"JSON parse failed after {max_json_retries + 1} attempts: {last_json_error}")
                        raise last_json_error
                    
                    # Ensure code_fingerprint is present (LLM might not return it)
                    # Check if it's missing or empty
                    code_fingerprint = result_dict.get('code_fingerprint', '').strip()
                    if not code_fingerprint:
                        # Generate a simple fingerprint from code if missing
                        # Normalize code: remove comments, normalize whitespace
                        normalized = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)  # Remove single-line comments
                        normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)  # Remove multi-line comments
                        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
                        normalized = normalized.strip()
                        code_fingerprint = normalized[:500] if normalized else code[:500]  # Limit length, fallback to raw code
                        result_dict['code_fingerprint'] = code_fingerprint
                    
                    # Merge static metrics into LLM result
                    result_dict.update({
                        'lines_of_code': static_metrics['lines_of_code'],
                        'cyclomatic_complexity': static_metrics['cyclomatic_complexity'],
                        'cognitive_complexity': static_metrics['cognitive_complexity'],
                        'max_nesting_depth': static_metrics['max_nesting_depth'],
                        'parameter_count': static_metrics['parameter_count'],
                        'coupling_score': static_metrics['coupling_score'],
                        'cohesion_score': static_metrics['cohesion_score'],
                        'afferent_coupling': static_metrics['afferent_coupling'],
                        'efferent_coupling': static_metrics['efferent_coupling'],
                        'n_plus_one_queries': static_metrics['n_plus_one_queries'],
                        'space_complexity': static_metrics['space_complexity'],
                        'hot_path_detected': static_metrics['hot_path_detected'],
                        'security_issues': static_metrics['security_issues'],
                        'hardcoded_secrets': static_metrics['hardcoded_secrets'],
                        'insecure_dependencies': static_metrics['insecure_dependencies'],
                        'is_god_object': static_metrics['is_god_object'],
                        'feature_envy_score': static_metrics['feature_envy_score'],
                        'data_clumps': static_metrics['data_clumps'],
                        'long_parameter_list': static_metrics['long_parameter_list'],
                    })
                    
                    logger.info("Successfully extracted JSON from response")
                    return CodeAnalysisResult(**result_dict), tokens_used
                except Exception as e2:
                    logger.error(f"Failed to parse extracted JSON: {e2}")
            
            # Log failed analysis for JSON decode error
            self._log_failed_analysis(e, entity_name, entity_type, language, self.provider, self.model, prompt)
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            # Check if it's a Pydantic validation error for code_fingerprint
            error_str = str(e)
            if 'code_fingerprint' in error_str and 'Field required' in error_str:
                # Try to generate code_fingerprint and retry
                logger.warning(f"Missing code_fingerprint in LLM response, generating it")
                try:
                    # Extract result_dict from the error if possible, or create a minimal one
                    # This is a fallback - the main generation should happen before validation
                    normalized = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
                    normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
                    normalized = re.sub(r'\s+', ' ', normalized)
                    normalized = normalized.strip()
                    # If we can't recover, raise the original error
                    logger.error(f"Could not recover from code_fingerprint error: {e}")
                except:
                    pass
            # Log failed analysis
            self._log_failed_analysis(e, entity_name, entity_type, language, self.provider, self.model, prompt)
            logger.error(f"Error analyzing code: {e}")
            raise
    
    def _extract_json_from_ollama_response(self, text: str) -> str:
        """Extract JSON from Ollama response that might contain reasoning or other text
        
        Ollama models (especially qwen3) sometimes return reasoning or explanations
        before the JSON. This method extracts just the JSON part.
        """
        if not text or not text.strip():
            return text
        
        # Strategy 1: Look for JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Strategy 2: Find the first complete JSON object (handle nested objects)
        # This regex finds { ... } with proper nesting
        depth = 0
        start = -1
        for i, char in enumerate(text):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    json_str = text[start:i+1]
                    # Validate it's valid JSON structure
                    if json_str.count('{') == json_str.count('}'):
                        return json_str
        
        # Strategy 3: Remove common prefixes and find JSON
        # Remove text like "<think>", "<think>", or reasoning blocks
        cleaned = re.sub(r'^[^{]*', '', text, flags=re.DOTALL)
        cleaned = cleaned.strip()
        
        # Try to find JSON object
        if cleaned.startswith('{'):
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(cleaned):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return cleaned[:i+1]
        
        # If nothing found, return original (will fail with better error message)
        return text
    
    def _fix_json_response(self, text: str) -> str:
        """Fix common JSON issues in LLM responses"""
        # Remove markdown code block markers if present
        text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
        
        # Try to fix invalid escape sequences in JSON strings
        # The issue is that GigaChat sometimes returns strings with unescaped backslashes
        # We need to fix escape sequences inside string values, but not outside
        
        # First, try to find and fix escape sequences in string values
        # This regex finds string values and fixes invalid escapes
        def fix_string_escapes(match):
            """Fix escape sequences inside a JSON string value"""
            content = match.group(1)
            # Fix invalid escape sequences (like \' or \. or \s)
            # But preserve valid ones (\\, \", \/, \b, \f, \n, \r, \t, \uXXXX)
            # Replace any backslash not followed by valid escape char with double backslash
            fixed = re.sub(r'\\(?![\\/bfnrt"u0123456789abcdefABCDEF])', r'\\\\', content)
            return f'"{fixed}"'
        
        # Match JSON string values (content between quotes)
        # This is a simplified approach - we match "..." but need to handle escaped quotes
        # For now, use a more aggressive fix: replace invalid escapes globally
        # but only inside what looks like string content
        
        # Better approach: use a state machine to track if we're inside a string
        # For simplicity, just fix common patterns:
        # 1. Fix \' -> ' (single quote doesn't need escaping in JSON)
        # 2. Fix \. -> . (period doesn't need escaping)
        # 3. Fix \s -> s (space doesn't need escaping)
        # 4. Fix any other invalid escape (except valid ones) by doubling the backslash
        
        # More careful: only fix escapes that are definitely invalid
        # Valid JSON escapes: \\, \/, \b, \f, \n, \r, \t, \", \uXXXX
        # Invalid: anything else after \
        
        # Use a more sophisticated approach: parse character by character
        # But for now, use regex that's more careful
        # Fix: \ followed by a character that's not a valid escape sequence
        # But we need to be inside a string, not in the JSON structure itself
        
        # Simplified: fix all invalid escapes, but be careful about context
        # Replace \ followed by invalid escape char with the char itself (remove the backslash)
        # OR double the backslash to make it a literal backslash
        
        # Actually, the safest approach: try to parse, and if it fails, 
        # try progressively more aggressive fixes
        
        # Fix invalid escape sequences in JSON strings
        # Valid JSON escapes: \\, \/, \b, \f, \n, \r, \t, \", \uXXXX
        # Invalid escapes (like \' or \. or \s) should be fixed
        
        # Strategy: Remove backslashes that are not part of valid escape sequences
        # This handles cases where GigaChat returns \' (should be ') or \. (should be .)
        # We remove the backslash, leaving the literal character
        
        # But we need to be careful: we only want to fix escapes inside string values
        # For simplicity, we'll fix all invalid escapes globally
        # Pattern: \ followed by a character that's NOT a valid escape sequence
        # Valid escapes: \\, \/, \b, \f, \n, \r, \t, \", \u (followed by 4 hex digits)
        
        # First pass: fix common invalid escapes by removing the backslash
        # This handles \', \., \s, etc. - they become ', ., s
        text = re.sub(r'\\(?![\\/bfnrt"u0-9a-fA-F])', '', text)
        
        # Second pass: if we have \u not followed by 4 hex digits, fix it
        # This handles incomplete unicode escapes
        text = re.sub(r'\\u(?![\dA-Fa-f]{4})', 'u', text)
        
        return text.strip()
    
    def _fix_unterminated_strings(self, text: str) -> str:
        """Fix unterminated strings in JSON by closing unclosed quotes"""
        result = []
        in_string = False
        escape_next = False
        string_start = -1
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if escape_next:
                escape_next = False
                result.append(char)
            elif char == '\\':
                escape_next = True
                result.append(char)
            elif char == '"':
                if not in_string:
                    # Opening quote
                    in_string = True
                    string_start = i
                    result.append(char)
                else:
                    # Closing quote
                    in_string = False
                    string_start = -1
                    result.append(char)
            elif in_string:
                # Inside a string
                result.append(char)
            else:
                # Outside a string
                result.append(char)
            
            i += 1
        
        # If we're still in a string at the end, close it
        if in_string:
            result.append('"')
        
        return ''.join(result)
    
    def _fix_missing_commas(self, text: str) -> str:
        """Fix missing commas in JSON by adding them where needed"""
        result = []
        i = 0
        in_string = False
        escape_next = False
        last_char = None
        
        while i < len(text):
            char = text[i]
            
            if escape_next:
                escape_next = False
                result.append(char)
                last_char = char
            elif char == '\\':
                escape_next = True
                result.append(char)
            elif char == '"':
                in_string = not in_string
                result.append(char)
                last_char = char
            elif in_string:
                result.append(char)
                last_char = char
            else:
                # Outside string - check if we need to add a comma
                if char in ['"', '{', '[']:
                    # Before opening quote, brace, or bracket
                    if last_char in ['"', '}', ']', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'e', 'E', '+', '-', '.']:
                        # Need comma before: "value"{ -> "value",{
                        # Check if there's already whitespace or comma
                        if i > 0 and text[i-1] not in [',', ' ', '\n', '\t', '\r', '{', '[', ':']:
                            result.append(',')
                elif char in ['}', ']']:
                    # Before closing brace or bracket
                    if last_char in ['"', '}', ']', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'e', 'E', '+', '-', '.']:
                        # Need comma if there's another value after
                        # Look ahead to see if there's a key or value
                        j = i + 1
                        while j < len(text) and text[j] in [' ', '\n', '\t', '\r']:
                            j += 1
                        if j < len(text) and text[j] in ['"', '{', '[', '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                            # There's another value, need comma
                            if i > 0 and text[i-1] not in [',', ' ', '\n', '\t', '\r', '{', '[', ':']:
                                result.append(',')
                
                result.append(char)
                if char not in [' ', '\n', '\t', '\r']:
                    last_char = char
            
            i += 1
        
        return ''.join(result)
    
    def _fix_json_response_aggressive(self, text: str) -> str:
        """More aggressive JSON fixing for cases where standard fix doesn't work"""
        # Remove all invalid escape sequences more aggressively
        # This is a fallback when standard fix doesn't work
        
        # First, try to fix unterminated strings
        text = self._fix_unterminated_strings(text)
        
        # Then, try to fix missing commas
        text = self._fix_missing_commas(text)
        
        # Strategy: process character by character, tracking if we're inside a string
        result = []
        in_string = False
        escape_next = False
        i = 0
        
        while i < len(text):
            char = text[i]
            
            if escape_next:
                # We're processing an escape sequence
                if char == '"':
                    result.append('\\"')
                elif char == '\\':
                    result.append('\\\\')
                elif char in 'bfnrt':
                    result.append(f'\\{char}')
                elif char == 'u' and i + 4 < len(text) and all(c in '0123456789abcdefABCDEF' for c in text[i+1:i+5]):
                    # Valid unicode escape
                    result.append(text[i-1:i+5])
                    i += 4
                else:
                    # Invalid escape - remove the backslash, keep the character
                    result.append(char)
                escape_next = False
            elif char == '\\':
                escape_next = True
            elif char == '"' and (i == 0 or text[i-1] != '\\' or (i > 1 and text[i-2] == '\\')):
                # Toggle string state (handle escaped quotes)
                in_string = not in_string
                result.append(char)
            else:
                result.append(char)
            
            i += 1
        
        return ''.join(result)
    
    def _build_prompt(
        self,
        code: str,
        language: str,
        entity_type: str,
        entity_name: str,
        context: Optional[str],
        ui_language: str = "EN",
        static_metrics: Optional[Dict] = None
    ) -> str:
        """Build analysis prompt for LLM with static metrics context"""
        
        # Language-specific instructions
        lang_instructions = {
            "RU": {
                "intro": "Вы эксперт по анализу кода. Проанализируйте следующий",
                "description": "Краткое описание того, что делает этот код (2-3 предложения)",
                "context_label": "КОНТЕКСТ (связанный код и зависимости)",
                "return_lang": "Верните ответ ТОЛЬКО в формате JSON, без markdown форматирования или блоков кода",
                "provide_analysis": "Предоставьте детальный анализ в формате JSON со следующей структурой:",
                "complexity_explanation": "Объясните почему такая сложность",
                "violation_description": "Подробное объяснение нарушения",
                "how_to_fix": "Как исправить (опционально)",
                "fingerprint_desc": "нормализованный код без имен переменных, комментариев и пробелов для поиска похожих участков",
                "important": "Важно:",
                "normalize": "Для code_fingerprint нормализуйте код: удалите имена переменных (замените на общие имена), удалите комментарии, нормализуйте пробелы",
                "thorough": "Будьте тщательны в анализе SOLID",
                "specific": "Будьте конкретны относительно паттернов проектирования, если они присутствуют",
                "testability_note": "Для тестируемости учитывайте: зависимости, побочные эффекты, связанность, тестируемость только публичных методов"
            },
            "EN": {
                "intro": "You are an expert code analyzer. Analyze the following",
                "description": "Brief description of what this code does (2-3 sentences)",
                "context_label": "CONTEXT (related code and dependencies)",
                "return_lang": "Return ONLY valid JSON, no markdown formatting or code blocks",
                "provide_analysis": "Provide a detailed analysis in JSON format with the following structure:",
                "complexity_explanation": "Explain why this complexity",
                "violation_description": "Detailed explanation of the violation",
                "how_to_fix": "How to fix (optional)",
                "fingerprint_desc": "normalized code without variable names, comments, and whitespace for similarity detection",
                "important": "Important:",
                "normalize": "For code_fingerprint, normalize the code: remove variable names (replace with generic names), remove comments, normalize whitespace",
                "thorough": "Be thorough in SOLID analysis",
                "specific": "Be specific about design patterns if any are present",
                "testability_note": "For testability, consider: dependencies, side effects, coupling, testability of public methods only"
            }
        }
        
        instructions = lang_instructions.get(ui_language, lang_instructions["EN"])
        
        context_section = ""
        if context:
            # Truncate context if too long (to avoid token limits)
            max_context_length = 3000  # characters
            if len(context) > max_context_length:
                context = context[:max_context_length] + "\n... (context truncated)"
            
            context_section = f"""
{instructions['context_label']}:
```{language}
{context}
```

Используйте этот контекст для более точного понимания того, что делает анализируемый код. Учитывайте:
- Родительские классы и их функциональность
- Реализуемые интерфейсы и их контракты
- Используемые классы и методы
- Описания зависимых сущностей
"""
        
        # Adjust instructions based on entity type
        entity_type_desc = {
            'constant': 'constant' if ui_language == 'EN' else 'константу',
            'enum': 'enum value' if ui_language == 'EN' else 'значение enum',
            'dict': 'dictionary/configuration' if ui_language == 'EN' else 'словарь/конфигурацию'
        }
        
        entity_desc = entity_type_desc.get(entity_type, entity_type)
        
        # Add static metrics section
        metrics_section = ""
        if static_metrics:
            metrics_info = []
            if static_metrics.get('lines_of_code'):
                metrics_info.append(f"Lines of Code: {static_metrics['lines_of_code']}")
            if static_metrics.get('cyclomatic_complexity'):
                metrics_info.append(f"Cyclomatic Complexity: {static_metrics['cyclomatic_complexity']}")
            if static_metrics.get('cognitive_complexity'):
                metrics_info.append(f"Cognitive Complexity: {static_metrics['cognitive_complexity']}")
            if static_metrics.get('max_nesting_depth'):
                metrics_info.append(f"Max Nesting Depth: {static_metrics['max_nesting_depth']}")
            if static_metrics.get('parameter_count'):
                metrics_info.append(f"Parameter Count: {static_metrics['parameter_count']}")
            if static_metrics.get('n_plus_one_queries'):
                metrics_info.append(f"N+1 Query Issues: {len(static_metrics['n_plus_one_queries'])}")
            if static_metrics.get('security_issues'):
                metrics_info.append(f"Security Issues: {len(static_metrics['security_issues'])}")
            if static_metrics.get('is_god_object'):
                metrics_info.append("God Object Detected: Yes")
            
            if metrics_info:
                metrics_section = f"""
STATIC METRICS (computed automatically):
{chr(10).join(metrics_info)}

Use these metrics to inform your analysis. For example:
- High cyclomatic complexity suggests the code may be doing too much
- N+1 query issues indicate performance problems
- Security issues require immediate attention
- God objects violate Single Responsibility Principle
"""
        
        # Special instructions for constants/enum/dict
        special_instructions = ""
        if entity_type == 'constant':
            if ui_language == 'RU':
                special_instructions = "\nВАЖНО: Это константа. В описании укажите:\n- Что хранит эта константа\n- Где и как она используется\n- Какое значение она содержит и зачем оно нужно"
            else:
                special_instructions = "\nIMPORTANT: This is a constant. In the description, specify:\n- What this constant stores\n- Where and how it is used\n- What value it contains and why it's needed"
        elif entity_type in ['enum', 'dict']:
            if ui_language == 'RU':
                special_instructions = "\nВАЖНО: Это значение enum/словаря. В описании укажите:\n- Что представляет это значение\n- Где оно используется\n- Какое значение оно имеет и для чего предназначено"
            else:
                special_instructions = "\nIMPORTANT: This is an enum/dict value. In the description, specify:\n- What this value represents\n- Where it is used\n- What value it has and what it's for"
        
        return f"""{instructions['intro']} {language} {entity_desc} named "{entity_name}".

CODE:
```{language}
{code}
```
{context_section}
{metrics_section}
{special_instructions}
{instructions['provide_analysis']}

{{
  "description": "{instructions['description']}",
  
  "complexity": "O(1)" | "O(log n)" | "O(n)" | "O(n log n)" | "O(n^2)" | "O(n^3)" | "O(2^n)" | "O(n!)",
  "complexity_explanation": "{instructions['complexity_explanation']}",
  
  IMPORTANT COMPLEXITY RULES:
  - For constants, enum values, and dict values: ALWAYS use "O(1)" (they are just value definitions)
  - Use O(1) for code with NO loops, NO recursion, and fixed number of operations (even if string operations like split/explode are used on bounded inputs)
  - Use O(n) only when complexity grows with the SIZE of input data structures (arrays, lists, collections), NOT string length for simple parsing
  - String operations like split/explode on fixed-format strings should be considered O(1) unless the string length is the primary variable
  - O(n) should be used for loops that iterate over arrays/lists where n is the number of elements
  - O(log n) for binary search, tree operations
  - O(n^2) for nested loops over collections
  
  "solid_violations": [
    {{
      "principle": "Single Responsibility Principle" | "Open/Closed Principle" | "Liskov Substitution Principle" | "Interface Segregation Principle" | "Dependency Inversion Principle",
      "description": "{instructions['violation_description']}",
      "severity": "low" | "medium" | "high",
      "suggestion": "{instructions['how_to_fix']}"
    }}
  ],
  NOTE: For constants, enum values, and dict values, "solid_violations" should be an empty array [] (they don't have SOLID violations).
  
  "design_patterns": ["Factory", "Strategy", "Observer", "Singleton", "Repository", etc.],
  NOTE: For constants, enum values, and dict values, "design_patterns" should be an empty array [].
  
  "ddd_role": "Entity" | "ValueObject" | "AggregateRoot" | "Service" | "Repository" | "DomainEvent" | null,
  "mvc_role": "Model" | "View" | "Controller" | null,
  
  "is_testable": true | false,
  "testability_score": 0.0-1.0,
  NOTE: For constants, enum values, and dict values, use "is_testable": true, "testability_score": 1.0, "testability_issues": [].
  "testability_issues": ["Global state dependency", "Hard-coded values", "Tight coupling", etc.],
  
  "code_fingerprint": "{instructions['fingerprint_desc']}",
  "dependencies": ["ClassName", "function_name", "module_name", etc.]
}}

{instructions['important']}
- {instructions['return_lang']}
- {instructions['normalize']}
- {instructions['thorough']}
- {instructions['specific']}
- {instructions['testability_note']}"""
    
    def get_context_window_size(self) -> int:
        """Get context window size for current model"""
        # Default context windows (approximate)
        context_windows = {
            "gpt-4-turbo-preview": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "deepseek-coder:33b": 16384,
            "llama3.1:70b": 131072,
        }
        return context_windows.get(self.model, 8192)  # Default fallback

