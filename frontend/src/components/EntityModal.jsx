import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { entitiesApi } from '../services/api'
import { X, FileCode, AlertCircle, Code, CheckCircle, XCircle, Network, ExternalLink, Info } from 'lucide-react'
import { MetricCard } from './MetricCard'

export default function EntityModal({ entityId, onClose }) {
  const { data: entity, isLoading: entityLoading } = useQuery({
    queryKey: ['entity', entityId],
    queryFn: () => entitiesApi.get(entityId),
    enabled: !!entityId,
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
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
        <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">Загрузка...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!entity) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
        <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center gap-3 text-red-600">
            <AlertCircle className="w-5 h-5" />
            <p>Сущность не найдена</p>
          </div>
        </div>
      </div>
    )
  }

  const entityData = entity.data || entity
  const analysisData = analysis?.data || analysis
  const dependenciesData = dependencies?.data || dependencies

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div 
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileCode className="w-6 h-6 text-blue-500" />
            <div>
              <h2 className="text-xl font-bold text-gray-900">{entityData.name}</h2>
              <p className="text-sm text-gray-600">
                {entityData.file_path}:{entityData.start_line}
                {entityData.end_line && `-${entityData.end_line}`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Entity Info */}
          <div className="flex flex-wrap gap-2">
            <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
              {entityData.type}
            </span>
            {entityData.visibility && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                {entityData.visibility}
              </span>
            )}
            {entityData.full_qualified_name && (
              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded font-mono">
                {entityData.full_qualified_name}
              </span>
            )}
          </div>

          {/* Description */}
          {analysisData?.description && (
            <div>
              <h3 className="font-semibold mb-2 text-gray-900">Описание</h3>
              <p className="text-gray-700">{analysisData.description}</p>
            </div>
          )}

          {/* Complexity */}
          {analysisData?.complexity && (
            <div>
              <h3 className="font-semibold mb-2 text-gray-900">Сложность</h3>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded font-mono">
                  {analysisData.complexity}
                </span>
                {analysisData.complexity_explanation && (
                  <span className="text-sm text-gray-600">
                    {analysisData.complexity_explanation}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Code */}
          {entityData.code && (
            <div>
              <h3 className="font-semibold mb-2 text-gray-900 flex items-center gap-2">
                <Code className="w-4 h-4" />
                Код
              </h3>
              <pre className="bg-gray-50 border border-gray-200 rounded p-4 overflow-x-auto text-sm">
                <code>{entityData.code}</code>
              </pre>
            </div>
          )}

          {/* Metrics */}
          {analysisData?.metrics && (
            <div>
              <h3 className="font-semibold mb-2 text-gray-900">Метрики</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {analysisData.metrics.lines_of_code && (
                  <MetricCard
                    label="Строк кода"
                    value={analysisData.metrics.lines_of_code}
                    icon={<Code className="w-4 h-4" />}
                  />
                )}
                {analysisData.metrics.cyclomatic_complexity && (
                  <MetricCard
                    label="Цикломатическая сложность"
                    value={analysisData.metrics.cyclomatic_complexity}
                    icon={<Network className="w-4 h-4" />}
                  />
                )}
                {analysisData.metrics.testability_score !== undefined && (
                  <MetricCard
                    label="Тестируемость"
                    value={(analysisData.metrics.testability_score * 100).toFixed(0) + '%'}
                    icon={analysisData.metrics.testability_score > 0.7 ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  />
                )}
              </div>
            </div>
          )}

          {/* Design Patterns */}
          {analysisData?.design_patterns && analysisData.design_patterns.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2 text-gray-900">Паттерны проектирования</h3>
              <div className="flex flex-wrap gap-2">
                {analysisData.design_patterns.map((pattern, idx) => (
                  <span key={idx} className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded">
                    {pattern}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* SOLID Violations */}
          {analysisData?.solid_violations && analysisData.solid_violations.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2 text-red-900">Нарушения SOLID</h3>
              <div className="space-y-2">
                {analysisData.solid_violations.map((violation, idx) => {
                  // Проверяем, является ли violation объектом или строкой
                  if (typeof violation === 'object' && violation !== null && !Array.isArray(violation)) {
                    // Получаем принцип - может быть строкой или объектом enum
                    const principle = typeof violation.principle === 'object' 
                      ? violation.principle?.value || violation.principle?.name || 'Нарушение SOLID'
                      : violation.principle || 'Нарушение SOLID'
                    
                    return (
                      <div key={idx} className="text-sm text-red-700 border-l-2 border-red-400 pl-3 py-1">
                        <div className="font-semibold text-red-800">
                          {principle}
                        </div>
                        {violation.description && (
                          <div className="text-gray-700 mt-1">{violation.description}</div>
                        )}
                        {violation.severity && (
                          <div className="text-xs text-gray-600 mt-1">
                            Серьезность: {typeof violation.severity === 'object' 
                              ? violation.severity?.value || violation.severity?.name || violation.severity
                              : violation.severity}
                          </div>
                        )}
                        {violation.suggestion && (
                          <div className="text-xs text-blue-600 mt-1">
                            Рекомендация: {violation.suggestion}
                          </div>
                        )}
                      </div>
                    )
                  } else {
                    // Если это строка, отображаем как раньше
                    return (
                      <div key={idx} className="text-sm text-red-700">
                        • {String(violation)}
                      </div>
                    )
                  }
                })}
              </div>
            </div>
          )}

          {/* Dependencies */}
          {dependenciesData && dependenciesData.length > 0 && (
            <div>
              <h3 className="font-semibold mb-2 text-gray-900">Зависимости</h3>
              <div className="space-y-1">
                {dependenciesData.slice(0, 10).map((dep, idx) => (
                  <div key={idx} className="text-sm text-gray-700">
                    • {dep.name} ({dep.type})
                  </div>
                ))}
                {dependenciesData.length > 10 && (
                  <div className="text-sm text-gray-500">
                    ... и еще {dependenciesData.length - 10}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
