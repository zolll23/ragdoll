import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { providersApi } from '../services/api'
import { Settings, Plus, RefreshCw, Trash2, CheckCircle, XCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import i18n from '../utils/i18n'

export default function ProvidersPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingProvider, setEditingProvider] = useState(null)
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    base_url: '',
    api_key: '',
    auth_key: '', // For GigaChat
    verify_ssl: false, // For GigaChat (default false due to self-signed certs)
    config: {},
    model: '',
    is_active: true,
    is_default: false,
  })
  const [availableModels, setAvailableModels] = useState([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [showApiKey, setShowApiKey] = useState({})

  const queryClient = useQueryClient()

  const { data: providers, isLoading } = useQuery({
    queryKey: ['providers'],
    queryFn: () => providersApi.list(),
  })

  const { data: currentProvider } = useQuery({
    queryKey: ['current-provider'],
    queryFn: () => providersApi.getCurrent(),
    retry: false, // Don't retry if no provider is set
  })

  const createMutation = useMutation({
    mutationFn: providersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries(['providers'])
      queryClient.invalidateQueries(['current-provider'])
      setShowForm(false)
      resetForm()
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => providersApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['providers'])
      queryClient.invalidateQueries(['current-provider'])
      setEditingProvider(null)
      setShowForm(false)
      resetForm()
    },
    onError: (error) => {
      console.error('Update error:', error)
      alert(`Error updating provider: ${error.response?.data?.detail || error.message}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: providersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries(['providers'])
      queryClient.invalidateQueries(['current-provider'])
    },
    onError: (error) => {
      console.error('Delete error:', error)
      alert(`Error deleting provider: ${error.response?.data?.detail || error.message}`)
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      display_name: '',
      base_url: '',
      api_key: '',
      auth_key: '',
      verify_ssl: false,
      config: {},
      model: '',
      is_active: true,
      is_default: false,
    })
  }

  const handleEdit = async (provider) => {
    setEditingProvider(provider.id)
    setFormData({
      name: provider.name,
      display_name: provider.display_name,
      base_url: provider.base_url || '',
      api_key: '', // Don't show existing key
      auth_key: '', // Don't show existing auth_key
      verify_ssl: (provider.config && provider.config.verify_ssl !== undefined) ? provider.config.verify_ssl : false,
      config: provider.config || {},
      model: provider.model || '',
      is_active: provider.is_active,
      is_default: provider.is_default,
    })
    setShowForm(true)
    // Load models for this provider
    await loadModelsForProvider(provider.id)
  }

  const loadModelsForProvider = async (providerId) => {
    if (!providerId) {
      setAvailableModels([])
      return
    }
    setLoadingModels(true)
    try {
      const response = await providersApi.getModels(providerId)
      if (response.data && response.data.models) {
        setAvailableModels(response.data.models)
      } else {
        setAvailableModels([])
      }
    } catch (error) {
      console.error('Error loading models:', error)
      setAvailableModels([])
    } finally {
      setLoadingModels(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const data = { ...formData }
    // Remove empty fields for update
    if (editingProvider) {
      const updateData = {
        display_name: data.display_name,
        is_active: data.is_active,
        is_default: data.is_default,
      }
      if (data.base_url) updateData.base_url = data.base_url
      if (data.api_key) updateData.api_key = data.api_key
      if (data.model) updateData.model = data.model
      
      // For GigaChat, save auth_key and verify_ssl in config
      if (data.name === 'gigachat') {
        const config = {}
        if (data.auth_key) config.auth_key = data.auth_key
        if (data.verify_ssl !== undefined) config.verify_ssl = data.verify_ssl
        else config.verify_ssl = false // Default
        
        // Merge with existing config
        const provider = providers?.data?.find(p => p.id === editingProvider)
        if (provider && provider.config) {
          Object.assign(config, provider.config)
          if (data.auth_key) config.auth_key = data.auth_key
          if (data.verify_ssl !== undefined) config.verify_ssl = data.verify_ssl
        }
        
        if (Object.keys(config).length > 0) {
          updateData.config = config
        }
      }
      
      updateMutation.mutate({ id: editingProvider, data: updateData })
    } else {
      // For create, all fields are required
      if (!data.base_url) delete data.base_url
      if (!data.api_key) delete data.api_key
      if (!data.model) delete data.model
      
      // For GigaChat, save auth_key and verify_ssl in config
      if (data.name === 'gigachat') {
        data.config = {
          auth_key: data.auth_key || '',
          verify_ssl: data.verify_ssl !== undefined ? data.verify_ssl : false
        }
        delete data.auth_key // Remove from top level
        delete data.verify_ssl // Remove from top level
      }
      
      createMutation.mutate(data)
    }
  }

  const providerTypes = [
    { value: 'ollama', label: 'Ollama', defaultUrl: 'http://192.168.22.146:11434' },
    { value: 'openai', label: 'OpenAI', defaultUrl: '' },
    { value: 'anthropic', label: 'Anthropic', defaultUrl: '' },
    { value: 'gigachat', label: 'GigaChat', defaultUrl: 'https://gigachat.devices.sberbank.ru/api/v1' },
    { value: 'vllm', label: 'vLLM', defaultUrl: 'http://192.168.22.146:8000' },
  ]

  return (
    <div className="px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold">{i18n.t('llmProviders')}</h1>
            <p className="text-gray-600 mt-1">{i18n.t('manageProviders')}</p>
            {currentProvider && currentProvider.data && (
              <div className="mt-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg inline-block">
                <span className="text-sm text-blue-800">
                  <strong>{i18n.t('currentProvider')}:</strong> {currentProvider.data.display_name}
                  {currentProvider.data.model && ` (${i18n.t('model')}: ${currentProvider.data.model})`}
                </span>
              </div>
            )}
            {!currentProvider && (
              <div className="mt-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg inline-block">
                <span className="text-sm text-yellow-800">
                  {i18n.t('noDefaultProvider')}
                </span>
              </div>
            )}
          </div>
          <button
            onClick={() => {
              setEditingProvider(null)
              resetForm()
              setShowForm(!showForm)
            }}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-700 transition flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            {i18n.t('addProvider')}
          </button>
        </div>

        {showForm && (
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-6">
            <h2 className="text-xl font-semibold mb-4">
              {editingProvider ? i18n.t('editProvider') : i18n.t('addProvider')}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {i18n.t('providerType')} *
                </label>
                <select
                  value={formData.name}
                  onChange={async (e) => {
                    const selected = providerTypes.find(t => t.value === e.target.value)
                    setFormData({
                      ...formData,
                      name: e.target.value,
                      base_url: selected?.defaultUrl || '',
                      model: '', // Reset model when provider changes
                    })
                    setAvailableModels([])
                    // If editing, try to load models for this provider type
                    if (editingProvider) {
                      // Find provider by name to get ID
                      const provider = providers?.data?.find(p => p.name === e.target.value)
                      if (provider) {
                        await loadModelsForProvider(provider.id)
                      }
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                  disabled={!!editingProvider}
                >
                  <option value="">{i18n.t('selectProvider')}</option>
                  {providerTypes.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {i18n.t('displayName')} *
                </label>
                <input
                  type="text"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {i18n.t('baseUrl')}
                </label>
                <input
                  type="text"
                  value={formData.base_url}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                  placeholder={providerTypes.find(t => t.value === formData.name)?.defaultUrl || ''}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              {formData.name !== 'gigachat' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {i18n.t('apiKey')} {editingProvider && `(${i18n.t('leaveEmptyToKeep')})`}
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey[editingProvider || 'new'] ? 'text' : 'password'}
                      value={formData.api_key}
                      onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                      className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder={editingProvider ? i18n.t('leaveEmptyToKeep') : ''}
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey({
                        ...showApiKey,
                        [editingProvider || 'new']: !showApiKey[editingProvider || 'new']
                      })}
                      className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    >
                      {showApiKey[editingProvider || 'new'] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
              )}
              {formData.name === 'gigachat' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Authorization Key (Basic) * {editingProvider && `(${i18n.t('leaveEmptyToKeep')})`}
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey[editingProvider || 'new'] ? 'text' : 'password'}
                      value={formData.auth_key}
                      onChange={(e) => setFormData({ ...formData, auth_key: e.target.value })}
                      className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                      placeholder={editingProvider ? i18n.t('leaveEmptyToKeep') : 'Used to get access tokens automatically'}
                      required={!editingProvider}
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey({
                        ...showApiKey,
                        [editingProvider || 'new']: !showApiKey[editingProvider || 'new']
                      })}
                      className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
                    >
                      {showApiKey[editingProvider || 'new'] ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    This key is used to automatically obtain and refresh access tokens (valid for 30 minutes)
                  </p>
                  <label className="flex items-center gap-2 mt-2">
                    <input
                      type="checkbox"
                      checked={formData.verify_ssl === true}
                      onChange={(e) => {
                        setFormData({ ...formData, verify_ssl: e.target.checked })
                      }}
                      className="w-4 h-4"
                    />
                    <span className="text-sm text-gray-700">Verify SSL certificates (uncheck if using self-signed certs)</span>
                  </label>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {i18n.t('defaultModel')}
                </label>
                <div className="flex gap-2">
                  <select
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">{i18n.t('selectModel')}</option>
                    {availableModels.map(model => (
                      <option key={model.id} value={model.id}>{model.name}</option>
                    ))}
                  </select>
                  {formData.name && (
                    <button
                      type="button"
                      onClick={() => {
                        if (editingProvider) {
                          const provider = providers?.data?.find(p => p.id === editingProvider)
                          if (provider) loadModelsForProvider(provider.id)
                        } else {
                          // For new provider, we need to create it first to get models
                          // So we'll just show a message
                          alert(i18n.t('saveProviderFirst'))
                        }
                      }}
                      disabled={loadingModels}
                      className="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition text-sm"
                      title={i18n.t('refreshModels')}
                    >
                      <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
                    </button>
                  )}
                </div>
                {formData.name && !editingProvider && (
                  <p className="text-xs text-gray-500 mt-1">{i18n.t('saveProviderToLoadModels')}</p>
                )}
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">{i18n.t('active')}</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">{i18n.t('default')}</span>
                </label>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <button
                type="submit"
                className="bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold hover:bg-blue-700"
              >
                {editingProvider ? i18n.t('update') : i18n.t('create')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false)
                  setEditingProvider(null)
                  resetForm()
                }}
                className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-semibold hover:bg-gray-300"
              >
                {i18n.t('cancel')}
              </button>
            </div>
          </form>
        )}

        {isLoading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        )}

        {providers && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {providers.data.map((provider) => (
              <ProviderCard
                key={provider.id}
                provider={provider}
                onEdit={handleEdit}
                onDelete={(id) => {
                  if (confirm(i18n.t('deleteProviderConfirm'))) {
                    deleteMutation.mutate(id)
                  }
                }}
              />
            ))}
          </div>
        )}

        {providers && providers.data.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <Settings className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>{i18n.t('noProviders')}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function ProviderCard({ provider, onEdit, onDelete }) {
  const [models, setModels] = useState(null)
  const [loadingModels, setLoadingModels] = useState(false)
  const [updatingModel, setUpdatingModel] = useState(false)
  const queryClient = useQueryClient()

  const loadModels = async () => {
    setLoadingModels(true)
    try {
      const response = await providersApi.getModels(provider.id)
      setModels(response.data)
    } catch (error) {
      setModels({ error: error.message, models: [] })
    } finally {
      setLoadingModels(false)
    }
  }

  const selectModel = async (modelId) => {
    setUpdatingModel(true)
    try {
      await providersApi.update(provider.id, { model: modelId })
      // Refresh providers list
      queryClient.invalidateQueries(['providers'])
      queryClient.invalidateQueries(['current-provider'])
    } catch (error) {
      console.error('Error selecting model:', error)
      alert(`Error selecting model: ${error.response?.data?.detail || error.message}`)
    } finally {
      setUpdatingModel(false)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{provider.display_name}</h3>
          <p className="text-sm text-gray-600">{provider.name}</p>
        </div>
        <div className="flex items-center gap-2">
          {provider.is_active ? (
            <CheckCircle className="w-5 h-5 text-green-500" title={i18n.t('active')} />
          ) : (
            <XCircle className="w-5 h-5 text-gray-400" title={i18n.t('inactive')} />
          )}
          {provider.is_default && (
            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded">
              {i18n.t('default')}
            </span>
          )}
        </div>
      </div>

      {provider.base_url && (
        <p className="text-sm text-gray-500 mb-2 break-all">
          <span className="font-medium">URL:</span> {provider.base_url}
        </p>
      )}
      {provider.model && (
        <p className="text-sm text-gray-500 mb-2">
          <span className="font-medium">{i18n.t('model')}:</span> {provider.model}
        </p>
      )}

      <div className="flex gap-2 mt-4">
        <button
          onClick={() => onEdit(provider)}
          className="flex-1 bg-blue-50 text-blue-600 px-3 py-2 rounded-lg text-sm font-semibold hover:bg-blue-100 transition"
        >
          {i18n.t('edit')}
        </button>
        <button
          onClick={loadModels}
          disabled={loadingModels}
          className="bg-green-50 text-green-600 px-3 py-2 rounded-lg text-sm font-semibold hover:bg-green-100 transition flex items-center gap-1"
        >
          <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
          {i18n.t('models')}
        </button>
        <button
          onClick={() => onDelete(provider.id)}
          className="bg-red-50 text-red-600 px-3 py-2 rounded-lg text-sm font-semibold hover:bg-red-100 transition"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {models && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          {models.error ? (
            <div className="text-sm text-red-600 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {models.error}
            </div>
          ) : (
            <div>
              <p className="text-sm font-medium mb-2">
                {i18n.t('availableModels')}: {models.models?.length || 0}
              </p>
              {models.models && models.models.length > 0 && (
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {models.models.map((model) => (
                    <button
                      key={model.id}
                      onClick={() => selectModel(model.id)}
                      disabled={updatingModel || provider.model === model.id}
                      className={`w-full text-left text-xs px-2 py-1 rounded transition ${
                        provider.model === model.id
                          ? 'bg-blue-100 text-blue-700 font-semibold cursor-default'
                          : 'bg-gray-50 hover:bg-gray-100 text-gray-700 cursor-pointer'
                      } ${updatingModel ? 'opacity-50 cursor-not-allowed' : ''}`}
                      title={provider.model === model.id ? i18n.t('currentModel') || 'Current model' : i18n.t('clickToSelect') || 'Click to select'}
                    >
                      {model.name || model.id}
                      {provider.model === model.id && ' ✓'}
                    </button>
                  ))}
                </div>
              )}
              {models.error && (
                <div className="text-xs text-red-600 mt-1">
                  {models.error}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

