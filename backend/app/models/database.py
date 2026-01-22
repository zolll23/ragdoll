from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float, Boolean, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False, unique=True)
    language = Column(String(50), nullable=False)  # php, python
    ui_language = Column(String(10), nullable=False, default="EN")  # EN, RU
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexing state
    is_indexing = Column(Boolean, default=False, nullable=False)
    indexing_task_id = Column(String(255), nullable=True)  # Celery task ID
    last_indexed_file_path = Column(String(512), nullable=True)  # Resume from this file
    current_file_path = Column(String(512), nullable=True)  # Current file being indexed
    indexing_status = Column(Text, nullable=True)  # Current status message
    
    # Progress tracking
    total_files = Column(Integer, default=0, nullable=False)
    indexed_files = Column(Integer, default=0, nullable=False)
    total_entities = Column(Integer, default=0, nullable=False)
    
    # Token usage tracking
    tokens_used = Column(Integer, default=0, nullable=False)  # Total tokens used for indexing
    
    # Failed entities reindexing state
    is_reindexing_failed = Column(Boolean, default=False, nullable=False)
    reindexing_failed_task_id = Column(String(255), nullable=True)  # Celery task ID for reindexing failed
    failed_entities_count = Column(Integer, default=0, nullable=False)  # Total failed entities found
    reindexed_failed_count = Column(Integer, default=0, nullable=False)  # Number of failed entities reindexed
    reindexing_failed_status = Column(Text, nullable=True)  # Status message for reindexing failed
    
    files = relationship("File", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_project_path', 'path'),
    )


class File(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    path = Column(String(512), nullable=False)
    hash = Column(String(64), nullable=False)
    last_modified = Column(DateTime, nullable=False)
    indexed_at = Column(DateTime)
    
    project = relationship("Project", back_populates="files")
    entities = relationship("Entity", back_populates="file", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_file_project_path', 'project_id', 'path'),
        Index('idx_file_hash', 'hash'),
    )


class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)  # class, method, function
    name = Column(String(255), nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    visibility = Column(String(20))  # public, private, protected
    code = Column(Text, nullable=False)
    full_qualified_name = Column(Text)  # e.g., "ClassName.method_name" (can be very long)
    
    file = relationship("File", back_populates="entities")
    analysis = relationship("Analysis", back_populates="entity", uselist=False, cascade="all, delete-orphan")
    dependencies = relationship(
        "Dependency", 
        foreign_keys="Dependency.entity_id",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index('idx_entity_file_type', 'file_id', 'type'),
        Index('idx_entity_name', 'name'),
        Index('idx_entity_fqn', 'full_qualified_name'),
    )


class Analysis(Base):
    __tablename__ = "analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    
    # Complexity
    complexity = Column(String(50), nullable=False)  # O(1), O(n), O(n^2), etc.
    complexity_numeric = Column(Float, nullable=False)  # For sorting: 1, 2, 3, 4, etc.
    complexity_explanation = Column(Text, nullable=True)
    
    # SOLID violations
    solid_violations = Column(JSON, default=list)
    
    # Architecture
    design_patterns = Column(JSON, default=list)
    ddd_role = Column(String(100))
    mvc_role = Column(String(100))
    
    # Testability
    is_testable = Column(Boolean, nullable=False)
    testability_score = Column(Float, nullable=False)
    testability_issues = Column(JSON, default=list)
    
    # For similarity detection
    code_fingerprint = Column(Text, nullable=False)
    
    # Embedding ID in Qdrant
    embedding_id = Column(String(255))
    
    # Keywords for better semantic search (synonyms, related terms, etc.)
    keywords = Column(Text, nullable=True)  # Comma-separated or JSON array of keywords
    
    # Size metrics
    lines_of_code = Column(Integer, default=0, nullable=True)
    cyclomatic_complexity = Column(Integer, default=1, nullable=True)
    cognitive_complexity = Column(Integer, default=0, nullable=True)
    max_nesting_depth = Column(Integer, default=0, nullable=True)
    parameter_count = Column(Integer, default=0, nullable=True)
    
    # Coupling and cohesion metrics
    coupling_score = Column(Float, default=0.0, nullable=True)
    cohesion_score = Column(Float, default=1.0, nullable=True)
    afferent_coupling = Column(Integer, default=0, nullable=True)  # входящие зависимости
    efferent_coupling = Column(Integer, default=0, nullable=True)  # исходящие зависимости
    
    # Performance metrics
    n_plus_one_queries = Column(JSON, default=list, nullable=True)
    space_complexity = Column(String(50), default="O(1)", nullable=True)
    hot_path_detected = Column(Boolean, default=False, nullable=True)
    
    # Security metrics
    security_issues = Column(JSON, default=list, nullable=True)
    hardcoded_secrets = Column(JSON, default=list, nullable=True)
    insecure_dependencies = Column(JSON, default=list, nullable=True)
    
    # Architecture metrics
    is_god_object = Column(Boolean, default=False, nullable=True)
    feature_envy_score = Column(Float, default=0.0, nullable=True)
    data_clumps = Column(JSON, default=list, nullable=True)
    long_parameter_list = Column(Boolean, default=False, nullable=True)
    
    entity = relationship("Entity", back_populates="analysis")
    
    __table_args__ = (
        Index('idx_analysis_complexity', 'complexity_numeric'),
        Index('idx_analysis_testable', 'is_testable', 'testability_score'),
        Index('idx_analysis_cyclomatic', 'cyclomatic_complexity'),
        Index('idx_analysis_security', 'security_issues'),
    )


class Dependency(Base):
    __tablename__ = "dependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    depends_on_entity_id = Column(Integer, ForeignKey("entities.id", ondelete="SET NULL"), nullable=True)
    depends_on_name = Column(String(255), nullable=False)
    type = Column(String(50))  # import, extends, implements, calls
    
    __table_args__ = (
        Index('idx_dependency_entity', 'entity_id'),
        Index('idx_dependency_name', 'depends_on_name'),
    )

