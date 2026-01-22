import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { MessageSquare, Send, Loader, ChevronRight, Code2, Search, Info, X } from 'lucide-react'
import { useLanguage } from '../utils/i18n'
import { projectsApi } from '../services/api'

// Goose API URL - use environment variable or default to localhost:8080
// Frontend runs in browser, so localhost refers to the host machine
// Port 8080 should be exposed in docker-compose.yml
const GOOSE_API_URL = import.meta.env.REACT_APP_GOOSE_API_URL || 'http://localhost:8080'

export default function GoosePage() {
  const { t } = useLanguage()
  const [question, setQuestion] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState(null)
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedLogRequestId, setSelectedLogRequestId] = useState(null)
  const [logContent, setLogContent] = useState(null)
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const askGoose = async () => {
    if (!question.trim()) return

    const userMessage = {
      role: 'user',
      content: question,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setQuestion('')
    setIsLoading(true)

    try {
      const response = await fetch(`${GOOSE_API_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          project_id: selectedProjectId
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      // Debug: log request_id
      console.log('Goose response data:', data)
      console.log('Request ID:', data.request_id)
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || 'No answer received',
        timestamp: new Date().toISOString(),
        requestId: data.request_id || null
      }
      
      // Debug: log message
      console.log('Assistant message:', assistantMessage)
      console.log('Has requestId:', !!assistantMessage.requestId)

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error asking Goose:', error)
      let errorMsg = error.message
      
      // Provide more helpful error messages
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMsg = `Не удалось подключиться к Goose сервису на ${GOOSE_API_URL}. Убедитесь, что сервис запущен: docker compose up goose`
      } else if (error.message.includes('404')) {
        errorMsg = `Goose сервис не найден. Проверьте, что сервис запущен и доступен на ${GOOSE_API_URL}`
      } else if (error.message.includes('500')) {
        errorMsg = `Ошибка сервера Goose. Проверьте логи: docker logs coderag_goose`
      }
      
      const errorMessage = {
        role: 'assistant',
        content: `Ошибка: ${errorMsg}`,
        timestamp: new Date().toISOString(),
        isError: true
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      askGoose()
    }
  }

  const clearMessages = () => {
    setMessages([])
  }

  const fetchLogs = async (requestId) => {
    if (!requestId) return
    
    setIsLoadingLogs(true)
    setSelectedLogRequestId(requestId)
    
    try {
      const response = await fetch(`${GOOSE_API_URL}/logs/${requestId}`)
      if (response.ok) {
        const text = await response.text()
        setLogContent(text)
      } else {
        setLogContent('Логи не найдены для этого запроса')
      }
    } catch (error) {
      console.error('Error fetching logs:', error)
      setLogContent('Ошибка при загрузке логов')
    } finally {
      setIsLoadingLogs(false)
    }
  }

  const closeLogModal = () => {
    setSelectedLogRequestId(null)
    setLogContent(null)
  }

  return (
    <div className="px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
            <Link to="/" className="hover:text-gray-900">
              {t('home') || 'Home'}
            </Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-gray-900 font-medium">
              {t('goose') || 'Goose AI Assistant'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {t('goose') || 'Goose AI Assistant'}
              </h1>
              <p className="text-gray-600">
                {t('gooseDescription') || 'Ask questions about your codebase using natural language'}
              </p>
            </div>
            {messages.length > 0 && (
              <button
                onClick={clearMessages}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                {t('clear') || 'Clear'}
              </button>
            )}
          </div>
        </div>

        {/* Project Selector */}
        {projects && (projects.data || projects).length > 0 && (
          <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {t('project') || 'Project'} (optional):
            </label>
            <select
              value={selectedProjectId || ''}
              onChange={(e) => setSelectedProjectId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full md:w-auto px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">{t('allProjects') || 'All Projects'}</option>
              {(projects.data || projects).map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Chat Interface */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm flex flex-col" style={{ height: 'calc(100vh - 300px)', minHeight: '500px' }}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
                <MessageSquare className="w-16 h-16 mb-4 text-gray-400" />
                <h3 className="text-lg font-medium mb-2">
                  {t('startConversation') || 'Start a conversation with Goose'}
                </h3>
                <p className="text-sm mb-4">
                  {t('gooseExamples') || 'Try asking:'}
                </p>
                <div className="space-y-2 text-sm">
                  <div className="bg-gray-50 px-4 py-2 rounded-lg">
                    "Какие статусы отправки письма есть?"
                  </div>
                  <div className="bg-gray-50 px-4 py-2 rounded-lg">
                    "Какой таймаут используется для отправки писем?"
                  </div>
                  <div className="bg-gray-50 px-4 py-2 rounded-lg">
                    "Найди методы с высокой сложностью"
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl rounded-lg p-4 relative ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : message.isError
                        ? 'bg-red-50 text-red-800 border border-red-200'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <div className="flex items-start gap-2 mb-1">
                      {message.role === 'assistant' && (
                        <Code2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="font-medium">
                            {message.role === 'user' ? (t('you') || 'You') : 'Goose'}
                          </div>
                          {message.role === 'assistant' && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                e.preventDefault()
                                console.log('Icon clicked, requestId:', message.requestId)
                                if (message.requestId) {
                                  fetchLogs(message.requestId)
                                } else {
                                  alert('Request ID не найден. Проверьте консоль для отладки.')
                                }
                              }}
                              onMouseDown={(e) => e.stopPropagation()}
                              className={`transition-colors z-10 relative ${
                                message.requestId 
                                  ? 'text-gray-400 hover:text-gray-600 cursor-pointer' 
                                  : 'text-gray-300 cursor-not-allowed'
                              }`}
                              title={message.requestId ? "Показать логи обработки запроса" : "Логи недоступны (нет request_id)"}
                              disabled={!message.requestId}
                              type="button"
                            >
                              <Info className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                        <div className="whitespace-pre-wrap break-words">
                          {message.content}
                        </div>
                        <div className="text-xs mt-2 opacity-70">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-4 max-w-3xl">
                  <div className="flex items-center gap-2">
                    <Loader className="w-5 h-5 animate-spin text-gray-600" />
                    <span className="text-gray-600">{t('thinking') || 'Thinking...'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={t('askQuestion') || 'Ask a question about your code...'}
                  className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={3}
                  disabled={isLoading}
                />
                <div className="absolute bottom-3 right-3 text-xs text-gray-400">
                  {t('pressEnter') || 'Press Enter to send, Shift+Enter for new line'}
                </div>
              </div>
              <button
                onClick={askGoose}
                disabled={!question.trim() || isLoading}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 transition"
              >
                <Send className="w-5 h-5" />
                <span>{t('send') || 'Send'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Log Modal */}
      {selectedLogRequestId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={closeLogModal}>
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-gray-900">Логи обработки запроса</h3>
                <button
                  onClick={closeLogModal}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">Request ID: {selectedLogRequestId}</p>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {isLoadingLogs ? (
                <div className="flex items-center justify-center py-8">
                  <Loader className="w-6 h-6 animate-spin text-gray-600" />
                  <span className="ml-2 text-gray-600">Загрузка логов...</span>
                </div>
              ) : (
                <pre className="text-xs font-mono bg-gray-50 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap break-words">
                  {logContent || 'Логи не найдены'}
                </pre>
              )}
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end">
              <button
                onClick={closeLogModal}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                {t('close') || 'Закрыть'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
