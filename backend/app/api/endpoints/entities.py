from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict
import re
from difflib import SequenceMatcher
import hashlib

from app.core.database import get_db
from app.models.database import Entity, Analysis, File, Dependency
from app.api.models.schemas import EntityResponse, AnalysisResponse, DependencyResponse, SimilarCodeResponse
from sqlalchemy import func

router = APIRouter(prefix="/api/entities", tags=["entities"])


def _convert_complexity(complexity: Optional[str]) -> str:
    """Convert ComplexityClass.* enum string to O(1), O(n), etc."""
    if not complexity:
        return "O(n)"
    if complexity.startswith('ComplexityClass.'):
        complexity_map = {
            'ComplexityClass.CONSTANT': 'O(1)',
            'ComplexityClass.LOGARITHMIC': 'O(log n)',
            'ComplexityClass.LINEAR': 'O(n)',
            'ComplexityClass.LINEARITHMIC': 'O(n log n)',
            'ComplexityClass.QUADRATIC': 'O(n^2)',
            'ComplexityClass.CUBIC': 'O(n^3)',
            'ComplexityClass.EXPONENTIAL': 'O(2^n)',
            'ComplexityClass.FACTORIAL': 'O(n!)'
        }
        return complexity_map.get(complexity, 'O(n)')
    return complexity


@router.get("/{entity_id}", response_model=EntityResponse)
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    """Get entity by ID"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    file = db.query(File).filter(File.id == entity.file_id).first()
    
    return EntityResponse(
        id=entity.id,
        type=entity.type,
        name=entity.name,
        start_line=entity.start_line,
        end_line=entity.end_line,
        visibility=entity.visibility,
        full_qualified_name=entity.full_qualified_name,
        file_path=file.path if file else "",
        code=entity.code
    )


@router.get("/{entity_id}/analysis", response_model=AnalysisResponse)
def get_entity_analysis(entity_id: int, db: Session = Depends(get_db)):
    """Get analysis for entity"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    file = db.query(File).filter(File.id == entity.file_id).first()
    entity_response = EntityResponse(
        id=entity.id,
        type=entity.type,
        name=entity.name,
        start_line=entity.start_line,
        end_line=entity.end_line,
        visibility=entity.visibility,
        full_qualified_name=entity.full_qualified_name,
        file_path=file.path if file else "",
        code=entity.code
    )
    
    analysis = db.query(Analysis).filter(Analysis.entity_id == entity_id).first()
    if not analysis:
        # Return response with null analysis fields if analysis doesn't exist
        return AnalysisResponse(
            id=None,
            description="Analysis not available",
            complexity="O(1)",
            complexity_numeric=1.0,
            solid_violations=[],
            design_patterns=[],
            ddd_role=None,
            mvc_role=None,
            is_testable=False,
            testability_score=0.0,
            testability_issues=["Analysis not available"],
            entity=entity_response
        )
    
    return AnalysisResponse(
        id=analysis.id,
        description=analysis.description,
        complexity=_convert_complexity(analysis.complexity),
        complexity_explanation=analysis.complexity_explanation,
        complexity_numeric=analysis.complexity_numeric,
        solid_violations=analysis.solid_violations or [],
        design_patterns=analysis.design_patterns or [],
        ddd_role=analysis.ddd_role,
        mvc_role=analysis.mvc_role,
        is_testable=analysis.is_testable,
        testability_score=analysis.testability_score,
        testability_issues=analysis.testability_issues or [],
        entity=entity_response,
        # Extended metrics
        lines_of_code=analysis.lines_of_code,
        cyclomatic_complexity=analysis.cyclomatic_complexity,
        cognitive_complexity=analysis.cognitive_complexity,
        max_nesting_depth=analysis.max_nesting_depth,
        parameter_count=analysis.parameter_count,
        coupling_score=analysis.coupling_score,
        cohesion_score=analysis.cohesion_score,
        afferent_coupling=analysis.afferent_coupling,
        efferent_coupling=analysis.efferent_coupling,
        n_plus_one_queries=analysis.n_plus_one_queries or [],
        space_complexity=analysis.space_complexity,
        hot_path_detected=analysis.hot_path_detected,
        security_issues=analysis.security_issues or [],
        hardcoded_secrets=analysis.hardcoded_secrets or [],
        insecure_dependencies=analysis.insecure_dependencies or [],
        is_god_object=analysis.is_god_object,
        feature_envy_score=analysis.feature_envy_score,
        data_clumps=analysis.data_clumps or [],
        long_parameter_list=analysis.long_parameter_list,
        keywords=analysis.keywords
    )


@router.get("/", response_model=List[EntityResponse])
def list_entities(
    project_id: Optional[int] = Query(None),
    file_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    name: Optional[str] = Query(None, description="Search entities by name (partial match)"),
    failed_analysis: Optional[bool] = Query(None, description="Filter by failed analysis status"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List entities with filters"""
    query = db.query(Entity).join(File).outerjoin(Analysis).options(joinedload(Entity.analysis))
    
    if project_id:
        query = query.filter(File.project_id == project_id)
    
    if file_id:
        query = query.filter(Entity.file_id == file_id)
    
    if name:
        # Search by name or full_qualified_name
        query = query.filter(
            (Entity.name.ilike(f'%{name}%')) |
            (Entity.full_qualified_name.ilike(f'%{name}%'))
        )
    
    if entity_type:
        if entity_type == 'enum':
            # Filter for enum case values (constants with :: in full_qualified_name)
            query = query.filter(
                Entity.type == 'constant',
                Entity.full_qualified_name.like('%::%')
            )
        else:
            query = query.filter(Entity.type == entity_type)
    
    if failed_analysis is not None:
        if failed_analysis:
            # Only entities with failed analysis
            query = query.filter(Analysis.description == 'Analysis failed')
        else:
            # Only entities with successful analysis (exclude failed and no analysis)
            query = query.filter(
                Analysis.description.isnot(None),
                Analysis.description != 'Analysis failed'
            )
    
    entities = query.offset(offset).limit(limit).all()
    
    results = []
    for entity in entities:
        file = db.query(File).filter(File.id == entity.file_id).first()
        analysis = entity.analysis
        results.append(EntityResponse(
            id=entity.id,
            type=entity.type,
            name=entity.name,
            start_line=entity.start_line,
            end_line=entity.end_line,
            visibility=entity.visibility,
            full_qualified_name=entity.full_qualified_name,
            file_path=file.path if file else "",
            code=entity.code,
            has_analysis=analysis is not None,
            complexity=_convert_complexity(analysis.complexity) if analysis else None,
            description=analysis.description[:200] + "..." if analysis and len(analysis.description) > 200 else (analysis.description if analysis else None)
        ))
    
    return results


@router.get("/{entity_id}/dependencies", response_model=List[DependencyResponse])
def get_entity_dependencies(entity_id: int, db: Session = Depends(get_db)):
    """Get dependencies for an entity (classes and methods it uses)"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    dependencies = db.query(Dependency).filter(Dependency.entity_id == entity_id).all()
    
    results = []
    for dep in dependencies:
        # Get full entity info if depends_on_entity_id is set
        depends_on_entity = None
        depends_on_analysis = None
        
        if dep.depends_on_entity_id:
            depends_on_entity_obj = db.query(Entity).filter(Entity.id == dep.depends_on_entity_id).first()
            if depends_on_entity_obj:
                depends_on_file = db.query(File).filter(File.id == depends_on_entity_obj.file_id).first()
                depends_on_entity = EntityResponse(
                    id=depends_on_entity_obj.id,
                    type=depends_on_entity_obj.type,
                    name=depends_on_entity_obj.name,
                    start_line=depends_on_entity_obj.start_line,
                    end_line=depends_on_entity_obj.end_line,
                    visibility=depends_on_entity_obj.visibility,
                    full_qualified_name=depends_on_entity_obj.full_qualified_name,
                    file_path=depends_on_file.path if depends_on_file else "",
                    code=depends_on_entity_obj.code
                )
                
                # Get analysis if available
                dep_analysis = db.query(Analysis).filter(Analysis.entity_id == dep.depends_on_entity_id).first()
                if dep_analysis:
                    depends_on_analysis = AnalysisResponse(
                        id=dep_analysis.id,
                        description=dep_analysis.description,
                        complexity=dep_analysis.complexity,
                        complexity_explanation=dep_analysis.complexity_explanation,
                        complexity_numeric=dep_analysis.complexity_numeric,
                        solid_violations=dep_analysis.solid_violations or [],
                        design_patterns=dep_analysis.design_patterns or [],
                        ddd_role=dep_analysis.ddd_role,
                        mvc_role=dep_analysis.mvc_role,
                        is_testable=dep_analysis.is_testable,
                        testability_score=dep_analysis.testability_score,
                        testability_issues=dep_analysis.testability_issues or [],
                        entity=depends_on_entity
                    )
        
        results.append(DependencyResponse(
            id=dep.id,
            depends_on_entity_id=dep.depends_on_entity_id,
            depends_on_name=dep.depends_on_name,
            type=dep.type,
            depends_on_entity=depends_on_entity,
            depends_on_analysis=depends_on_analysis
        ))
    
    return results


def _normalize_fingerprint(fingerprint: str) -> str:
    """Normalize fingerprint for comparison"""
    if not fingerprint:
        return ''
    # Remove all whitespace and convert to lowercase
    # Also normalize variable names to make comparison more robust
    normalized = re.sub(r'\s+', '', fingerprint.lower())
    # Replace variable names with placeholders to focus on structure
    normalized = re.sub(r'\$[a-zA-Z_][a-zA-Z0-9_]*', '$var', normalized)
    return normalized


def _calculate_fingerprint_similarity(fp1: str, fp2: str) -> float:
    """Calculate similarity between two fingerprints using sequence matching"""
    if not fp1 or not fp2:
        return 0.0
    
    # Use sequence matcher for similarity
    return SequenceMatcher(None, fp1, fp2).ratio()


@router.get("/{entity_id}/similar", response_model=List[SimilarCodeResponse])
def get_similar_code(
    entity_id: int,
    limit: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """Find similar code blocks for refactoring suggestions"""
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    analysis = db.query(Analysis).filter(Analysis.entity_id == entity_id).first()
    if not analysis:
        # If no analysis, use code directly as fingerprint
        target_fingerprint = entity.code
    else:
        target_fingerprint = analysis.code_fingerprint or entity.code
    
    if not target_fingerprint:
        return []
    
    # Normalize fingerprint for comparison (remove whitespace, lowercase)
    target_normalized = _normalize_fingerprint(target_fingerprint)
    
    # Find similar entities by comparing fingerprints
    # Get all entities of the same type
    if analysis:
        # If we have analysis, prefer entities with analysis
        all_analyses = db.query(Analysis, Entity).join(Entity).filter(
            Analysis.entity_id != entity_id,  # Exclude self
            Entity.type == entity.type  # Only same type (method vs method, class vs class)
        ).all()
    else:
        # If no analysis, compare code directly
        all_entities = db.query(Entity).filter(
            Entity.id != entity_id,
            Entity.type == entity.type,
            Entity.code.isnot(None)
        ).all()
        all_analyses = [(None, e) for e in all_entities]
    
    similar_results = []
    for analysis_obj, entity_obj in all_analyses:
        # Get fingerprint from analysis or use code directly
        if analysis_obj and analysis_obj.code_fingerprint:
            compare_fingerprint = analysis_obj.code_fingerprint
        elif entity_obj.code:
            compare_fingerprint = entity_obj.code
        else:
            continue
        
        # Calculate similarity using normalized fingerprints
        similarity = _calculate_fingerprint_similarity(
            target_normalized,
            _normalize_fingerprint(compare_fingerprint)
        )
        
        if similarity >= min_similarity:
            file = db.query(File).filter(File.id == entity_obj.file_id).first()
            
            # Build analysis response if available
            analysis_response = None
            if analysis_obj:
                analysis_response = AnalysisResponse(
                    id=analysis_obj.id,
                    description=analysis_obj.description,
                    complexity=_convert_complexity(analysis_obj.complexity),
                    complexity_explanation=analysis_obj.complexity_explanation,
                    complexity_numeric=analysis_obj.complexity_numeric,
                    solid_violations=analysis_obj.solid_violations or [],
                    design_patterns=analysis_obj.design_patterns or [],
                    ddd_role=analysis_obj.ddd_role,
                    mvc_role=analysis_obj.mvc_role,
                    is_testable=analysis_obj.is_testable,
                    testability_score=analysis_obj.testability_score,
                    testability_issues=analysis_obj.testability_issues or [],
                    entity=EntityResponse(
                        id=entity_obj.id,
                        type=entity_obj.type,
                        name=entity_obj.name,
                        start_line=entity_obj.start_line,
                        end_line=entity_obj.end_line,
                        visibility=entity_obj.visibility,
                        full_qualified_name=entity_obj.full_qualified_name,
                        file_path=file.path if file else "",
                        code=entity_obj.code
                    ),
                    keywords=analysis_obj.keywords
                )
            
            similar_results.append(SimilarCodeResponse(
                entity=EntityResponse(
                    id=entity_obj.id,
                    type=entity_obj.type,
                    name=entity_obj.name,
                    start_line=entity_obj.start_line,
                    end_line=entity_obj.end_line,
                    visibility=entity_obj.visibility,
                    full_qualified_name=entity_obj.full_qualified_name,
                    file_path=file.path if file else "",
                    code=entity_obj.code
                ),
                analysis=analysis_response,
                similarity_score=similarity
            ))
    
    # Sort by similarity and return top results
    similar_results.sort(key=lambda x: x.similarity_score, reverse=True)
    return similar_results[:limit]


def _extract_code_fragments(code: str, min_lines: int = 3, max_lines: int = 30) -> List[Dict]:
    """Extract code fragments from method code for comparison"""
    if not code:
        return []
    
    lines = code.split('\n')
    fragments = []
    seen_fragments = set()  # Track normalized fragments to avoid duplicates
    
    # Extract sliding windows of code (overlapping chunks)
    # This helps find similar code blocks of different sizes
    for window_size in range(min_lines, min(max_lines, len(lines)) + 1):
        for i in range(len(lines) - window_size + 1):
            window = lines[i:i+window_size]
            window_code = '\n'.join(window)
            
            # Skip very short or empty windows
            if len(window_code.strip()) < 20:
                continue
            
            # Normalize and check for duplicates
            normalized = _normalize_fingerprint(window_code)
            if normalized in seen_fragments:
                continue
            seen_fragments.add(normalized)
            
            fragments.append({
                'lines': window,
                'start_line': i,
                'end_line': i + window_size - 1,
                'code': window_code
            })
    
    # Also extract logical blocks (between braces, if/else, loops, etc.)
    current_block = []
    brace_level = 0
    block_start = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Track brace level
        brace_level += stripped.count('{') - stripped.count('}')
        
        # Start new block on control structures
        if any(stripped.startswith(kw) for kw in ['if', 'else', 'for', 'foreach', 'while', 'switch', 'try', 'catch']):
            if current_block and len(current_block) >= min_lines:
                block_code = '\n'.join(current_block)
                normalized = _normalize_fingerprint(block_code)
                if normalized not in seen_fragments:
                    seen_fragments.add(normalized)
                    fragments.append({
                        'lines': current_block,
                        'start_line': block_start,
                        'end_line': i - 1,
                        'code': block_code
                    })
            current_block = [line]
            block_start = i
        elif stripped and brace_level == 0 and current_block:
            # End of block
            current_block.append(line)
            if len(current_block) >= min_lines:
                block_code = '\n'.join(current_block)
                normalized = _normalize_fingerprint(block_code)
                if normalized not in seen_fragments:
                    seen_fragments.add(normalized)
                    fragments.append({
                        'lines': current_block,
                        'start_line': block_start,
                        'end_line': i,
                        'code': block_code
                    })
            current_block = []
        elif current_block or stripped:
            current_block.append(line)
    
    # Add remaining block
    if current_block and len(current_block) >= min_lines:
        block_code = '\n'.join(current_block)
        normalized = _normalize_fingerprint(block_code)
        if normalized not in seen_fragments:
            fragments.append({
                'lines': current_block,
                'start_line': block_start,
                'end_line': len(lines) - 1,
                'code': block_code
            })
    
    return fragments


@router.get("/similar/search", response_model=Dict)
def search_similar_code(
    project_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    min_similarity: float = Query(0.7, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Search for similar code pairs across the project for refactoring suggestions"""
    # Get all entities with code
    query = db.query(Entity, Analysis, File).join(File).outerjoin(Analysis)
    
    if project_id:
        query = query.filter(File.project_id == project_id)
    
    if entity_type:
        query = query.filter(Entity.type == entity_type)
    
    entities = query.filter(Entity.code.isnot(None)).all()
    
    # Build pairs of similar code (both full entities and fragments)
    similar_pairs = []
    seen_pairs = set()
    seen_code_hashes = set()  # Track code content to avoid duplicates
    
    for i, (entity1, analysis1, file1) in enumerate(entities):
        if not entity1.code:
            continue
        
        # Extract fragments from entity1 (only fragments, not full entity to focus on refactoring opportunities)
        fragments1 = _extract_code_fragments(entity1.code, min_lines=3, max_lines=25)
        
        for frag1 in fragments1:
            fp1 = _normalize_fingerprint(frag1['code'])
            if not fp1 or len(fp1) < 10:  # Skip very short fragments
                continue
            
            # Create hash to check for duplicates
            frag1_hash = hash(fp1)
            if frag1_hash in seen_code_hashes:
                continue
            
            for j, (entity2, analysis2, file2) in enumerate(entities[i+1:], start=i+1):
                if not entity2.code:
                    continue
                
                # Skip if same entity ID
                if entity1.id == entity2.id:
                    continue
                
                # Skip if same file, same name, and same line range (duplicate)
                if (file1 and file2 and 
                    file1.path == file2.path and 
                    entity1.name == entity2.name and
                    entity1.start_line == entity2.start_line and
                    entity1.end_line == entity2.end_line):
                    continue
                
                # Extract fragments from entity2 (only fragments, not full entity)
                fragments2 = _extract_code_fragments(entity2.code, min_lines=3, max_lines=25)
                
                for frag2 in fragments2:
                    fp2 = _normalize_fingerprint(frag2['code'])
                    if not fp2 or len(fp2) < 10:
                        continue
                    
                    # Skip if same code
                    if fp1 == fp2:
                        continue
                    
                    # Calculate similarity
                    similarity = _calculate_fingerprint_similarity(fp1, fp2)
                    
                    if similarity >= min_similarity:
                        frag2_hash = hash(fp2)
                        
                        # Create pair key and check for duplicates
                        # Use sorted tuple to ensure same pair is detected regardless of order
                        pair_key = tuple(sorted([frag1_hash, frag2_hash]))
                        if pair_key in seen_pairs:
                            continue
                        
                        # Check if either fragment was already shown (to avoid showing same code twice)
                        if frag1_hash in seen_code_hashes or frag2_hash in seen_code_hashes:
                            continue
                        
                        seen_pairs.add(pair_key)
                        seen_code_hashes.add(frag1_hash)
                        seen_code_hashes.add(frag2_hash)
                        
                        # Calculate actual line numbers in source file
                        frag1_start = entity1.start_line + frag1.get('start_line', 0)
                        frag1_end = entity1.start_line + frag1.get('end_line', len(frag1['lines']) - 1)
                        frag2_start = entity2.start_line + frag2.get('start_line', 0)
                        frag2_end = entity2.start_line + frag2.get('end_line', len(frag2['lines']) - 1)
                        
                        # Build entity responses with fragment info
                        entity1_resp = EntityResponse(
                            id=entity1.id,
                            type=entity1.type,
                            name=entity1.name,
                            start_line=frag1_start,
                            end_line=frag1_end,
                            visibility=entity1.visibility,
                            full_qualified_name=entity1.full_qualified_name,
                            file_path=file1.path if file1 else "",
                            code=frag1['code']  # Use fragment code, not full entity code
                        )
                        
                        entity2_resp = EntityResponse(
                            id=entity2.id,
                            type=entity2.type,
                            name=entity2.name,
                            start_line=frag2_start,
                            end_line=frag2_end,
                            visibility=entity2.visibility,
                            full_qualified_name=entity2.full_qualified_name,
                            file_path=file2.path if file2 else "",
                            code=frag2['code']  # Use fragment code, not full entity code
                        )
                        
                        # Build analysis responses (use parent entity analysis)
                        analysis1_resp = None
                        if analysis1:
                            analysis1_resp = AnalysisResponse(
                                id=analysis1.id,
                                description=analysis1.description,
                                complexity=_convert_complexity(analysis1.complexity),
                                complexity_explanation=getattr(analysis1, 'complexity_explanation', None),
                                complexity_numeric=analysis1.complexity_numeric,
                                solid_violations=analysis1.solid_violations or [],
                                design_patterns=analysis1.design_patterns or [],
                                ddd_role=analysis1.ddd_role,
                                mvc_role=analysis1.mvc_role,
                                is_testable=analysis1.is_testable,
                                testability_score=analysis1.testability_score,
                                testability_issues=analysis1.testability_issues or [],
                                entity=entity1_resp
                            )
                        
                        analysis2_resp = None
                        if analysis2:
                            analysis2_resp = AnalysisResponse(
                                id=analysis2.id,
                                description=analysis2.description,
                                complexity=_convert_complexity(analysis2.complexity),
                                complexity_explanation=getattr(analysis2, 'complexity_explanation', None),
                                complexity_numeric=analysis2.complexity_numeric,
                                solid_violations=analysis2.solid_violations or [],
                                design_patterns=analysis2.design_patterns or [],
                                ddd_role=analysis2.ddd_role,
                                mvc_role=analysis2.mvc_role,
                                is_testable=analysis2.is_testable,
                                testability_score=analysis2.testability_score,
                                testability_issues=analysis2.testability_issues or [],
                                entity=entity2_resp
                            )
                        
                        similar_pairs.append({
                            "left": {
                                "entity": entity1_resp,
                                "analysis": analysis1_resp
                            },
                            "right": {
                                "entity": entity2_resp,
                                "analysis": analysis2_resp
                            },
                            "similarity": similarity
                        })
    
    # Sort by similarity (highest first), then by code length (shorter fragments first - more actionable)
    similar_pairs.sort(key=lambda x: (x["similarity"], -len(x["left"]["entity"].code or "")), reverse=True)
    
    # Additional deduplication: remove pairs where code appears in reverse order
    final_pairs = []
    seen_left_codes = set()
    seen_right_codes = set()
    
    for pair in similar_pairs:
        left_code_hash = hash(_normalize_fingerprint(pair["left"]["entity"].code or ""))
        right_code_hash = hash(_normalize_fingerprint(pair["right"]["entity"].code or ""))
        
        # Skip if we've seen this code on the left or right before
        if left_code_hash in seen_left_codes or right_code_hash in seen_right_codes:
            continue
        
        # Skip if left and right are swapped versions of a pair we've seen
        if (left_code_hash in seen_right_codes and right_code_hash in seen_left_codes):
            continue
        
        seen_left_codes.add(left_code_hash)
        seen_right_codes.add(right_code_hash)
        final_pairs.append(pair)
    
    return {
        "pairs": final_pairs[:limit],
        "total": len(final_pairs),
        "limit": limit
    }

