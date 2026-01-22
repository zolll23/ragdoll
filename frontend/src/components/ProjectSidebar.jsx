import React, { useState } from 'react'
import { FolderOpen, Plus, MoreVertical, Trash2, MessageSquare } from 'lucide-react'
import { chatStorage } from '../utils/chatStorage'

export default function ProjectSidebar({ 
  projects, 
  selectedProjectId, 
  selectedChatId,
  onProjectSelect,
  onChatSelect,
  onCreateNewChat
}) {
  const [contextMenu, setContextMenu] = useState({ projectId: null, x: 0, y: 0 })

  const handleProjectRightClick = (e, projectId) => {
    e.preventDefault()
    e.stopPropagation()
    setContextMenu({
      projectId,
      x: e.clientX,
      y: e.clientY
    })
  }

  const handleCreateNewChat = (projectId) => {
    const project = projects.find(p => p.id === projectId)
    onCreateNewChat(projectId, project?.name || 'Проект')
    setContextMenu({ projectId: null, x: 0, y: 0 })
  }

  const handleCloseContextMenu = () => {
    setContextMenu({ projectId: null, x: 0, y: 0 })
  }

  // Получаем чаты для каждого проекта
  const getProjectChats = (projectId) => {
    return chatStorage.getProjectChats(projectId)
  }

  return (
    <>
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col h-full min-h-0 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex-shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">Проекты</h2>
        </div>

        {/* Projects List */}
        <div className="flex-1 overflow-y-auto min-h-0" style={{ height: 0 }}>
          {/* Projects */}
          {(projects || []).map((project) => {
            const projectChats = getProjectChats(project.id)
            const isSelected = selectedProjectId === project.id
            
            return (
              <div key={project.id} className="flex flex-col min-h-0">
                <div
                  className={`px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors flex-shrink-0 ${
                    isSelected ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                  }`}
                  onClick={() => onProjectSelect(project.id)}
                  onContextMenu={(e) => handleProjectRightClick(e, project.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1">
                      <FolderOpen className="w-5 h-5 text-gray-600" />
                      <span className="font-medium text-gray-900 truncate">{project.name}</span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCreateNewChat(project.id)
                      }}
                      className="p-1 hover:bg-gray-200 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                      title="Новый чат"
                    >
                      <Plus className="w-4 h-4 text-gray-600" />
                    </button>
                  </div>
                </div>
                  
                {/* Chat sub-items - отдельный прокручиваемый контейнер */}
                {isSelected && projectChats.length > 0 && (
                  <div className="overflow-y-auto max-h-40 min-h-0 px-4 pb-2">
                    <div className="space-y-1">
                      {projectChats.map((chat) => (
                        <div
                          key={chat.id}
                          onClick={(e) => {
                            e.stopPropagation()
                            onChatSelect(chat.id)
                          }}
                          className={`px-3 py-1.5 rounded text-sm cursor-pointer flex items-center gap-2 ${
                            selectedChatId === chat.id
                              ? 'bg-blue-100 text-blue-900'
                              : 'text-gray-700 hover:bg-gray-100'
                          }`}
                        >
                          <MessageSquare className="w-4 h-4 flex-shrink-0" />
                          <span className="truncate flex-1">{chat.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu.projectId !== null && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={handleCloseContextMenu}
          />
          <div
            className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1"
            style={{
              left: `${contextMenu.x}px`,
              top: `${contextMenu.y}px`
            }}
          >
            <button
              onClick={() => {
                handleCreateNewChat(contextMenu.projectId)
              }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Новый чат
            </button>
          </div>
        </>
      )}
    </>
  )
}
