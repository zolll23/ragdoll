import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { entitiesApi } from '../services/api'
import { useLanguage } from '../utils/i18n'
import { ChevronLeft, ChevronRight, FileCode } from 'lucide-react'

export default function SimilarCodePage() {
  const { t } = useLanguage()
  const [searchParams, setSearchParams] = useSearchParams()
  const [currentIndex, setCurrentIndex] = useState(0)
  const leftScrollRef = useRef(null)
  const rightScrollRef = useRef(null)
  const isScrollingRef = useRef(false)
  
  const projectId = searchParams.get('project_id') ? parseInt(searchParams.get('project_id')) : null
  const entityType = searchParams.get('entity_type') || null
  const minSimilarity = parseFloat(searchParams.get('min_similarity') || '0.7')
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['similarCode', projectId, entityType, minSimilarity],
    queryFn: () => entitiesApi.searchSimilar({
      project_id: projectId,
      entity_type: entityType,
      min_similarity: minSimilarity,
      limit: 100
    })
  })
  
  const pairs = data?.data?.pairs || data?.pairs || []
  const currentPair = pairs[currentIndex]
  
  useEffect(() => {
    // Reset to first pair when data changes
    setCurrentIndex(0)
  }, [data])
  
  // Synchronize scrolling between left and right panels
  useEffect(() => {
    const leftPanel = leftScrollRef.current
    const rightPanel = rightScrollRef.current
    
    if (!leftPanel || !rightPanel) return
    
    const handleLeftScroll = () => {
      if (isScrollingRef.current) return
      isScrollingRef.current = true
      rightPanel.scrollTop = leftPanel.scrollTop
      requestAnimationFrame(() => {
        isScrollingRef.current = false
      })
    }
    
    const handleRightScroll = () => {
      if (isScrollingRef.current) return
      isScrollingRef.current = true
      leftPanel.scrollTop = rightPanel.scrollTop
      requestAnimationFrame(() => {
        isScrollingRef.current = false
      })
    }
    
    leftPanel.addEventListener('scroll', handleLeftScroll)
    rightPanel.addEventListener('scroll', handleRightScroll)
    
    return () => {
      leftPanel.removeEventListener('scroll', handleLeftScroll)
      rightPanel.removeEventListener('scroll', handleRightScroll)
    }
  }, [currentPair])
  
  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }
  
  const handleNext = () => {
    if (currentIndex < pairs.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg">{t('loading')}</div>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">{t('error')}: {error.message}</div>
      </div>
    )
  }
  
  if (!currentPair) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg">{t('noSimilarCodeFound') || 'No similar code found'}</div>
      </div>
    )
  }
  
  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">{t('similarCodeSearch') || 'Similar Code Search'}</h1>
          <div className="text-sm text-gray-600">
            {t('pair')} {currentIndex + 1} {t('of')} {pairs.length}
          </div>
        </div>
      </div>
      
      {/* Diff View */}
      <div className="flex-1 flex overflow-auto min-h-0 justify-center bg-gray-100">
        <div className="flex gap-4 max-w-[1600px] w-full px-4 py-4">
          {/* Left Code */}
          <div className="flex-1 flex flex-col border border-gray-300 bg-white min-w-0 max-w-[800px] shadow-sm">
            <div className="bg-gray-100 px-4 py-2 border-b flex items-center gap-2 flex-shrink-0">
              <FileCode className="w-4 h-4 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{currentPair.left.entity.name}</div>
                <div className="text-xs text-gray-600 truncate">{currentPair.left.entity.file_path}</div>
              </div>
              <div className="text-xs text-gray-500 flex-shrink-0 whitespace-nowrap">
                {currentPair.left.entity.type} • Lines {currentPair.left.entity.start_line}-{currentPair.left.entity.end_line}
              </div>
            </div>
            <div 
              ref={leftScrollRef}
              className="flex-1 overflow-auto min-h-0"
              style={{ scrollbarWidth: 'thin' }}
            >
              <CodeViewer code={currentPair.left.entity.code} language="php" />
            </div>
          </div>
          
          {/* Right Code */}
          <div className="flex-1 flex flex-col border border-gray-300 bg-white min-w-0 max-w-[800px] shadow-sm">
            <div className="bg-gray-100 px-4 py-2 border-b flex items-center gap-2 flex-shrink-0">
              <FileCode className="w-4 h-4 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{currentPair.right.entity.name}</div>
                <div className="text-xs text-gray-600 truncate">{currentPair.right.entity.file_path}</div>
              </div>
              <div className="text-xs text-gray-500 flex-shrink-0 whitespace-nowrap">
                {currentPair.right.entity.type} • Lines {currentPair.right.entity.start_line}-{currentPair.right.entity.end_line}
              </div>
            </div>
            <div 
              ref={rightScrollRef}
              className="flex-1 overflow-auto min-h-0"
              style={{ scrollbarWidth: 'thin' }}
            >
              <CodeViewer code={currentPair.right.entity.code} language="php" />
            </div>
          </div>
        </div>
      </div>
      
      {/* Footer with Navigation */}
      <div className="bg-white border-t px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="text-sm">
            <span className="font-medium">{t('similarity')}:</span>{' '}
            <span className="text-blue-600">{(currentPair.similarity * 100).toFixed(1)}%</span>
          </div>
          {currentPair.left.analysis && (
            <div className="text-sm text-gray-600">
              {t('complexity')}: {currentPair.left.analysis.complexity}
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevious}
            disabled={currentIndex === 0}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed rounded flex items-center gap-2"
          >
            <ChevronLeft className="w-4 h-4" />
            {t('previous') || 'Previous'}
          </button>
          <button
            onClick={handleNext}
            disabled={currentIndex >= pairs.length - 1}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed rounded flex items-center gap-2"
          >
            {t('next') || 'Next'}
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

function CodeViewer({ code, language }) {
  // Simple syntax highlighting for PHP
  const highlightCode = (codeLine) => {
    if (!codeLine) return '&nbsp;'
    
    // Escape HTML first to prevent injection
    let escaped = codeLine
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    
    // Match patterns in order of priority (most specific first)
    const patterns = [
      // Comments (highest priority - don't highlight anything inside)
      { regex: /(\/\/.*$|\/\*[\s\S]*?\*\/)/gm, class: 'text-gray-500' },
      // Strings (high priority - don't highlight inside strings)
      { regex: /(['"])((?:\\.|(?!\1)[^\\])*?)(\1)/g, class: 'text-green-600', fullMatch: true },
      // Class names with ::class
      { regex: /\b([A-Z][a-zA-Z0-9_]*::class)\b/g, class: 'text-indigo-600' },
      // Variables
      { regex: /(\$[a-zA-Z_][a-zA-Z0-9_]*)/g, class: 'text-blue-600' },
      // Numbers
      { regex: /\b(\d+)\b/g, class: 'text-orange-600' },
      // Keywords (lowest priority)
      { regex: /\b(public|private|protected|function|class|return|if|else|foreach|for|while|use|namespace|extends|implements)\b/g, class: 'text-purple-600 font-semibold' },
    ]
    
    // Collect all matches with their positions
    const matches = []
    patterns.forEach(({ regex, class: className, fullMatch }) => {
      let match
      const regexCopy = new RegExp(regex.source, regex.flags)
      while ((match = regexCopy.exec(escaped)) !== null) {
        const start = match.index
        const end = start + match[0].length
        const text = fullMatch ? match[0] : (match[1] || match[0])
        
        // Check if this match overlaps with any existing match
        const overlaps = matches.some(m => 
          (start >= m.start && start < m.end) || 
          (end > m.start && end <= m.end) ||
          (start <= m.start && end >= m.end)
        )
        
        if (!overlaps) {
          matches.push({ start, end, text, className })
        }
      }
    })
    
    // Sort matches by start position
    matches.sort((a, b) => a.start - b.start)
    
    // Build highlighted string
    let result = ''
    let currentIndex = 0
    
    matches.forEach(match => {
      // Add text before match
      if (currentIndex < match.start) {
        result += escaped.substring(currentIndex, match.start)
      }
      // Add highlighted match
      result += `<span class="${match.className}">${match.text}</span>`
      currentIndex = match.end
    })
    
    // Add remaining text
    if (currentIndex < escaped.length) {
      result += escaped.substring(currentIndex)
    }
    
    return result || '&nbsp;'
  }
  
  const lines = code.split('\n')
  
  // Limit code width to ~100-110 characters (PSR2/PEP8 compliant)
  // At 14px monospace font, ~8px per character = ~800-900px
  const codeMaxWidth = '800px'
  
  return (
    <div className="font-mono text-sm">
      <table className="border-collapse" style={{ width: '100%', tableLayout: 'fixed' }}>
        <colgroup>
          <col style={{ width: '50px' }} />
          <col style={{ width: codeMaxWidth }} />
        </colgroup>
        <tbody>
          {lines.map((line, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-3 py-0.5 text-right text-gray-400 select-none border-r border-gray-200 bg-gray-50 sticky left-0 z-10">
                {index + 1}
              </td>
              <td className="px-3 py-0.5 whitespace-pre font-mono text-sm" style={{ maxWidth: codeMaxWidth }} dangerouslySetInnerHTML={{ __html: highlightCode(line) || '&nbsp;' }} />
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

