import React, { useEffect, useRef } from 'react'
import { Send, Loader, Info, Trash2 } from 'lucide-react'
import EntityFormatter from './EntityFormatter'

// Ragdoll cat logo - using photo
import ragdollPhoto from '../assets/ragdoll-cat.jpg'

const RagdollLogoComponent = ({ className = "w-8 h-8" }) => (
  <img 
    src={ragdollPhoto} 
    alt="Ragdoll cat" 
    className={`${className} rounded-full object-cover`}
    style={{ objectPosition: 'center top' }}
  />
)

export default function ChatWindow({
  messages,
  question,
  setQuestion,
  isLoading,
  projectId,
  onSendMessage,
  onClearChat,
  onShowLogs
}) {
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)
  const previousMessagesLengthRef = useRef(0)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const checkIfAtBottom = () => {
    const container = messagesContainerRef.current
    if (!container) return true
    
    // Проверяем, находится ли пользователь внизу (с допуском 100px)
    const threshold = 100
    const isAtBottom = 
      container.scrollHeight - container.scrollTop - container.clientHeight < threshold
    
    return isAtBottom
  }

  const handleScroll = () => {
    // Обновляем флаг, находится ли пользователь внизу
    shouldAutoScrollRef.current = checkIfAtBottom()
  }

  useEffect(() => {
    const currentMessagesLength = messages.length
    const previousMessagesLength = previousMessagesLengthRef.current
    
    // Определяем, было ли добавлено новое сообщение
    const isNewMessage = currentMessagesLength > previousMessagesLength
    
    // Прокручиваем вниз если:
    // 1. Пользователь был внизу (shouldAutoScrollRef.current === true)
    // 2. Или идет загрузка (isLoading === true) - когда приходит ответ
    // 3. Или было добавлено новое сообщение и пользователь был внизу
    if (shouldAutoScrollRef.current && (isLoading || isNewMessage)) {
      scrollToBottom()
    }
    
    // Обновляем флаг после прокрутки
    if (!isLoading) {
      shouldAutoScrollRef.current = checkIfAtBottom()
    }
    
    // Сохраняем текущую длину для следующего сравнения
    previousMessagesLengthRef.current = currentMessagesLength
  }, [messages, isLoading])

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSendMessage()
    }
  }

  return (
    <div className="flex-1 flex flex-col bg-white min-h-0">
      {/* Chat Header */}
      <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between bg-white flex-shrink-0">
        <div className="flex items-center gap-3">
          <RagdollLogoComponent className="w-8 h-8" />
          <div>
            <h3 className="font-semibold text-gray-900">Ragdoll</h3>
            <p className="text-xs text-gray-500">AI Assistant</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={onClearChat}
            className="px-4 py-2 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 border border-red-200 rounded-lg transition-colors flex items-center gap-2 shadow-sm"
            title="Очистить историю чата"
          >
            <Trash2 className="w-4 h-4" />
            Очистить чат
          </button>
        )}
      </div>

      {/* Messages */}
      <div 
        ref={messagesContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0"
      >
        {!projectId ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <div className="mb-4">
              <RagdollLogoComponent className="w-20 h-20 mx-auto" />
            </div>
            <h3 className="text-lg font-medium mb-2 text-gray-900">
              Выберите проект для начала беседы
            </h3>
            <p className="text-sm text-gray-600 max-w-md">
              Пожалуйста, выберите проект из списка слева, чтобы начать задавать вопросы о коде.
            </p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <div className="mb-4">
              <RagdollLogoComponent className="w-20 h-20 mx-auto" />
            </div>
            <h3 className="text-lg font-medium mb-2">
              Начните беседу с Ragdoll
            </h3>
            <p className="text-sm mb-4">Попробуйте задать вопрос:</p>
            <div className="space-y-2 text-sm max-w-md">
              <div 
                className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => setQuestion('Какие статусы отправки письма есть?')}
              >
                "Какие статусы отправки письма есть?"
              </div>
              <div 
                className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => setQuestion('Какой таймаут используется для отправки писем?')}
              >
                "Какой таймаут используется для отправки писем?"
              </div>
              <div 
                className="bg-gray-50 px-4 py-2 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => setQuestion('Найди методы с высокой сложностью')}
              >
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
                    <RagdollLogoComponent className="w-5 h-5 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <div className="font-medium">
                        {message.role === 'user' ? 'Вы' : 'Ragdoll'}
                      </div>
                      {message.role === 'assistant' && message.requestId && (
                        <button
                          onClick={() => onShowLogs(message.requestId)}
                          className="text-gray-400 hover:text-gray-600 cursor-pointer transition-colors"
                          title="Показать логи обработки запроса"
                          type="button"
                        >
                          <Info className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                    <div className="whitespace-pre-wrap break-words">
                      {message.role === 'assistant' ? (
                        <EntityFormatter 
                          text={message.content} 
                          projectId={projectId}
                        />
                      ) : (
                        message.content
                      )}
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
                <span className="text-gray-600">Думаю...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 flex-shrink-0">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={projectId ? "Задайте вопрос о коде..." : "Выберите проект для начала беседы"}
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={3}
              disabled={isLoading || !projectId}
            />
            <div className="absolute bottom-3 right-3 text-xs text-gray-400">
              Enter для отправки, Shift+Enter для новой строки
            </div>
          </div>
          <button
            onClick={onSendMessage}
            disabled={!question.trim() || isLoading || !projectId}
            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 transition"
          >
            <Send className="w-5 h-5" />
            <span>Отправить</span>
          </button>
        </div>
      </div>
    </div>
  )
}
