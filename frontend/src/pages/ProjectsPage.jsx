import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { projectsApi } from '../services/api'
import { FolderOpen, Plus, RefreshCw, Trash2, AlertCircle, Globe, List, Code2, Play, Square, X, FileText } from 'lucide-react'
import { useLanguage } from '../utils/i18n'

export default function ProjectsPage() {
  const { t } = useLanguage()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    path: '',
    language: 'python',
    ui_language: 'EN',
  })

  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const createMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['projects'])
      setShowForm(false)
      setFormData({ name: '', path: '', language: 'python', ui_language: 'EN' })
    },
  })

  const reindexMutation = useMutation({
    mutationFn: ({ id, onlyFailed }) => {
      console.log('Reindex mutation called:', { id, onlyFailed })
      return projectsApi.reindex(id, onlyFailed)
    },
    onSuccess: (response, variables) => {
      console.log('Reindex success:', response, variables)
      alert(variables.onlyFailed ? t('reindexFailedStarted') : t('reindexStarted'))
      queryClient.invalidateQueries(['projects'])
      queryClient.invalidateQueries(['project-progress', variables.id])
    },
    onError: (err) => {
      console.error('Reindex error:', err)
      alert(`${t('error')}: ${err.response?.data?.detail || err.message}`)
    },
  })

  const deleteEntitiesMutation = useMutation({
    mutationFn: ({ id, options }) => projectsApi.deleteEntities(id, options),
    onSuccess: () => {
      alert(t('deleteEntitiesStarted'))
      queryClient.invalidateQueries(['projects'])
      queryClient.invalidateQueries(['project-progress'])
      queryClient.invalidateQueries(['entities'])
    },
    onError: (err) => {
      alert(`${t('error')}: ${err.response?.data?.detail || err.message}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: projectsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['projects'])
    },
  })

  const stopIndexingMutation = useMutation({
    mutationFn: projectsApi.stopIndexing,
    onSuccess: () => {
      queryClient.invalidateQueries(['projects'])
      alert(t('indexingStopped'))
    },
    onError: (err) => {
      alert(`${t('error')}: ${err.response?.data?.detail || err.message}`)
    },
  })

  const resumeIndexingMutation = useMutation({
    mutationFn: projectsApi.resumeIndexing,
    onSuccess: () => {
      queryClient.invalidateQueries(['projects'])
      alert(t('indexingResumed'))
    },
    onError: (err) => {
      alert(`${t('error')}: ${err.response?.data?.detail || err.message}`)
    },
  })

  const startIndexingMutation = useMutation({
    mutationFn: projectsApi.startIndexing,
    onSuccess: () => {
      queryClient.invalidateQueries(['projects'])
      alert(t('indexingStarted') || 'Indexing started')
    },
    onError: (err) => {
      alert(`${t('error')}: ${err.response?.data?.detail || err.message}`)
    },
  })

  const updateLanguageMutation = useMutation({
    mutationFn: ({ id, language }) => projectsApi.updateLanguage(id, language),
    onSuccess: () => {
      queryClient.invalidateQueries(['projects'])
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  // Auto-refresh progress for indexing projects
  useEffect(() => {
    const projects = data?.data || data
    if (!projects) return
    
    const indexingProjects = projects.filter(p => {
      // Check if project might be indexing (simple heuristic)
      return true // We'll check progress for all
    })
    
    if (indexingProjects.length > 0) {
      const interval = setInterval(() => {
        indexingProjects.forEach(project => {
          queryClient.invalidateQueries(['project-progress', project.id])
        })
      }, 2000) // Refresh every 2 seconds
      
      return () => clearInterval(interval)
    }
  }, [data, queryClient])

  return (
    <div className="px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold">{t('projects')}</h1>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-700 transition flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            {t('addProject')}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('projectName')}
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('path')}
                </label>
                <input
                  type="text"
                  value={formData.path}
                  onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                  placeholder="/path/to/project"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('language')}
                </label>
                <select
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="python">Python</option>
                  <option value="php">PHP</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('uiLanguage')}
                </label>
                <select
                  value={formData.ui_language}
                  onChange={(e) => setFormData({ ...formData, ui_language: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="EN">English</option>
                  <option value="RU">Русский</option>
                </select>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-700"
              >
                {t('create')}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-semibold hover:bg-gray-300"
              >
                {t('cancel')}
              </button>
            </div>
          </form>
        )}

        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-red-800">Error: {error.message}</p>
          </div>
        )}

        {data && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {(data.data || data).map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onReindex={() => reindexMutation.mutate({ id: project.id, onlyFailed: false })}
                onReindexFailed={(id) => {
                  console.log('onReindexFailed called with id:', id)
                  if (confirm(t('reindexFailedConfirm'))) {
                    console.log('User confirmed, calling reindexMutation.mutate')
                    reindexMutation.mutate({ id, onlyFailed: true })
                  } else {
                    console.log('User cancelled reindex')
                  }
                }}
                onDeleteEntities={(id) => {
                  if (confirm(t('deleteAllEntitiesConfirm'))) {
                    deleteEntitiesMutation.mutate({ id, options: { delete_all: true } })
                  }
                }}
                onDelete={() => {
                  if (confirm(t('deleteConfirm'))) {
                    deleteMutation.mutate(project.id)
                  }
                }}
                onLanguageChange={(lang) => updateLanguageMutation.mutate({ id: project.id, language: lang })}
                onStopIndexing={(id) => stopIndexingMutation.mutate(id)}
                onResumeIndexing={(id) => resumeIndexingMutation.mutate(id)}
                onStartIndexing={(id) => startIndexingMutation.mutate(id)}
              />
            ))}
          </div>
        )}

        {data && (data.data || data).length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <FolderOpen className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>{t('noProjects')}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function ProjectCard({ project, onReindex, onReindexFailed, onDelete, onDeleteEntities, onLanguageChange, onStopIndexing, onResumeIndexing, onStartIndexing }) {
  const { t } = useLanguage()
  const { data: progress, isLoading: progressLoading } = useQuery({
    queryKey: ['project-progress', project.id],
    queryFn: () => projectsApi.getProgress(project.id),
      refetchInterval: (data) => {
        // Auto-refresh if indexing or reindexing failed
        const progress = data?.data || data
        return (progress?.is_indexing || progress?.is_reindexing_failed) ? 2000 : false
      },
  })

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <FolderOpen className="w-6 h-6 text-blue-500" />
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {project.name}
            </h3>
            <p className="text-sm text-gray-600">{project.language}</p>
          </div>
        </div>
      </div>
      
      <p className="text-sm text-gray-500 mb-4 break-all">
        {project.path}
      </p>

      {/* Progress */}
      {progress && !progressLoading && (
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">
              {t('progress')}
            </span>
            <span className="text-sm text-gray-600">
              {((progress.data || progress).progress_percent || 0).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${((progress.data || progress).progress_percent || 0)}%` }}
            />
          </div>
          <div className="flex flex-col gap-1 text-xs text-gray-500 mt-2">
            <div className="flex justify-between">
              <span>
                {t('filesIndexed')}: {(progress.data || progress).indexed_files} / {(progress.data || progress).total_files}
              </span>
              <span>
                {t('entities')}: {(progress.data || progress).total_entities}
              </span>
            </div>
            {((progress.data || progress).entities_with_failed_analysis > 0 || (progress.data || progress).entities_without_analysis > 0) && (
              <div className="flex justify-between text-orange-600 font-medium">
                <span>
                  {t('failedAnalysis') || 'Failed analysis'}: {(progress.data || progress).entities_with_failed_analysis || 0}
                </span>
                <span>
                  {t('withoutAnalysis') || 'Without analysis'}: {(progress.data || progress).entities_without_analysis || 0}
                </span>
              </div>
            )}
            {project.tokens_used > 0 && (
              <div className="flex justify-between">
                <span>
                  {t('tokensUsed')}: {project.tokens_used.toLocaleString()}
                </span>
              </div>
            )}
          </div>
          {(progress.data || progress).is_indexing && (
            <div className="mt-2 space-y-1">
              <div className="text-sm text-blue-600 flex items-center gap-1">
                <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse" />
                {t('indexing')}
              </div>
              {(progress.data || progress).current_file && (
                <div className="text-xs text-gray-600 ml-3">
                  {t('currentFile') || 'Current file'}: {(progress.data || progress).current_file}
                </div>
              )}
              {(progress.data || progress).status_message && (
                <div className="text-xs text-gray-500 ml-3 italic">
                  {(progress.data || progress).status_message}
                </div>
              )}
            </div>
          )}
          {(progress.data || progress).is_reindexing_failed && (
            <div className="mt-2 space-y-1 border-t border-gray-200 pt-2">
              <div className="text-sm text-orange-600 flex items-center gap-1">
                <div className="w-2 h-2 bg-orange-600 rounded-full animate-pulse" />
                {t('reindexingFailed') || 'Reindexing failed entities'}
              </div>
              {(progress.data || progress).failed_entities_count > 0 && (
                <div className="text-xs text-gray-600 ml-3">
                  {t('failedEntities') || 'Failed entities'}: {(progress.data || progress).failed_entities_count}
                </div>
              )}
              {(progress.data || progress).reindexed_failed_count > 0 && (
                <div className="text-xs text-gray-600 ml-3">
                  {t('reindexed') || 'Reindexed'}: {(progress.data || progress).reindexed_failed_count}/{(progress.data || progress).failed_entities_count}
                </div>
              )}
              {(progress.data || progress).reindexing_failed_status && (
                <div className="text-xs text-gray-500 ml-3 italic">
                  {(progress.data || progress).reindexing_failed_status}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Language selector */}
      <div className="mb-4">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          {t('uiLanguage')}
        </label>
        <select
          value={project.ui_language || 'EN'}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500"
        >
          <option value="EN">English</option>
          <option value="RU">Русский</option>
        </select>
      </div>

      {/* Actions - vertical list with icons */}
      <div className="border-t border-gray-200 pt-4 mt-4">
        <div className="space-y-2">
          <Link
            to={`/projects/${project.id}/entities`}
            className="w-full bg-green-50 text-green-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-green-100 transition flex items-center gap-2"
          >
            <List className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('viewEntities')}</span>
          </Link>
          
          <Link
            to={`/projects/${project.id}/files`}
            className="w-full bg-indigo-50 text-indigo-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-indigo-100 transition flex items-center gap-2"
          >
            <FileText className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('viewFiles') || 'View Files'}</span>
          </Link>
          
          <Link
            to={`/similar-code?project_id=${project.id}`}
            className="w-full bg-purple-50 text-purple-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-purple-100 transition flex items-center gap-2"
          >
            <Code2 className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('similarCode') || 'Similar Code'}</span>
          </Link>
          
          <button
            onClick={onReindex}
            className="w-full bg-blue-50 text-blue-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-100 transition flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('reindex')}</span>
          </button>
          
          <button
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              console.log('Reindex failed button clicked for project:', project.id)
              if (onReindexFailed) {
                onReindexFailed(project.id)
              } else {
                console.error('onReindexFailed is not defined!')
              }
            }}
            className="w-full bg-yellow-50 text-yellow-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-yellow-100 transition flex items-center gap-2"
            title={t('reindexFailed')}
            type="button"
          >
            <RefreshCw className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('reindexFailed')}</span>
          </button>
          
          {project.is_indexing ? (
            <button
              onClick={() => onStopIndexing && onStopIndexing(project.id)}
              className="w-full bg-orange-50 text-orange-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-orange-100 transition flex items-center gap-2"
              title={t('stopIndexing')}
            >
              <Square className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{t('stopIndexing')}</span>
            </button>
          ) : (
            <>
              {project.last_indexed_file_path ? (
                <button
                  onClick={() => onResumeIndexing && onResumeIndexing(project.id)}
                  className="w-full bg-green-50 text-green-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-green-100 transition flex items-center gap-2"
                  title={t('resumeIndexing')}
                >
                  <Play className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">{t('resumeIndexing')}</span>
                </button>
              ) : (
                <button
                  onClick={() => onStartIndexing && onStartIndexing(project.id)}
                  className="w-full bg-blue-50 text-blue-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-blue-100 transition flex items-center gap-2"
                  title={t('startIndexing') || 'Start Indexing'}
                >
                  <Play className="w-4 h-4 flex-shrink-0" />
                  <span className="truncate">{t('startIndexing') || 'Start Indexing'}</span>
                </button>
              )}
            </>
          )}
          
          <button
            onClick={() => onDeleteEntities && onDeleteEntities(project.id)}
            className="w-full bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-red-100 transition flex items-center gap-2"
            title={t('deleteEntities')}
          >
            <Trash2 className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('deleteEntities')}</span>
          </button>
          
          <button
            onClick={onDelete}
            className="w-full bg-red-50 text-red-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-red-100 transition flex items-center gap-2"
            title={t('delete')}
          >
            <X className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{t('delete')}</span>
          </button>
        </div>
      </div>
    </div>
  )
}
