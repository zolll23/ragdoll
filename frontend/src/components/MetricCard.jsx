import React, { useState } from 'react'
import { Info, X } from 'lucide-react'
import { useLanguage } from '../utils/i18n'

export function MetricInfoModal({ metric, onClose }) {
  const { t } = useLanguage()
  
  if (!metric) return null
  
  const descriptions = {
    linesOfCode: t('locDescription'),
    parameters: t('parametersDescription'),
    cyclomaticComplexity: t('cyclomaticComplexityDescription'),
    cognitiveComplexity: t('cognitiveComplexityDescription'),
    maxNestingDepth: t('maxNestingDepthDescription'),
    couplingScore: t('couplingScoreDescription'),
    cohesionScore: t('cohesionScoreDescription'),
    securityIssues: t('securityIssuesDescription'),
    nPlusOneQueries: t('nPlusOneQueriesDescription'),
    godObject: t('godObjectDescription'),
    longParameterList: t('longParameterListDescription'),
  }
  
  const metricTitles = {
    linesOfCode: t('linesOfCode'),
    parameters: t('parameters'),
    cyclomaticComplexity: t('cyclomaticComplexity'),
    cognitiveComplexity: t('cognitiveComplexity'),
    maxNestingDepth: t('maxNestingDepth'),
    couplingScore: t('couplingScore'),
    cohesionScore: t('cohesionScore'),
    securityIssues: t('securityIssues'),
    nPlusOneQueries: t('nPlusOneQueries'),
    godObject: t('godObject'),
    longParameterList: t('longParameterList'),
  }
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900">{metricTitles[metric] || t('metricDescription')}</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
          <div className="prose max-w-none">
            <p className="text-gray-700 leading-relaxed">{descriptions[metric] || t('noDescriptionAvailable') || 'No description available'}</p>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            >
              {t('close')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function MetricCard({ title, value, metricKey, bgColor, borderColor, textColor, textValueColor }) {
  const { t } = useLanguage()
  const [showModal, setShowModal] = useState(false)
  
  return (
    <>
      <div className={`${bgColor} ${borderColor} rounded-lg p-3 relative`}>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <div className={`text-sm ${textColor} font-semibold`}>{title}</div>
              <button
                onClick={() => setShowModal(true)}
                className="text-gray-500 hover:text-gray-700 transition-colors"
                title={t('metricDescription')}
              >
                <Info className="w-4 h-4" />
              </button>
            </div>
            <div className={`text-2xl font-bold ${textValueColor}`}>{value}</div>
          </div>
        </div>
      </div>
      {showModal && <MetricInfoModal metric={metricKey} onClose={() => setShowModal(false)} />}
    </>
  )
}

