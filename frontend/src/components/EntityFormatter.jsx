import React, { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { entitiesApi } from '../services/api'
import EntityModal from './EntityModal'

/**
 * EntityFormatter - форматирует текст ответа агента, делая упоминания сущностей кликабельными
 * 
 * Паттерны для поиска:
 * - `methodName` - методы
 * - `ClassName` - классы (с заглавной буквы)
 * - `CONSTANT_NAME` - константы (все заглавные с подчеркиваниями)
 * - `EnumName::CaseName` - enum cases
 * - `ClassName::CONSTANT` - константы классов
 * - `ClassName::methodName()` - методы классов
 */
export default function EntityFormatter({ 
  text, 
  projectId,
  className = "" 
}) {
  const [selectedEntityId, setSelectedEntityId] = useState(null)
  const [entityCache, setEntityCache] = useState({}) // Кэш для найденных сущностей

  // Проверка на общие слова, которые не являются сущностями
  const isCommonWord = (word) => {
    const commonWords = [
      'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use',
      'это', 'что', 'как', 'для', 'или', 'был', 'была', 'было', 'были', 'есть', 'быть', 'был', 'была', 'было', 'были', 'есть', 'быть'
    ]
    return commonWords.includes(word.toLowerCase())
  }

  // Регулярные выражения для поиска упоминаний сущностей
  const entityPatterns = useMemo(() => [
    // Enum cases: EnumName::CaseName (приоритет 1 - самый специфичный)
    {
      pattern: /\b([A-Z][a-zA-Z0-9_]*::[A-Z][a-zA-Z0-9_]*)\b/g,
      type: 'enum_case',
      priority: 1
    },
    // Class constants: ClassName::CONSTANT_NAME
    {
      pattern: /\b([A-Z][a-zA-Z0-9_]*::[A-Z][A-Z0-9_]+)\b/g,
      type: 'constant',
      priority: 2
    },
    // Class methods: ClassName::methodName()
    {
      pattern: /\b([A-Z][a-zA-Z0-9_]*::[a-z][a-zA-Z0-9_]*)\s*\(/g,
      type: 'method',
      priority: 2
    },
    // Methods in backticks: `methodName` или `MethodName` (самый распространенный формат в ответах агента)
    {
      pattern: /`([a-zA-Z][a-zA-Z0-9_]*)`/g,
      type: 'method',
      priority: 3
    },
    // Methods: methodName() (с маленькой буквы, заканчивается на скобку)
    {
      pattern: /\b([a-z][a-zA-Z0-9_]*)\s*\(/g,
      type: 'method',
      priority: 4
    },
    // Methods without brackets: methodName (с маленькой буквы, после слова "method" или "метод")
    {
      pattern: /(?:method|метод|функция|function)\s+([a-z][a-zA-Z0-9_]{3,})\b/gi,
      type: 'method',
      priority: 4
    },
    // Constants: CONSTANT_NAME (все заглавные с подчеркиваниями, минимум 3 символа)
    {
      pattern: /\b([A-Z][A-Z0-9_]{2,})\b/g,
      type: 'constant',
      priority: 5
    },
    // Classes: ClassName (с заглавной буквы, минимум 3 символа, не в начале предложения)
    {
      pattern: /(?:^|[^a-zA-Z])([A-Z][a-zA-Z0-9_]{2,})\b/g,
      type: 'class',
      priority: 6
    },
  ], [])

  // Функция для поиска сущности по имени
  const findEntity = async (entityName, type) => {
    // Проверяем кэш
    const cacheKey = `${entityName}_${type}`
    if (entityCache[cacheKey]) {
      return entityCache[cacheKey]
    }

    if (!projectId) return null

    try {
      // Ищем сущность по имени в рамках проекта
      const response = await entitiesApi.list({
        project_id: projectId,
        name: entityName,
        entity_type: type !== 'enum_case' ? type : undefined
      })

      const entities = response.data?.data || response.data || []
      
      if (entities.length === 0) return null
      
      // Для enum cases ищем точное совпадение по full_qualified_name
      if (type === 'enum_case' && entityName.includes('::')) {
        const found = entities.find(e => 
          e.full_qualified_name === entityName || 
          e.full_qualified_name?.endsWith(`::${entityName.split('::')[1]}`)
        )
        if (found) {
          setEntityCache(prev => ({ ...prev, [cacheKey]: found.id }))
          return found.id
        }
      }
      
      // Для остальных типов ищем точное совпадение по имени или full_qualified_name
      let found = entities.find(e => 
        e.name === entityName || 
        e.full_qualified_name === entityName ||
        e.full_qualified_name?.endsWith(`::${entityName}`)
      )
      
      // Если точного совпадения нет, берем первое
      if (!found && entities.length > 0) {
        found = entities[0]
      }
      
      if (found) {
        setEntityCache(prev => ({ ...prev, [cacheKey]: found.id }))
        return found.id
      }
    } catch (error) {
      console.error('Error finding entity:', error)
    }

    return null
  }

  // Форматируем текст, заменяя упоминания сущностей на кликабельные ссылки
  const formatText = useMemo(() => {
    if (!text) return []

    const parts = []
    let lastIndex = 0
    const matches = []

    // Собираем все совпадения
    entityPatterns.forEach(({ pattern, type, priority }) => {
      const regex = new RegExp(pattern.source, pattern.flags)
      let match
      while ((match = regex.exec(text)) !== null) {
        const entityName = match[1]
        // Исключаем слишком короткие имена и общие слова
        if (entityName.length < 3 || isCommonWord(entityName)) {
          continue
        }
        // Для классов проверяем, что это не начало предложения
        if (type === 'class' && match.index > 0) {
          const prevChar = text[match.index - 1]
          if (/[a-zA-Z]/.test(prevChar)) {
            continue // Это часть другого слова
          }
        }
        matches.push({
          start: match.index + (match[0].indexOf(match[1])),
          end: match.index + (match[0].indexOf(match[1])) + entityName.length,
          entityName,
          type,
          priority: priority || 10,
          fullMatch: match[0]
        })
      }
    })

    // Сортируем по приоритету (меньше = выше приоритет), затем по позиции
    matches.sort((a, b) => {
      if (a.priority !== b.priority) {
        return a.priority - b.priority
      }
      return a.start - b.start
    })
    
    // Удаляем перекрывающиеся, оставляя более специфичные (с меньшим приоритетом)
    const filteredMatches = []
    for (const match of matches) {
      const overlaps = filteredMatches.some(m => 
        (match.start >= m.start && match.start < m.end) ||
        (match.end > m.start && match.end <= m.end) ||
        (match.start <= m.start && match.end >= m.end)
      )
      if (!overlaps) {
        filteredMatches.push(match)
      }
    }
    
    // Сортируем по позиции для правильного отображения
    filteredMatches.sort((a, b) => a.start - b.start)

    // Строим массив частей текста
    filteredMatches.forEach((match) => {
      // Добавляем текст до совпадения
      if (match.start > lastIndex) {
        parts.push({
          type: 'text',
          content: text.substring(lastIndex, match.start)
        })
      }

      // Добавляем кликабельную ссылку
      // Для методов в backticks сохраняем оригинальный формат с backticks
      let displayContent = match.entityName
      if (match.fullMatch.startsWith('`') && match.fullMatch.endsWith('`')) {
        displayContent = `\`${match.entityName}\``
      }
      
      parts.push({
        type: 'entity',
        entityName: match.entityName,
        entityType: match.type,
        content: displayContent
      })

      lastIndex = match.end
    })

    // Добавляем оставшийся текст
    if (lastIndex < text.length) {
      parts.push({
        type: 'text',
        content: text.substring(lastIndex)
      })
    }

    return parts.length > 0 ? parts : [{ type: 'text', content: text }]
  }, [text, entityPatterns, isCommonWord])

  const handleEntityClick = async (entityName, entityType) => {
    const entityId = await findEntity(entityName, entityType)
    if (entityId) {
      setSelectedEntityId(entityId)
    }
  }

  return (
    <>
      <span className={className}>
        {formatText.map((part, index) => {
          if (part.type === 'text') {
            // Сохраняем переносы строк в тексте
            const lines = part.content.split('\n')
            return (
              <React.Fragment key={index}>
                {lines.map((line, lineIndex) => (
                  <React.Fragment key={lineIndex}>
                    {line}
                    {lineIndex < lines.length - 1 && <br />}
                  </React.Fragment>
                ))}
              </React.Fragment>
            )
          } else {
            return (
              <button
                key={index}
                onClick={() => handleEntityClick(part.entityName, part.entityType)}
                className="text-blue-600 hover:text-blue-800 hover:underline font-medium cursor-pointer transition-colors"
                title={`Показать детали: ${part.entityName}`}
              >
                {part.content}
              </button>
            )
          }
        })}
      </span>

      {selectedEntityId && (
        <EntityModal
          entityId={selectedEntityId}
          onClose={() => setSelectedEntityId(null)}
        />
      )}
    </>
  )
}
