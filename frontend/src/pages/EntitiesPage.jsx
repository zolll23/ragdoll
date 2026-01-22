import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { entitiesApi, projectsApi } from '../services/api'
import { FileCode, Search, Filter, ChevronRight, Code, AlertCircle, CheckCircle, XCircle, Info, X, Network, ExternalLink } from 'lucide-react'
import i18n from '../utils/i18n'
import { MetricCard, MetricInfoModal } from '../components/MetricCard'

export default function EntitiesPage() {
  const { projectId } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [entityTypeFilter, setEntityTypeFilter] = useState('')
  const [selectedEntity, setSelectedEntity] = useState(null)

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  })

  const { data: entities, isLoading } = useQuery({
    queryKey: ['entities', projectId, entityTypeFilter],
    queryFn: () => entitiesApi.list({ project_id: projectId, entity_type: entityTypeFilter || undefined }),
    enabled: !!projectId,
  })

  const { data: analysis } = useQuery({
    queryKey: ['analysis', selectedEntity],
    queryFn: () => entitiesApi.getAnalysis(selectedEntity),
    enabled: !!selectedEntity,
  })

  const filteredEntities = entities?.data?.filter(entity => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      entity.name.toLowerCase().includes(query) ||
      entity.file_path.toLowerCase().includes(query) ||
      (entity.description && entity.description.toLowerCase().includes(query)) ||
      (entity.full_qualified_name && entity.full_qualified_name.toLowerCase().includes(query))
    )
  }) || []

  // Get entity types, including 'enum' if there are enum case values
  const baseEntityTypes = [...new Set(entities?.data?.map(e => e.type) || [])]
  const hasEnumCases = entities?.data?.some(e => e.type === 'constant' && e.full_qualified_name?.includes('::')) || false
  const entityTypes = hasEnumCases && !baseEntityTypes.includes('enum') 
    ? [...baseEntityTypes, 'enum'] 
    : baseEntityTypes

  return (
    <div className="px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-2">
            <Link to="/projects" className="text-gray-500 hover:text-gray-700">
              {i18n.t('projects')}
            </Link>
            <ChevronRight className="w-4 h-4 text-gray-400" />
            <span className="font-semibold">{project?.data?.name || 'Project'}</span>
          </div>
          <h1 className="text-3xl font-bold">{i18n.t('entities')}</h1>
          <p className="text-gray-600 mt-1">
            {filteredEntities.length} {i18n.t('entities')} {project?.data?.name ? `in ${project.data.name}` : ''}
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white p-4 rounded-lg shadow mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={i18n.t('searchEntities')}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <select
                value={entityTypeFilter}
                onChange={(e) => setEntityTypeFilter(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="">{i18n.t('allTypes')}</option>
                {entityTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center text-sm text-gray-600">
              {i18n.t('showing')} {filteredEntities.length} {i18n.t('of')} {entities?.data?.length || 0} {i18n.t('entities')}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Entities List */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">{i18n.t('entitiesList')}</h2>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {isLoading && (
                <div className="p-8 text-center">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              )}
              {!isLoading && filteredEntities.length === 0 && (
                <div className="p-8 text-center text-gray-500">
                  <FileCode className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p>{i18n.t('noEntities')}</p>
                </div>
              )}
              {!isLoading && filteredEntities.map((entity) => (
                <div
                  key={entity.id}
                  onClick={() => setSelectedEntity(entity.id)}
                  className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition ${
                    selectedEntity === entity.id ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Code className="w-4 h-4 text-blue-500" />
                        <h3 className="font-semibold text-gray-900">{entity.name}</h3>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                          {entity.type}
                        </span>
                        {entity.has_analysis && (
                          <CheckCircle className="w-4 h-4 text-green-500" title={i18n.t('hasAnalysis')} />
                        )}
                      </div>
                      {entity.full_qualified_name && (
                        <p className="text-sm text-gray-600 mb-1">{entity.full_qualified_name}</p>
                      )}
                      <p className="text-xs text-gray-500 mb-2">
                        {entity.file_path}:{entity.start_line}-{entity.end_line}
                      </p>
                      {entity.description && (
                        <p className="text-sm text-gray-700 line-clamp-2">{entity.description}</p>
                      )}
                      {entity.complexity && (
                        <span className="inline-block mt-2 px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                          {i18n.t('complexity')}: {entity.complexity}
                        </span>
                      )}
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Analysis Details */}
          <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold">{i18n.t('analysisDetails')}</h2>
            </div>
            <div className="p-6">
              {!selectedEntity && (
                <div className="text-center py-12 text-gray-500">
                  <AlertCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <p>{i18n.t('selectEntity')}</p>
                </div>
              )}
              {selectedEntity && !analysis && (
                <div className="text-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              )}
              {selectedEntity && analysis && analysis.data && (
                <EntityAnalysisView analysis={analysis.data} entityId={selectedEntity} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function EntityAnalysisView({ analysis, entityId }) {
  const { data: dependencies, isLoading: dependenciesLoading } = useQuery({
    queryKey: ['entity-dependencies', entityId],
    queryFn: () => entitiesApi.getDependencies(entityId),
    enabled: !!entityId,
  })

  return (
    <div className="space-y-6">
      {/* Entity Info */}
      <div>
        <h3 className="text-lg font-semibold mb-2">{analysis.entity.name}</h3>
        <p className="text-sm text-gray-600 mb-4">
          {analysis.entity.file_path}:{analysis.entity.start_line}-{analysis.entity.end_line}
        </p>
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
            {analysis.entity.type}
          </span>
          {analysis.entity.visibility && (
            <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
              {analysis.entity.visibility}
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      <div>
        <h4 className="font-semibold mb-2">{i18n.t('description')}</h4>
        <p className="text-gray-700">{analysis.description}</p>
      </div>

      {/* Keywords */}
      {analysis.keywords && (
        <div>
          <h4 className="font-semibold mb-2 flex items-center gap-2">
            <Info className="w-4 h-4" />
            Keywords
          </h4>
          <div className="flex flex-wrap gap-2">
            {analysis.keywords.split(', ').slice(0, 10).map((keyword, idx) => (
              <span
                key={idx}
                className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200"
              >
                {keyword.trim()}
              </span>
            ))}
            {analysis.keywords.split(', ').length > 10 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded">
                +{analysis.keywords.split(', ').length - 10} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Complexity */}
      <div>
        <h4 className="font-semibold mb-2">{i18n.t('complexity')}</h4>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded font-semibold">
            {analysis.complexity}
          </span>
        </div>
      </div>

      {/* Design Patterns */}
      {analysis.design_patterns && analysis.design_patterns.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2">{i18n.t('designPatterns')}</h4>
          <div className="flex flex-wrap gap-2">
            {analysis.design_patterns.map((pattern, idx) => (
              <span key={idx} className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                {pattern}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* DDD/MVC Roles */}
      {(analysis.ddd_role || analysis.mvc_role) && (
        <div>
          <h4 className="font-semibold mb-2">{i18n.t('architecturalRoles')}</h4>
          <div className="flex flex-wrap gap-2">
            {analysis.ddd_role && (
              <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded">
                DDD: {analysis.ddd_role}
              </span>
            )}
            {analysis.mvc_role && (
              <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded">
                MVC: {analysis.mvc_role}
              </span>
            )}
          </div>
        </div>
      )}

      {/* SOLID Violations */}
      {analysis.solid_violations && analysis.solid_violations.length > 0 && (
        <div>
          <h4 className="font-semibold mb-2 text-red-700">{i18n.t('solidViolations')}</h4>
          <div className="space-y-3">
            {analysis.solid_violations.map((violation, idx) => (
              <div key={idx} className="border-l-4 border-red-500 pl-4 py-2 bg-red-50 rounded">
                <div className="flex items-center gap-2 mb-1">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span className="font-semibold text-red-800">{violation.principle}</span>
                  <span className={`px-2 py-1 text-xs rounded ${
                    violation.severity === 'high' ? 'bg-red-200 text-red-800' :
                    violation.severity === 'medium' ? 'bg-orange-200 text-orange-800' :
                    'bg-yellow-200 text-yellow-800'
                  }`}>
                    {violation.severity}
                  </span>
                </div>
                <p className="text-sm text-gray-700 mb-1">{violation.description}</p>
                {violation.suggestion && (
                  <p className="text-sm text-blue-700 italic">{i18n.t('suggestion')}: {violation.suggestion}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Testability */}
      <div>
        <h4 className="font-semibold mb-2">{i18n.t('testability')}</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            {analysis.is_testable ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
            <span className={analysis.is_testable ? 'text-green-700' : 'text-red-700'}>
              {analysis.is_testable ? i18n.t('testable') : i18n.t('notTestable')}
            </span>
            <span className="text-gray-600">
              ({i18n.t('score')}: {(analysis.testability_score * 100).toFixed(0)}%)
            </span>
          </div>
          {analysis.testability_issues && analysis.testability_issues.length > 0 && (
            <div className="mt-2">
              <p className="text-sm font-medium text-gray-700 mb-1">{i18n.t('testabilityIssues')}:</p>
              <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                {analysis.testability_issues.map((issue, idx) => (
                  <li key={idx}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Extended Metrics */}
      {(analysis.lines_of_code !== null && analysis.lines_of_code !== undefined) ||
       (analysis.cyclomatic_complexity !== null && analysis.cyclomatic_complexity !== undefined) ||
       (analysis.cognitive_complexity !== null && analysis.cognitive_complexity !== undefined) ? (
        <div className="border-t border-gray-200 pt-4 mt-4">
          <h4 className="font-semibold text-gray-700 mb-4">{i18n.t('codeMetrics') || 'Code Metrics'}</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Size Metrics */}
            {analysis.lines_of_code !== null && analysis.lines_of_code !== undefined && (
              <MetricCard
                title={i18n.t('linesOfCode') || 'Lines of Code'}
                value={analysis.lines_of_code}
                metricKey="linesOfCode"
                bgColor="bg-blue-50"
                borderColor="border border-blue-200"
                textColor="text-blue-700"
                textValueColor="text-blue-900"
              />
            )}
            
            {analysis.parameter_count !== null && analysis.parameter_count !== undefined && (
              <MetricCard
                title={i18n.t('parameters') || 'Parameters'}
                value={analysis.parameter_count}
                metricKey="parameters"
                bgColor="bg-blue-50"
                borderColor="border border-blue-200"
                textColor="text-blue-700"
                textValueColor="text-blue-900"
              />
            )}

            {/* Complexity Metrics */}
            {analysis.cyclomatic_complexity !== null && analysis.cyclomatic_complexity !== undefined && (
              <MetricCard
                title={i18n.t('cyclomaticComplexity') || 'Cyclomatic Complexity'}
                value={analysis.cyclomatic_complexity}
                metricKey="cyclomaticComplexity"
                bgColor="bg-purple-50"
                borderColor="border border-purple-200"
                textColor="text-purple-700"
                textValueColor="text-purple-900"
              />
            )}

            {analysis.cognitive_complexity !== null && analysis.cognitive_complexity !== undefined && (
              <MetricCard
                title={i18n.t('cognitiveComplexity') || 'Cognitive Complexity'}
                value={analysis.cognitive_complexity}
                metricKey="cognitiveComplexity"
                bgColor="bg-purple-50"
                borderColor="border border-purple-200"
                textColor="text-purple-700"
                textValueColor="text-purple-900"
              />
            )}

            {analysis.max_nesting_depth !== null && analysis.max_nesting_depth !== undefined && (
              <MetricCard
                title={i18n.t('maxNestingDepth') || 'Max Nesting Depth'}
                value={analysis.max_nesting_depth}
                metricKey="maxNestingDepth"
                bgColor="bg-purple-50"
                borderColor="border border-purple-200"
                textColor="text-purple-700"
                textValueColor="text-purple-900"
              />
            )}

            {/* Coupling & Cohesion */}
            {analysis.coupling_score !== null && analysis.coupling_score !== undefined && (
              <MetricCard
                title={i18n.t('couplingScore') || 'Coupling Score'}
                value={analysis.coupling_score.toFixed(2)}
                metricKey="couplingScore"
                bgColor="bg-orange-50"
                borderColor="border border-orange-200"
                textColor="text-orange-700"
                textValueColor="text-orange-900"
              />
            )}

            {analysis.cohesion_score !== null && analysis.cohesion_score !== undefined && (
              <MetricCard
                title={i18n.t('cohesionScore') || 'Cohesion Score'}
                value={analysis.cohesion_score.toFixed(2)}
                metricKey="cohesionScore"
                bgColor="bg-green-50"
                borderColor="border border-green-200"
                textColor="text-green-700"
                textValueColor="text-green-900"
              />
            )}

            {/* Security Issues */}
            {analysis.security_issues && analysis.security_issues.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="text-sm text-red-700 font-semibold mb-1">{i18n.t('securityIssues') || 'Security Issues'}</div>
                <div className="text-2xl font-bold text-red-900">{analysis.security_issues.length}</div>
                <div className="mt-2 space-y-1">
                  {analysis.security_issues.slice(0, 3).map((issue, idx) => (
                    <div key={idx} className="text-xs text-red-800">
                      • {issue.type || issue.severity}: {issue.description?.substring(0, 50) || ''}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* N+1 Queries */}
            {analysis.n_plus_one_queries && analysis.n_plus_one_queries.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <div className="text-sm text-yellow-700 font-semibold mb-1">{i18n.t('nPlusOneQueries') || 'N+1 Queries'}</div>
                <div className="text-2xl font-bold text-yellow-900">{analysis.n_plus_one_queries.length}</div>
              </div>
            )}

            {/* Architecture Metrics */}
            {analysis.is_god_object !== null && analysis.is_god_object !== undefined && analysis.is_god_object && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="text-sm text-red-700 font-semibold mb-1">{i18n.t('godObject') || 'God Object'}</div>
                <div className="text-lg font-bold text-red-900">⚠️ {i18n.t('detected') || 'Detected'}</div>
              </div>
            )}

            {analysis.long_parameter_list !== null && analysis.long_parameter_list !== undefined && analysis.long_parameter_list && (
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                <div className="text-sm text-orange-700 font-semibold mb-1">{i18n.t('longParameterList') || 'Long Parameter List'}</div>
                <div className="text-lg font-bold text-orange-900">⚠️ {i18n.t('detected') || 'Detected'}</div>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Code */}
      {analysis.entity.code && (
        <div>
          <h4 className="font-semibold mb-2">{i18n.t('code')}</h4>
          <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
            <code>{analysis.entity.code}</code>
          </pre>
        </div>
      )}

      {/* Dependencies */}
      <div className="border-t border-gray-200 pt-6 mt-6">
        <h4 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Network className="w-5 h-5" />
          {i18n.t('dependencies') || 'Dependencies'}
        </h4>
        
        {dependenciesLoading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        {!dependenciesLoading && dependencies && (
          (() => {
            const deps = Array.isArray(dependencies.data) ? dependencies.data : (Array.isArray(dependencies) ? dependencies : [])
            if (deps.length === 0) {
              return (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
                  <p className="text-gray-600">{i18n.t('noDependencies') || 'No dependencies found'}</p>
                </div>
              )
            }
            
            return (
              <div className="space-y-4">
                {(() => {
                  const grouped = deps.reduce((acc, dep) => {
                    const type = dep.type || 'calls'
                    if (!acc[type]) acc[type] = []
                    acc[type].push(dep)
                    return acc
                  }, {})

                  const typeLabels = {
                    'import': i18n.t('imports') || 'Imports',
                    'extends': i18n.t('extends') || 'Extends',
                    'implements': i18n.t('implements') || 'Implements',
                    'calls': i18n.t('methodCalls') || 'Method Calls'
                  }

                  return Object.entries(grouped).map(([type, deps]) => (
                    <div key={type} className="border-l-4 border-blue-500 pl-4">
                      <h5 className="font-semibold text-gray-700 mb-2">
                        {typeLabels[type] || type}
                      </h5>
                      <div className="space-y-2">
                        {deps.map((dep) => (
                          <div key={dep.id} className="bg-gray-50 rounded-lg p-3">
                            {dep.depends_on_entity ? (
                              <Link
                                to={`/entities/${dep.depends_on_entity.id}?from=entities&projectId=${entityId}`}
                                className="flex items-start gap-2 hover:bg-gray-100 rounded p-2 -m-2 transition-colors"
                              >
                                <ExternalLink className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="font-semibold text-blue-700">
                                      {dep.depends_on_entity.full_qualified_name || dep.depends_on_entity.name}
                                    </span>
                                    <span className="px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded">
                                      {dep.depends_on_entity.type}
                                    </span>
                                  </div>
                                  {dep.depends_on_entity.file_path && (
                                    <p className="text-xs text-gray-500 truncate">
                                      {dep.depends_on_entity.file_path}:{dep.depends_on_entity.start_line}
                                    </p>
                                  )}
                                  {dep.depends_on_analysis && dep.depends_on_analysis.description && (
                                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                                      {dep.depends_on_analysis.description}
                                    </p>
                                  )}
                                </div>
                              </Link>
                            ) : (
                              <div className="flex items-start gap-2">
                                <span className="text-gray-400 mt-0.5">•</span>
                                <div className="flex-1">
                                  <span className="font-mono text-gray-700">{dep.depends_on_name}</span>
                                  <span className="text-xs text-gray-500 ml-2">
                                    ({i18n.t('notIndexed') || 'Not indexed'})
                                  </span>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                })()}
              </div>
            )
          })()
        )}
      </div>
    </div>
  )
}

