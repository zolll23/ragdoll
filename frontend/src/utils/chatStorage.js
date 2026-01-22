/**
 * Утилиты для работы с историей чатов в localStorage
 */

const STORAGE_KEY = 'ragdoll_chats'

/**
 * Структура чата:
 * {
 *   id: string, // уникальный ID чата
 *   projectId: number | null,
 *   projectName: string,
 *   role: string, // 'reference', 'code-review', 'refactoring'
 *   title: string, // название чата
 *   messages: Array<{role, content, timestamp, requestId}>,
 *   createdAt: string,
 *   updatedAt: string
 * }
 */

export const chatStorage = {
  /**
   * Получить все чаты
   */
  getAllChats() {
    try {
      const data = localStorage.getItem(STORAGE_KEY)
      return data ? JSON.parse(data) : {}
    } catch (error) {
      console.error('Error reading chats from storage:', error)
      return {}
    }
  },

  /**
   * Получить чаты для проекта
   */
  getProjectChats(projectId) {
    const allChats = this.getAllChats()
    return Object.values(allChats).filter(
      chat => chat.projectId === projectId
    ).sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
  },

  /**
   * Получить чат по ID
   */
  getChat(chatId) {
    const allChats = this.getAllChats()
    return allChats[chatId] || null
  },

  /**
   * Сохранить чат
   */
  saveChat(chat) {
    try {
      const allChats = this.getAllChats()
      allChats[chat.id] = {
        ...chat,
        updatedAt: new Date().toISOString()
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(allChats))
      return chat
    } catch (error) {
      console.error('Error saving chat to storage:', error)
      return null
    }
  },

  /**
   * Создать новый чат
   */
  createChat(projectId, projectName, role = 'reference') {
    const chatId = `${projectId || 'all'}_${role}_${Date.now()}`
    const chat = {
      id: chatId,
      projectId,
      projectName: projectName || 'Все проекты',
      role,
      title: projectName ? `${projectName} (1)` : 'Новый чат (1)',
      messages: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
    return this.saveChat(chat)
  },

  /**
   * Обновить сообщения в чате
   */
  updateChatMessages(chatId, messages) {
    const chat = this.getChat(chatId)
    if (!chat) return null
    
    chat.messages = messages
    return this.saveChat(chat)
  },

  /**
   * Обновить название чата
   */
  updateChatTitle(chatId, title) {
    const chat = this.getChat(chatId)
    if (!chat) return null
    
    chat.title = title
    return this.saveChat(chat)
  },

  /**
   * Удалить чат
   */
  deleteChat(chatId) {
    try {
      const allChats = this.getAllChats()
      delete allChats[chatId]
      localStorage.setItem(STORAGE_KEY, JSON.stringify(allChats))
      return true
    } catch (error) {
      console.error('Error deleting chat:', error)
      return false
    }
  },

  /**
   * Очистить все сообщения в чате
   */
  clearChatMessages(chatId) {
    const chat = this.getChat(chatId)
    if (!chat) return null
    
    chat.messages = []
    // Восстанавливаем исходное название
    const existingChats = this.getProjectChats(chat.projectId)
    const chatIndex = existingChats.findIndex(c => c.id === chatId)
    const chatNumber = chatIndex >= 0 ? chatIndex + 1 : existingChats.length + 1
    chat.title = chat.projectName ? `${chat.projectName} (${chatNumber})` : `Новый чат (${chatNumber})`
    return this.saveChat(chat)
  }
}
