import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Search, FolderOpen, Home, Globe, Settings, MessageSquare } from 'lucide-react'
import i18n from '../utils/i18n'

// Ragdoll cat logo - using photo
import ragdollPhoto from '../assets/ragdoll-cat.jpg'

const RagdollLogo = ({ className = "w-5 h-5" }) => (
  <img 
    src={ragdollPhoto} 
    alt="Ragdoll cat" 
    className={`${className} rounded-full object-cover`}
    style={{ objectPosition: 'center top' }}
  />
)

export default function Layout({ children }) {
  const location = useLocation()
  const [language, setLanguage] = useState(i18n.getLanguage())
  
  const isActive = (path) => location.pathname === path
  
  useEffect(() => {
    i18n.setLanguage(language)
    // Force re-render by updating state
    window.dispatchEvent(new Event('languagechange'))
  }, [language])
  
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <nav className="bg-white shadow-sm border-b flex-shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link to="/" className="flex items-center px-2 py-2 text-xl font-bold text-gray-900">
                CodeRAG
              </Link>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                <Link
                  to="/"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/') 
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Home className="w-4 h-4 mr-1" />
                  {i18n.t('home')}
                </Link>
                <Link
                  to="/search"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/search') 
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Search className="w-4 h-4 mr-1" />
                  {i18n.t('search')}
                </Link>
                <Link
                  to="/projects"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/projects') 
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <FolderOpen className="w-4 h-4 mr-1" />
                  {i18n.t('projects')}
                </Link>
                <Link
                  to="/ragdoll"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/ragdoll') || isActive('/goose')
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <RagdollLogo className="w-4 h-4 mr-1" />
                  {i18n.t('ragdoll') || 'Ragdoll'}
                </Link>
                <Link
                  to="/providers"
                  className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                    isActive('/providers') 
                      ? 'border-blue-500 text-gray-900' 
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Settings className="w-4 h-4 mr-1" />
                  {i18n.t('providers')}
                </Link>
              </div>
            </div>
            <div className="flex items-center">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-gray-500" />
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="text-sm border border-gray-300 rounded px-2 py-1 focus:ring-2 focus:ring-blue-500"
                >
                  <option value="EN">EN</option>
                  <option value="RU">RU</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </nav>
      
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
