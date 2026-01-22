import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ChevronRight, X, Loader } from 'lucide-react'
import { useLanguage } from '../utils/i18n'
import { projectsApi } from '../services/api'
import ProjectSidebar from '../components/ProjectSidebar'
import RoleSelector from '../components/RoleSelector'
import ChatWindow from '../components/ChatWindow'
import { chatStorage } from '../utils/chatStorage'
import { summarizeChat, getQuickChatTitle } from '../utils/chatSummarizer'

const RAGDOLL_API_URL = import.meta.env.REACT_APP_GOOSE_API_URL || 'http://localhost:8080'

export default function RagdollPage() {
  const { t } = useLanguage()
  const [selectedRole, setSelectedRole] = useState('reference')
  const [selectedProjectId, setSelectedProjectId] = useState(null)
  const [selectedChatId, setSelectedChatId] = useState(null)
  const [question, setQuestion] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedLogRequestId, setSelectedLogRequestId] = useState(null)
  const [logContent, setLogContent] = useState(null)
  const [isLoadingLogs, setIsLoadingLogs] = useState(false)

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  })

  const projectsList = projects?.data || projects || []

  // Загружаем текущий чат
  const currentChat = selectedChatId ? chatStorage.getChat(selectedChatId) : null
  const [messages, setMessages] = useState(currentChat?.messages || [])
  
  // Синхронизируем messages с currentChat
  useEffect(() => {
    if (currentChat) {
      setMessages(currentChat.messages || [])
    } else {
      setMessages([])
    }
  }, [currentChat, selectedChatId])

  // При изменении проекта или роли создаем/переключаем чат
  useEffect(() => {
    // Если проект не выбран, очищаем выбранный чат
    if (!selectedProjectId) {
      setSelectedChatId(null)
      return
    }
    
    // Ищем чат с нужной ролью для проекта
    const projectChats = chatStorage.getProjectChats(selectedProjectId)
    const chatWithRole = projectChats.find(c => c.role === selectedRole)
    
    if (chatWithRole) {
      // Переключаемся на существующий чат с нужной ролью
      setSelectedChatId(chatWithRole.id)
    } else if (projectChats.length > 0) {
      // Если есть чаты, но не с нужной ролью, переключаемся на последний
      setSelectedChatId(projectChats[0].id)
    } else {
      // Создаем новый чат только если нет чатов для проекта
      const project = projectsList.find(p => p.id === selectedProjectId)
      const newChat = chatStorage.createChat(
        selectedProjectId,
        project?.name || null,
        selectedRole
      )
      if (newChat) {
        setSelectedChatId(newChat.id)
      }
    }
  }, [selectedProjectId, selectedRole, projectsList])

  const askRagdoll = async () => {
    if (!question.trim() || !currentChat || !selectedProjectId) return

    const userMessage = {
      role: 'user',
      content: question,
      timestamp: new Date().toISOString()
    }

    const updatedMessages = [...messages, userMessage]
    chatStorage.updateChatMessages(currentChat.id, updatedMessages)
    setMessages(updatedMessages)
    setQuestion('')
    setIsLoading(true)

    try {
      const response = await fetch(`${RAGDOLL_API_URL}/ask`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          project_id: selectedProjectId,
          conversation_history: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          }))
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || 'No answer received',
        timestamp: new Date().toISOString(),
        requestId: data.request_id || null
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      chatStorage.updateChatMessages(currentChat.id, finalMessages)
      setMessages(finalMessages)

      // Если это первое сообщение после создания чата, обновляем название
      if (updatedMessages.length === 1) {
        const quickTitle = getQuickChatTitle(finalMessages, currentChat.projectName, 1)
        chatStorage.updateChatTitle(currentChat.id, quickTitle)
        
        // Асинхронно генерируем полное summarize
        summarizeChat(finalMessages).then(summary => {
          if (summary) {
            chatStorage.updateChatTitle(currentChat.id, summary)
            // Принудительно обновляем компонент
            setSelectedChatId(prev => prev) // триггерим ре-рендер
          }
        })
      }
    } catch (error) {
      console.error('Error asking Ragdoll:', error)
      let errorMsg = error.message
      
      if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMsg = `Не удалось подключиться к Ragdoll сервису на ${RAGDOLL_API_URL}. Убедитесь, что сервис запущен: docker compose up goose`
      } else if (error.message.includes('404')) {
        errorMsg = `Ragdoll сервис не найден. Проверьте, что сервис запущен и доступен на ${RAGDOLL_API_URL}`
      } else if (error.message.includes('500')) {
        errorMsg = `Ошибка сервера Ragdoll. Проверьте логи: docker logs coderag_goose`
      }
      
      const errorMessage = {
        role: 'assistant',
        content: `Ошибка: ${errorMsg}`,
        timestamp: new Date().toISOString(),
        isError: true
      }
      
      const finalMessages = [...updatedMessages, errorMessage]
      chatStorage.updateChatMessages(currentChat.id, finalMessages)
      setMessages(finalMessages)
    } finally {
      setIsLoading(false)
    }
  }

  const handleProjectSelect = (projectId) => {
    setSelectedProjectId(projectId)
  }

  const handleChatSelect = (chatId) => {
    setSelectedChatId(chatId)
    const chat = chatStorage.getChat(chatId)
    if (chat) {
      setSelectedProjectId(chat.projectId)
      setSelectedRole(chat.role)
    }
  }

  const handleCreateNewChat = (projectId, projectName) => {
    const newChat = chatStorage.createChat(projectId, projectName, selectedRole)
    if (newChat) {
      setSelectedProjectId(projectId)
      setSelectedChatId(newChat.id)
    }
  }

  const handleClearChat = () => {
    if (currentChat) {
      chatStorage.clearChatMessages(currentChat.id)
      // Обновляем messages напрямую
      setMessages([])
      // Также обновляем selectedChatId для синхронизации с storage
      const updatedChat = chatStorage.getChat(currentChat.id)
      if (updatedChat) {
        setSelectedChatId(updatedChat.id)
      }
    }
  }

  const fetchLogs = async (requestId) => {
    if (!requestId) return
    
    setIsLoadingLogs(true)
    setSelectedLogRequestId(requestId)
    
    try {
      const response = await fetch(`${RAGDOLL_API_URL}/logs/${requestId}`)
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
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
          <Link to="/" className="hover:text-gray-900">
            {t('home') || 'Home'}
          </Link>
          <ChevronRight className="w-4 h-4" />
          <span className="text-gray-900 font-medium">
            {t('ragdoll') || 'Ragdoll AI Assistant'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            {t('ragdoll') || 'Ragdoll AI Assistant'}
          </h1>
          <RoleSelector 
            selectedRole={selectedRole}
            onRoleChange={setSelectedRole}
          />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <ProjectSidebar
          projects={projectsList}
          selectedProjectId={selectedProjectId}
          selectedChatId={selectedChatId}
          onProjectSelect={handleProjectSelect}
          onChatSelect={handleChatSelect}
          onCreateNewChat={handleCreateNewChat}
        />

        {/* Chat Window */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <ChatWindow
            messages={messages}
            question={question}
            setQuestion={setQuestion}
            isLoading={isLoading}
            projectId={selectedProjectId}
            onSendMessage={askRagdoll}
            onClearChat={handleClearChat}
            onShowLogs={fetchLogs}
          />
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
