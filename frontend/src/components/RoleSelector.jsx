import React from 'react'
import { HelpCircle, Code2, RefreshCw } from 'lucide-react'

const ROLES = [
  {
    id: 'reference',
    name: 'Справочная',
    description: 'Ответы на вопросы о коде, поиск сущностей, анализ',
    icon: HelpCircle,
    color: 'blue'
  },
  {
    id: 'code-review',
    name: 'Код-ревью',
    description: 'Анализ кода на ошибки, проблемы, улучшения',
    icon: Code2,
    color: 'green',
    comingSoon: true
  },
  {
    id: 'refactoring',
    name: 'Рефакторинг',
    description: 'Предложения по улучшению структуры кода',
    icon: RefreshCw,
    color: 'purple',
    comingSoon: true
  }
]

export default function RoleSelector({ selectedRole, onRoleChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-gray-700 whitespace-nowrap">Роль:</span>
      <div className="flex gap-2">
        {ROLES.map((role) => {
          const Icon = role.icon
          const isSelected = selectedRole === role.id
          const isDisabled = role.comingSoon
          
          return (
            <button
              key={role.id}
              onClick={() => !isDisabled && onRoleChange(role.id)}
              disabled={isDisabled}
              className={`
                flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border transition-all text-sm
                ${isSelected 
                  ? `border-${role.color}-500 bg-${role.color}-50` 
                  : 'border-gray-200 hover:border-gray-300'
                }
                ${isDisabled 
                  ? 'opacity-50 cursor-not-allowed' 
                  : 'cursor-pointer hover:bg-gray-50'
                }
              `}
              title={role.comingSoon ? 'Скоро будет доступно' : role.description}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${isSelected ? `text-${role.color}-600` : 'text-gray-600'}`} />
              <span className={`font-medium whitespace-nowrap ${isSelected ? `text-${role.color}-900` : 'text-gray-900'}`}>
                {role.name}
              </span>
              {role.comingSoon && (
                <span className="text-xs text-gray-500">(скоро)</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
