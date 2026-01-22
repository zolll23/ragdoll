from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from enum import Enum


class ComplexityClass(str, Enum):
    CONSTANT = "O(1)"
    LOGARITHMIC = "O(log n)"
    LINEAR = "O(n)"
    LINEARITHMIC = "O(n log n)"
    QUADRATIC = "O(n^2)"
    CUBIC = "O(n^3)"
    EXPONENTIAL = "O(2^n)"
    FACTORIAL = "O(n!)"


class SOLIDPrinciple(str, Enum):
    SRP = "Single Responsibility Principle"
    OCP = "Open/Closed Principle"
    LSP = "Liskov Substitution Principle"
    ISP = "Interface Segregation Principle"
    DIP = "Dependency Inversion Principle"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SOLIDViolation(BaseModel):
    principle: SOLIDPrinciple
    description: str
    severity: Severity
    suggestion: Optional[str] = None


class SecurityIssue(BaseModel):
    """Security issue detected in code"""
    type: Literal["sql_injection", "xss", "hardcoded_secret", "insecure_dependency"]
    severity: Severity
    description: str
    location: str  # строка кода или контекст
    suggestion: Optional[str] = None


class CodeAnalysisResult(BaseModel):
    """Structured output from AI agent with extended metrics"""
    
    description: str = Field(description="What this code does (2-3 sentences)")
    
    complexity: ComplexityClass
    complexity_explanation: str
    
    solid_violations: List[SOLIDViolation] = Field(default_factory=list)
    
    design_patterns: List[str] = Field(default_factory=list)
    ddd_role: Optional[str] = None
    mvc_role: Optional[str] = None
    
    is_testable: bool
    testability_score: float = Field(ge=0.0, le=1.0)
    testability_issues: List[str] = Field(default_factory=list)
    
    code_fingerprint: str = Field(default="")
    dependencies: List[str] = Field(default_factory=list)
    
    # Size metrics
    lines_of_code: int = Field(default=0, ge=0)
    cyclomatic_complexity: int = Field(default=1, ge=1)
    cognitive_complexity: int = Field(default=0, ge=0)
    max_nesting_depth: int = Field(default=0, ge=0)
    parameter_count: int = Field(default=0, ge=0)
    
    # Coupling and cohesion metrics
    coupling_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cohesion_score: float = Field(default=1.0, ge=0.0, le=1.0)
    afferent_coupling: int = Field(default=0, ge=0)  # входящие зависимости
    efferent_coupling: int = Field(default=0, ge=0)  # исходящие зависимости
    
    # Performance metrics
    n_plus_one_queries: List[str] = Field(default_factory=list)
    space_complexity: str = Field(default="O(1)")
    hot_path_detected: bool = Field(default=False)
    
    # Security metrics
    security_issues: List[SecurityIssue] = Field(default_factory=list)
    hardcoded_secrets: List[str] = Field(default_factory=list)
    insecure_dependencies: List[str] = Field(default_factory=list)
    
    # Architecture metrics
    is_god_object: bool = Field(default=False)
    feature_envy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    data_clumps: List[str] = Field(default_factory=list)
    long_parameter_list: bool = Field(default=False)


# Request/Response models

class ProjectCreate(BaseModel):
    name: str
    path: str
    language: Literal["php", "python"]
    ui_language: Literal["EN", "RU"] = "EN"


class ProjectResponse(BaseModel):
    id: int
    name: str
    path: str
    language: str
    ui_language: str
    created_at: datetime
    updated_at: datetime
    is_indexing: Optional[bool] = False
    indexing_task_id: Optional[str] = None
    last_indexed_file_path: Optional[str] = None
    total_files: Optional[int] = 0
    indexed_files: Optional[int] = 0
    total_entities: Optional[int] = 0
    tokens_used: Optional[int] = 0
    
    class Config:
        from_attributes = True


class ProjectProgressResponse(BaseModel):
    """Project indexing progress"""
    project_id: int
    total_files: int
    indexed_files: int
    total_entities: int
    progress_percent: float
    is_indexing: bool
    current_file: Optional[str] = None
    status_message: Optional[str] = None
    # Analysis status
    entities_with_analysis: Optional[int] = 0
    entities_with_failed_analysis: Optional[int] = 0
    entities_without_analysis: Optional[int] = 0
    # Failed entities reindexing info
    is_reindexing_failed: Optional[bool] = False
    failed_entities_count: Optional[int] = 0
    reindexed_failed_count: Optional[int] = 0
    reindexing_failed_status: Optional[str] = None


class EntityResponse(BaseModel):
    id: int
    type: str
    name: str
    start_line: int
    end_line: int
    visibility: Optional[str]
    full_qualified_name: Optional[str]
    file_path: str
    code: Optional[str] = None
    has_analysis: bool = False
    complexity: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    id: Optional[int] = None
    description: str
    complexity: str
    complexity_explanation: Optional[str] = None
    complexity_numeric: float
    solid_violations: List[Dict[str, Any]]
    design_patterns: List[str]
    ddd_role: Optional[str]
    mvc_role: Optional[str]
    is_testable: bool
    testability_score: float
    testability_issues: List[str]
    entity: EntityResponse
    
    # Extended metrics (optional for backward compatibility)
    lines_of_code: Optional[int] = None
    cyclomatic_complexity: Optional[int] = None
    cognitive_complexity: Optional[int] = None
    max_nesting_depth: Optional[int] = None
    parameter_count: Optional[int] = None
    coupling_score: Optional[float] = None
    cohesion_score: Optional[float] = None
    afferent_coupling: Optional[int] = None
    efferent_coupling: Optional[int] = None
    n_plus_one_queries: Optional[List[str]] = None
    space_complexity: Optional[str] = None
    hot_path_detected: Optional[bool] = None
    security_issues: Optional[List[Dict[str, Any]]] = None
    hardcoded_secrets: Optional[List[str]] = None
    insecure_dependencies: Optional[List[str]] = None
    is_god_object: Optional[bool] = None
    feature_envy_score: Optional[float] = None
    data_clumps: Optional[List[str]] = None
    long_parameter_list: Optional[bool] = None
    keywords: Optional[str] = None  # Keywords for semantic search
    
    class Config:
        from_attributes = True


class SearchQuery(BaseModel):
    query: str
    project_id: Optional[int] = None
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SearchResult(BaseModel):
    entity: EntityResponse
    analysis: Optional[AnalysisResponse]
    score: float
    match_type: str  # "semantic", "structured", "hybrid"


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str


# LLM Provider models
class LLMProviderCreate(BaseModel):
    name: str  # ollama, openai, anthropic, gigachat
    display_name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None  # Default model for this provider
    is_active: bool = True
    is_default: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)


class LLMProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class LLMProviderResponse(BaseModel):
    id: int
    name: str
    display_name: str
    base_url: Optional[str]
    api_key: Optional[str] = None  # Only return if requested
    model: Optional[str] = None
    is_active: bool
    is_default: bool
    config: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str


class ProviderModelsResponse(BaseModel):
    provider: str
    models: List[ModelInfo]
    available: bool
    error: Optional[str] = None


class CurrentProviderInfo(BaseModel):
    provider_name: Optional[str]
    model_name: Optional[str]


class DependencyResponse(BaseModel):
    """Dependency information"""
    id: int
    depends_on_entity_id: Optional[int]
    depends_on_name: str
    type: str  # import, extends, implements, calls
    depends_on_entity: Optional[EntityResponse] = None  # Full entity info if found
    depends_on_analysis: Optional[AnalysisResponse] = None  # Analysis of dependent entity
    
    class Config:
        from_attributes = True


class SimilarCodeResponse(BaseModel):
    """Similar code block for refactoring suggestions"""
    entity: EntityResponse
    analysis: Optional[AnalysisResponse]
    similarity_score: float  # 0.0-1.0 based on code_fingerprint similarity
    
    class Config:
        from_attributes = True

