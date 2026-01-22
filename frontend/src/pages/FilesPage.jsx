import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { projectsApi } from '../services/api'
import { FileText, CheckCircle, XCircle, Search, Filter, ChevronRight, FileCode } from 'lucide-react'
import { useLanguage } from '../utils/i18n'

export default function FilesPage() {
  const { projectId } = useParams()
  const { t } = useLanguage()
  const [searchQuery, setSearchQuery] = useState('')
  const [indexedFilter, setIndexedFilter] = useState(null) // null = all, true = indexed, false = not indexed

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  })

  const { data: filesData, isLoading } = useQuery({
    queryKey: ['project-files', projectId, indexedFilter],
    queryFn: () => projectsApi.getFiles(projectId, { 
      indexed_only: indexedFilter === null ? undefined : indexedFilter 
    }),
    enabled: !!projectId,
  })

  const files = filesData?.data?.files || []
  const totalFiles = filesData?.data?.total_files || 0
  const indexedFiles = filesData?.data?.indexed_files || 0
  const notIndexedFiles = filesData?.data?.not_indexed_files || 0

  const filteredFiles = files.filter(file => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      file.path.toLowerCase().includes(query) ||
      file.relative_path.toLowerCase().includes(query)
    )
  })

  return (
    <div className="px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
            <Link to="/projects" className="hover:text-gray-900">
              {t('projects') || 'Projects'}
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">
              {project?.data?.name || project?.name || 'Project'}
            </span>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">
              {t('files') || 'Files'}
            </span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {t('files') || 'Files'}
          </h1>
          <p className="text-gray-600">
            {totalFiles} {t('files') || 'Files'} in {project?.data?.name || project?.name || 'Project'}
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('totalFiles') || 'Total Files'}</p>
                <p className="text-2xl font-bold text-gray-900">{totalFiles}</p>
              </div>
              <FileText className="w-8 h-8 text-gray-400" />
            </div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('indexedFiles') || 'Indexed Files'}</p>
                <p className="text-2xl font-bold text-green-600">{indexedFiles}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-500" />
            </div>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{t('notIndexedFiles') || 'Not Indexed'}</p>
                <p className="text-2xl font-bold text-orange-600">{notIndexedFiles}</p>
              </div>
              <XCircle className="w-8 h-8 text-orange-500" />
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                placeholder={t('searchFiles') || 'Search files...'}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIndexedFilter(null)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  indexedFilter === null
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {t('all') || 'All'}
              </button>
              <button
                onClick={() => setIndexedFilter(true)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
                  indexedFilter === true
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <CheckCircle className="w-4 h-4" />
                {t('indexed') || 'Indexed'}
              </button>
              <button
                onClick={() => setIndexedFilter(false)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
                  indexedFilter === false
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <XCircle className="w-4 h-4" />
                {t('notIndexed') || 'Not Indexed'}
              </button>
            </div>
          </div>
        </div>

        {/* Files List */}
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <p className="mt-4 text-gray-600">{t('loading') || 'Loading...'}</p>
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>{t('noFilesFound') || 'No files found'}</p>
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('file') || 'File'}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('status') || 'Status'}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('entities') || 'Entities'}
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {t('indexedAt') || 'Indexed At'}
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredFiles.map((file, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <FileCode className="w-4 h-4 text-gray-400" />
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {file.relative_path}
                            </div>
                            <div className="text-xs text-gray-500 truncate max-w-md">
                              {file.path}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {file.is_indexed ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            <CheckCircle className="w-3 h-3" />
                            {t('indexed') || 'Indexed'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                            <XCircle className="w-3 h-3" />
                            {t('notIndexed') || 'Not Indexed'}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {file.entity_count || 0}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {file.indexed_at ? (
                          new Date(file.indexed_at).toLocaleString()
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
              <p className="text-sm text-gray-600">
                {t('showing') || 'Showing'} {filteredFiles.length} {t('of') || 'of'} {files.length} {t('files') || 'files'}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
