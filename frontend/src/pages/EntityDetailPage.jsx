import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { entitiesApi } from '../services/api'
import { FileCode, AlertCircle, Code, ArrowLeft, CheckCircle, XCircle, Network, ExternalLink, Info, X } from 'lucide-react'
import { useLanguage } from '../utils/i18n'
import { MetricCard, MetricInfoModal } from '../components/MetricCard'

export default function EntityDetailPage() {
  const { entityId } = useParams()
  const [searchParams] = useSearchParams()
  const { t } = useLanguage()
  
  // Get return URL from query params
  const from = searchParams.get('from')
  const searchQuery = searchParams.get('q')
  const projectId = searchParams.get('project_id')
  
  // Build back URL with query and project_id if available
  let backUrl = '/search'
  if (from === 'search' && searchQuery) {
    const params = new URLSearchParams({ q: searchQuery })
    if (projectId) {
      params.set('project_id', projectId)
    }
    backUrl = `/search?${params.toString()}`
  }

  const { data: entity, isLoading: entityLoading } = useQuery({
    queryKey: ['entity', entityId],
    queryFn: () => entitiesApi.get(entityId),
  })

  const { data: analysis, isLoading: analysisLoading } = useQuery({
    queryKey: ['entity-analysis', entityId],
    queryFn: () => entitiesApi.getAnalysis(entityId),
    enabled: !!entity && entity.has_analysis,
  })

  const { data: dependencies, isLoading: dependenciesLoading } = useQuery({
    queryKey: ['entity-dependencies', entityId],
    queryFn: () => entitiesApi.getDependencies(entityId),
    enabled: !!entity,
  })

  if (entityLoading) {
    return (
      <div className="px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!entity) {
    return (
      <div className="px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-800">{t('entityNotFound')}</p>
          </div>
        </div>
      </div>
    )
  }

  const entityData = entity.data || entity
  const analysisData = analysis?.data || analysis

  return (
    <div className="px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <Link
          to={backUrl}
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          {from === 'search' ? t('backToSearch') : t('backToEntities')}
        </Link>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <div className="flex items-start gap-4 mb-4">
            <FileCode className="w-6 h-6 text-blue-500 mt-1" />
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl font-bold text-gray-900">
                  {entityData.name}
                </h1>
                <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                  {entityData.type}
                </span>
                {entityData.visibility && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                    {entityData.visibility}
                  </span>
                )}
              </div>
              
              <p className="text-sm text-gray-600 mb-4">
                {entityData.file_path}:{entityData.start_line}-{entityData.end_line}
              </p>

              {entityData.full_qualified_name && (
                <p className="text-sm text-gray-500 mb-4 font-mono">
                  {entityData.full_qualified_name}
                </p>
              )}
            </div>
          </div>

          {/* Code */}
          <div className="mt-6">
            <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
              <Code className="w-5 h-5" />
              {t('code')}
            </h2>
            <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 overflow-x-auto text-sm">
              <code>{entityData.code}</code>
            </pre>
          </div>
        </div>

        {/* Analysis */}
        {analysisLoading && (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        {analysisData && (
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">{t('analysisDetails')}</h2>
            
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-gray-700 mb-2">{t('description')}</h3>
                <p className="text-gray-700">{analysisData.description}</p>
              </div>

              {/* Keywords */}
              {analysisData.keywords && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    Keywords
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {analysisData.keywords.split(', ').map((keyword, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200"
                      >
                        {keyword.trim()}
                      </span>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Keywords used for semantic search to improve findability
                  </p>
                </div>
              )}

              <div>
                <h3 className="font-semibold text-gray-700 mb-2">{t('complexity')}</h3>
                <p className="text-gray-700">
                  {analysisData.complexity}
                  {analysisData.complexity_explanation && (
                    <span className="text-sm text-gray-600 ml-2">
                      ({analysisData.complexity_explanation})
                    </span>
                  )}
                </p>
              </div>

              {analysisData.design_patterns && analysisData.design_patterns.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">{t('designPatterns')}</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysisData.design_patterns.map((pattern, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-1 bg-green-100 text-green-700 text-sm rounded"
                      >
                        {pattern}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="font-semibold text-gray-700 mb-2">{t('architecturalRoles')}</h3>
                <div className="flex flex-wrap gap-2">
                  {analysisData.ddd_role && (
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-sm rounded">
                      DDD: {analysisData.ddd_role}
                    </span>
                  )}
                  {analysisData.mvc_role && (
                    <span className="px-2 py-1 bg-orange-100 text-orange-700 text-sm rounded">
                      MVC: {analysisData.mvc_role}
                    </span>
                  )}
                </div>
              </div>

              {analysisData.solid_violations && analysisData.solid_violations.length > 0 && (
                <div>
                  <h3 className="font-semibold text-red-700 mb-2">{t('solidViolations')}</h3>
                  <div className="space-y-2">
                    {analysisData.solid_violations.map((violation, idx) => (
                      <div key={idx} className="bg-red-50 border border-red-200 rounded p-3">
                        <p className="font-semibold text-red-800">
                          {violation.principle} ({violation.severity})
                        </p>
                        <p className="text-sm text-gray-700 mt-1">{violation.description}</p>
                        {violation.suggestion && (
                          <p className="text-sm text-blue-700 mt-2">
                            <strong>{t('suggestion')}:</strong> {violation.suggestion}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h3 className="font-semibold text-gray-700 mb-2">{t('testability')}</h3>
                <div className="flex items-center gap-3">
                  {analysisData.is_testable ? (
                    <span className="flex items-center gap-2 text-green-700">
                      <CheckCircle className="w-5 h-5" />
                      {t('testable')}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2 text-red-700">
                      <XCircle className="w-5 h-5" />
                      {t('notTestable')}
                    </span>
                  )}
                  <span className="text-sm text-gray-600">
                    {t('score')}: {(analysisData.testability_score * 100).toFixed(0)}%
                  </span>
                </div>
                {analysisData.testability_issues && analysisData.testability_issues.length > 0 && (
                  <div className="mt-2">
                    <p className="text-sm font-semibold text-gray-700 mb-1">{t('testabilityIssues')}:</p>
                    <ul className="list-disc list-inside text-sm text-gray-600">
                      {analysisData.testability_issues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Extended Metrics */}
              {(analysisData.lines_of_code !== null && analysisData.lines_of_code !== undefined) ||
               (analysisData.cyclomatic_complexity !== null && analysisData.cyclomatic_complexity !== undefined) ||
               (analysisData.cognitive_complexity !== null && analysisData.cognitive_complexity !== undefined) ? (
                <div className="border-t border-gray-200 pt-4 mt-4">
                  <h3 className="font-semibold text-gray-700 mb-4">{t('codeMetrics') || 'Code Metrics'}</h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* Size Metrics */}
                    {analysisData.lines_of_code !== null && analysisData.lines_of_code !== undefined && (
                      <MetricCard
                        title={t('linesOfCode') || 'Lines of Code'}
                        value={analysisData.lines_of_code}
                        metricKey="linesOfCode"
                        bgColor="bg-blue-50"
                        borderColor="border border-blue-200"
                        textColor="text-blue-700"
                        textValueColor="text-blue-900"
                      />
                    )}
                    
                    {analysisData.parameter_count !== null && analysisData.parameter_count !== undefined && (
                      <MetricCard
                        title={t('parameters') || 'Parameters'}
                        value={analysisData.parameter_count}
                        metricKey="parameters"
                        bgColor="bg-blue-50"
                        borderColor="border border-blue-200"
                        textColor="text-blue-700"
                        textValueColor="text-blue-900"
                      />
                    )}

                    {/* Complexity Metrics */}
                    {analysisData.cyclomatic_complexity !== null && analysisData.cyclomatic_complexity !== undefined && (
                      <MetricCard
                        title={t('cyclomaticComplexity') || 'Cyclomatic Complexity'}
                        value={analysisData.cyclomatic_complexity}
                        metricKey="cyclomaticComplexity"
                        bgColor="bg-purple-50"
                        borderColor="border border-purple-200"
                        textColor="text-purple-700"
                        textValueColor="text-purple-900"
                      />
                    )}

                    {analysisData.cognitive_complexity !== null && analysisData.cognitive_complexity !== undefined && (
                      <MetricCard
                        title={t('cognitiveComplexity') || 'Cognitive Complexity'}
                        value={analysisData.cognitive_complexity}
                        metricKey="cognitiveComplexity"
                        bgColor="bg-purple-50"
                        borderColor="border border-purple-200"
                        textColor="text-purple-700"
                        textValueColor="text-purple-900"
                      />
                    )}

                    {analysisData.max_nesting_depth !== null && analysisData.max_nesting_depth !== undefined && (
                      <MetricCard
                        title={t('maxNestingDepth') || 'Max Nesting Depth'}
                        value={analysisData.max_nesting_depth}
                        metricKey="maxNestingDepth"
                        bgColor="bg-purple-50"
                        borderColor="border border-purple-200"
                        textColor="text-purple-700"
                        textValueColor="text-purple-900"
                      />
                    )}

                    {/* Coupling & Cohesion */}
                    {analysisData.coupling_score !== null && analysisData.coupling_score !== undefined && (
                      <MetricCard
                        title={t('couplingScore') || 'Coupling Score'}
                        value={analysisData.coupling_score.toFixed(2)}
                        metricKey="couplingScore"
                        bgColor="bg-orange-50"
                        borderColor="border border-orange-200"
                        textColor="text-orange-700"
                        textValueColor="text-orange-900"
                      />
                    )}

                    {analysisData.cohesion_score !== null && analysisData.cohesion_score !== undefined && (
                      <MetricCard
                        title={t('cohesionScore') || 'Cohesion Score'}
                        value={analysisData.cohesion_score.toFixed(2)}
                        metricKey="cohesionScore"
                        bgColor="bg-green-50"
                        borderColor="border border-green-200"
                        textColor="text-green-700"
                        textValueColor="text-green-900"
                      />
                    )}

                    {/* Security Issues */}
                    {analysisData.security_issues && analysisData.security_issues.length > 0 && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <div className="text-sm text-red-700 font-semibold mb-1">{t('securityIssues') || 'Security Issues'}</div>
                        <div className="text-2xl font-bold text-red-900">{analysisData.security_issues.length}</div>
                        <div className="mt-2 space-y-1">
                          {analysisData.security_issues.slice(0, 3).map((issue, idx) => (
                            <div key={idx} className="text-xs text-red-800">
                              • {issue.type || issue.severity}: {issue.description?.substring(0, 50) || ''}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* N+1 Queries */}
                    {analysisData.n_plus_one_queries && analysisData.n_plus_one_queries.length > 0 && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <div className="text-sm text-yellow-700 font-semibold mb-1">{t('nPlusOneQueries') || 'N+1 Queries'}</div>
                        <div className="text-2xl font-bold text-yellow-900">{analysisData.n_plus_one_queries.length}</div>
                      </div>
                    )}

                    {/* Architecture Metrics */}
                    {analysisData.is_god_object !== null && analysisData.is_god_object !== undefined && analysisData.is_god_object && (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                        <div className="text-sm text-red-700 font-semibold mb-1">{t('godObject') || 'God Object'}</div>
                        <div className="text-lg font-bold text-red-900">⚠️ {t('detected') || 'Detected'}</div>
                      </div>
                    )}

                    {analysisData.long_parameter_list !== null && analysisData.long_parameter_list !== undefined && analysisData.long_parameter_list && (
                      <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                        <div className="text-sm text-orange-700 font-semibold mb-1">{t('longParameterList') || 'Long Parameter List'}</div>
                        <div className="text-lg font-bold text-orange-900">⚠️ {t('detected') || 'Detected'}</div>
                      </div>
                    )}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}

        {!analysisData && !analysisLoading && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-yellow-800">{t('noAnalysis')}</p>
          </div>
        )}

        {/* Dependencies */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 mt-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Network className="w-5 h-5" />
            {t('dependencies') || 'Dependencies'}
          </h2>
          
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
                    <p className="text-gray-600">{t('noDependencies') || 'No dependencies found'}</p>
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
                  'import': t('imports') || 'Imports',
                  'extends': t('extends') || 'Extends',
                  'implements': t('implements') || 'Implements',
                  'calls': t('methodCalls') || 'Method Calls'
                }

                return Object.entries(grouped).map(([type, deps]) => (
                  <div key={type} className="border-l-4 border-blue-500 pl-4">
                    <h3 className="font-semibold text-gray-700 mb-2">
                      {typeLabels[type] || type}
                    </h3>
                    <div className="space-y-2">
                      {deps.map((dep) => (
                        <div key={dep.id} className="bg-gray-50 rounded-lg p-3">
                          {dep.depends_on_entity ? (
                            <Link
                              to={`/entities/${dep.depends_on_entity.id}?from=entity&q=${encodeURIComponent(searchQuery || '')}`}
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
                                  ({t('notIndexed') || 'Not indexed'})
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
    </div>
  )
}

