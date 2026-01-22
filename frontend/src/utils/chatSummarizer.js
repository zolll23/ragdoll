/**
 * Утилита для генерации названий чатов на основе истории беседы
 */

const RAGDOLL_API_URL = import.meta.env.REACT_APP_GOOSE_API_URL || 'http://localhost:8080'

/**
 * Генерирует краткое название чата (1-2 предложения) на основе истории
 */
export async function summarizeChat(messages) {
  if (!messages || messages.length === 0) {
    return null
  }

  // Если только одно сообщение пользователя, используем его как название
  if (messages.length === 1 && messages[0].role === 'user') {
    const question = messages[0].content
    return question.length > 60 ? question.substring(0, 60) + '...' : question
  }

  // Если есть ответ ассистента, генерируем summarize
  try {
    const response = await fetch(`${RAGDOLL_API_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: `Суммаризируй эту беседу в одно-два коротких предложения (максимум 80 символов). Беседа:\n${messages.map(m => `${m.role === 'user' ? 'Пользователь' : 'Ассистент'}: ${m.content}`).join('\n')}`,
        project_id: null,
        conversation_history: []
      })
    })

    if (response.ok) {
      const data = await response.json()
      const summary = data.answer || ''
      // Ограничиваем длину
      return summary.length > 80 ? summary.substring(0, 80) + '...' : summary
    }
  } catch (error) {
    console.error('Error summarizing chat:', error)
  }

  // Fallback: используем первый вопрос пользователя
  const firstUserMessage = messages.find(m => m.role === 'user')
  if (firstUserMessage) {
    const question = firstUserMessage.content
    return question.length > 60 ? question.substring(0, 60) + '...' : question
  }

  return 'Новый чат'
}

/**
 * Простая версия summarize без запроса к API (для быстрого отображения)
 */
export function getQuickChatTitle(messages, projectName, chatNumber) {
  if (!messages || messages.length === 0) {
    return projectName ? `${projectName} (${chatNumber})` : `Новый чат (${chatNumber})`
  }

  const firstUserMessage = messages.find(m => m.role === 'user')
  if (firstUserMessage) {
    const question = firstUserMessage.content
    const shortQuestion = question.length > 50 ? question.substring(0, 50) + '...' : question
    return shortQuestion
  }

  return projectName ? `${projectName} (${chatNumber})` : `Новый чат (${chatNumber})`
}
