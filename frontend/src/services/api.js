import axios from 'axios'

const API_URL = import.meta.env.REACT_APP_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const projectsApi = {
  list: () => api.get('/api/projects'),
  get: (id) => api.get(`/api/projects/${id}`),
  create: (data) => api.post('/api/projects', data),
  reindex: (id, onlyFailed = false) => api.post(`/api/projects/${id}/reindex?only_failed=${onlyFailed}`),
  delete: (id) => api.delete(`/api/projects/${id}`),
  getProgress: (id) => api.get(`/api/projects/${id}/progress`),
  updateLanguage: (id, language) => api.patch(`/api/projects/${id}?ui_language=${language}`),
  deleteEntities: (id, options = {}) => {
    const params = new URLSearchParams()
    if (options.delete_all) params.append('delete_all', 'true')
    if (options.file_id) params.append('file_id', options.file_id)
    if (options.entity_ids) params.append('entity_ids', options.entity_ids.join(','))
    return api.post(`/api/projects/${id}/delete-entities?${params.toString()}`)
  },
  stopIndexing: (id) => api.post(`/api/projects/${id}/indexing/stop`),
  resumeIndexing: (id) => api.post(`/api/projects/${id}/indexing/resume`),
  startIndexing: (id) => api.post(`/api/projects/${id}/indexing/start`),
  getFiles: (id, params = {}) => api.get(`/api/projects/${id}/files`, { params }),
}

export const searchApi = {
  search: (query, projectId = null) => {
    return api.post('/api/search', {
      query,
      project_id: projectId,
    })
  },
}

export const entitiesApi = {
  get: (id) => api.get(`/api/entities/${id}`),
  getAnalysis: (id) => api.get(`/api/entities/${id}/analysis`),
  list: (params) => api.get('/api/entities', { params }),
  getDependencies: (id) => api.get(`/api/entities/${id}/dependencies`),
  getSimilar: (id, params = {}) => api.get(`/api/entities/${id}/similar`, { params }),
  searchSimilar: (params = {}) => api.get('/api/entities/similar/search', { params }),
}

export const providersApi = {
  list: (includeKeys = false) => api.get('/api/providers', { params: { include_keys: includeKeys } }),
  get: (id, includeKey = false) => api.get(`/api/providers/${id}`, { params: { include_key: includeKey } }),
  getCurrent: () => api.get('/api/providers/current'),
  create: (data) => api.post('/api/providers', data),
  update: (id, data) => api.patch(`/api/providers/${id}`, data),
  delete: (id) => api.delete(`/api/providers/${id}`),
  getModels: (id) => api.get(`/api/providers/${id}/models`),
}

export default api

