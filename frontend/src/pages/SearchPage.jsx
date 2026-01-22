import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { searchApi, projectsApi } from '../services/api'
import { Search, FileCode, AlertCircle, ExternalLink } from 'lucide-react'
import { useLanguage } from '../utils/i18n'

export default function SearchPage() {
  const { t } = useLanguage()
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Get query and project_id from URL params
  const urlQuery = searchParams.get('q') || ''
  const urlProjectId = searchParams.get('project_id')
  const [query, setQuery] = useState(urlQuery)
  const [searchQuery, setSearchQuery] = useState(urlQuery)
  const [selectedProjectId, setSelectedProjectId] = useState(urlProjectId ? parseInt(urlProjectId) : null)

  // Load projects list
  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const projects = (projectsData?.data || projectsData) || []

  // Update query when URL params change (e.g., when returning from entity page)
  useEffect(() => {
    const urlQuery = searchParams.get('q') || ''
    const urlProjectId = searchParams.get('project_id')
    if (urlQuery && urlQuery !== searchQuery) {
      setQuery(urlQuery)
      setSearchQuery(urlQuery)
    }
    if (urlProjectId && parseInt(urlProjectId) !== selectedProjectId) {
      setSelectedProjectId(parseInt(urlProjectId))
    }
  }, [searchParams, searchQuery, selectedProjectId])

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', searchQuery, selectedProjectId],
    queryFn: () => searchApi.search(searchQuery, selectedProjectId),
    enabled: searchQuery.length > 0 && selectedProjectId !== null,
  })

  const handleSearch = (e) => {
    e.preventDefault()
    if (!selectedProjectId) {
      alert(t('selectProjectFirst') || 'Please select a project first')
      return
    }
    setSearchQuery(query)
    // Update URL with search query and project_id
    const params = { q: query }
    if (selectedProjectId) {
      params.project_id = selectedProjectId.toString()
    }
    setSearchParams(params)
  }

  const handleProjectChange = (e) => {
    const projectId = e.target.value ? parseInt(e.target.value) : null
    setSelectedProjectId(projectId)
    // Update URL with project_id
    const params = {}
    if (query) params.q = query
    if (projectId) params.project_id = projectId.toString()
    setSearchParams(params)
  }

  const handleExampleClick = (exampleText) => {
    // Remove quotes if present
    const cleanText = exampleText.replace(/^["']|["']$/g, '').trim()
    setQuery(cleanText)
  }

  return (
    <div className="px-4 py-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">{t('search')}</h1>

        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4">
            <select
              value={selectedProjectId || ''}
              onChange={handleProjectChange}
              className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white min-w-[200px]"
              required
            >
              <option value="">{t('selectProject') || 'Select Project'}</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name} ({project.language})
                </option>
              ))}
            </select>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('searchPlaceholder')}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              type="submit"
              className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition flex items-center gap-2"
              disabled={!selectedProjectId}
            >
              <Search className="w-5 h-5" />
              {t('searchButton')}
            </button>
          </div>
          {!selectedProjectId && (
            <p className="text-sm text-red-600 mt-2">{t('selectProjectFirst') || 'Please select a project to search'}</p>
          )}
        </form>

        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">{t('searching')}</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-800">Error: {error.message}</p>
          </div>
        )}

        {data && (
          <div>
            <p className="text-gray-600 mb-4">
              {t('foundResults', { count: (data.data || data).total })}
            </p>

            <div className="space-y-4">
              {((data.data || data).results || []).map((result, idx) => (
                <div
                  key={idx}
                  className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition"
                >
                  <div className="flex items-start gap-4">
                    <FileCode className="w-6 h-6 text-blue-500 mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <Link
                          to={`/entities/${result.entity.id}?from=search&q=${encodeURIComponent(searchQuery)}${selectedProjectId ? `&project_id=${selectedProjectId}` : ''}`}
                          className="text-lg font-semibold text-gray-900 hover:text-blue-600 transition flex items-center gap-2"
                        >
                          {result.entity.name}
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                        <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                          {result.entity.type}
                        </span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
                          {result.match_type}
                        </span>
                      </div>
                      
                      <p className="text-sm text-gray-600 mb-2">
                        {result.entity.file_path}:{result.entity.start_line}-{result.entity.end_line}
                      </p>

                      {result.analysis && (
                        <div className="mt-4 space-y-2">
                          <p className="text-gray-700">{result.analysis.description}</p>
                          
                          <div className="flex flex-wrap gap-2 mt-3">
                            <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded">
                              Complexity: {result.analysis.complexity}
                            </span>
                            {result.analysis.design_patterns?.length > 0 && (
                              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded">
                                Patterns: {result.analysis.design_patterns.join(', ')}
                              </span>
                            )}
                            {result.analysis.ddd_role && (
                              <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded">
                                DDD: {result.analysis.ddd_role}
                              </span>
                            )}
                            {result.analysis.mvc_role && (
                              <span className="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded">
                                MVC: {result.analysis.mvc_role}
                              </span>
                            )}
                          </div>

                          {result.analysis.solid_violations?.length > 0 && (
                            <div className="mt-3">
                              <p className="text-sm font-semibold text-red-700 mb-1">SOLID Violations:</p>
                              <ul className="list-disc list-inside text-sm text-gray-700">
                                {result.analysis.solid_violations.map((violation, vIdx) => (
                                  <li key={vIdx}>
                                    {violation.principle} ({violation.severity})
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!searchQuery && (
          <div className="text-center py-12 text-gray-500">
            {!selectedProjectId ? (
              <p>{t('selectProjectFirst') || 'Please select a project to search'}</p>
            ) : (
              <>
                <p>{t('enterQuery')}</p>
                <p className="text-sm mt-2">{t('examples')}</p>
                <ul className="text-sm mt-2 space-y-2 max-w-md mx-auto">
                  <li 
                    className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleExampleClick(t('example1') || '')}
                  >
                    "{t('example1')}"
                  </li>
                  <li 
                    className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleExampleClick(t('example2') || '')}
                  >
                    "{t('example2')}"
                  </li>
                  <li 
                    className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleExampleClick(t('example3') || '')}
                  >
                    "{t('example3')}"
                  </li>
                  <li 
                    className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                    onClick={() => handleExampleClick(t('example4') || '')}
                  >
                    "{t('example4')}"
                  </li>
                </ul>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
