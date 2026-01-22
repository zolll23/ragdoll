import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search, Code, Database, Zap } from 'lucide-react'
import i18n from '../utils/i18n'

export default function HomePage() {
  const [, forceUpdate] = useState()
  
  useEffect(() => {
    const handleLanguageChange = () => forceUpdate({})
    window.addEventListener('languagechange', handleLanguageChange)
    return () => window.removeEventListener('languagechange', handleLanguageChange)
  }, [])
  
  return (
    <div className="px-4 py-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {i18n.t('title')}
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          {i18n.t('subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        <div className="bg-white p-6 rounded-lg shadow">
          <Search className="w-8 h-8 text-blue-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">{i18n.t('semanticSearch')}</h3>
          <p className="text-gray-600 text-sm">
            {i18n.t('semanticSearchDesc')}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <Code className="w-8 h-8 text-green-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">{i18n.t('codeAnalysis')}</h3>
          <p className="text-gray-600 text-sm">
            {i18n.t('codeAnalysisDesc')}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <Database className="w-8 h-8 text-purple-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">{i18n.t('similarityDetection')}</h3>
          <p className="text-gray-600 text-sm">
            {i18n.t('similarityDetectionDesc')}
          </p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <Zap className="w-8 h-8 text-yellow-500 mb-4" />
          <h3 className="text-lg font-semibold mb-2">{i18n.t('fastIndexing')}</h3>
          <p className="text-gray-600 text-sm">
            {i18n.t('fastIndexingDesc')}
          </p>
        </div>
      </div>

      <div className="text-center">
        <Link
          to="/search"
          className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
        >
          {i18n.t('startSearching')}
        </Link>
      </div>
    </div>
  )
}
