package com.coderag.ide.ui

import com.coderag.ide.client.EntityResponse
import com.coderag.ide.client.RefactoringResponse
import com.coderag.ide.client.SearchResult
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowManager
import javax.swing.JComponent
import javax.swing.JPanel
import javax.swing.JTextArea

/**
 * CodeRAG tool window for displaying analysis results
 */
object CodeRAGToolWindow {
    private val toolWindows = mutableMapOf<Project, ToolWindow>()
    
    fun create(project: Project, toolWindow: ToolWindow) {
        toolWindows[project] = toolWindow
        val content = toolWindow.contentManager.factory.createContent(
            createContentPanel(),
            "",
            false
        )
        toolWindow.contentManager.addContent(content)
    }
    
    fun show(project: Project, entity: EntityResponse) {
        val toolWindow = toolWindows[project] 
            ?: ToolWindowManager.getInstance(project).getToolWindow("CodeRAG")
        
        toolWindow?.show()
        // Update content with entity analysis
    }
    
    fun showSearchResults(project: Project, results: List<SearchResult>) {
        val toolWindow = toolWindows[project]
            ?: ToolWindowManager.getInstance(project).getToolWindow("CodeRAG")
        
        toolWindow?.show()
        // Update content with search results
    }
    
    fun showRefactoringSuggestions(project: Project, suggestions: RefactoringResponse) {
        val toolWindow = toolWindows[project]
            ?: ToolWindowManager.getInstance(project).getToolWindow("CodeRAG")
        
        toolWindow?.show()
        // Update content with refactoring suggestions
    }
    
    private fun createContentPanel(): JComponent {
        val panel = JPanel()
        val textArea = JTextArea("CodeRAG Analysis Results\n\nSelect code and use 'Analyze with CodeRAG' action")
        textArea.isEditable = false
        panel.add(textArea)
        return panel
    }
}



