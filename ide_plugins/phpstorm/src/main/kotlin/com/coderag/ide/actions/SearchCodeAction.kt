package com.coderag.ide.actions

import com.coderag.ide.services.CodeRAGProjectService
import com.coderag.ide.services.CodeRAGService
import com.coderag.ide.ui.CodeRAGToolWindow
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import javax.swing.JComponent
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextField

/**
 * Action to search code using natural language
 */
class SearchCodeAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        
        val dialog = SearchCodeDialog(project)
        if (dialog.showAndGet()) {
            val query = dialog.getQuery()
            val projectId = dialog.getProjectId()
            
            if (query.isNotBlank() && projectId != null) {
                performSearch(project, projectId, query)
            }
        }
    }
    
    private fun performSearch(project: Project, projectId: Int, query: String) {
        val service = CodeRAGService.getInstance()
        val client = service.getClient()
        
        try {
            val results = client.searchCode(query, projectId, 20)
            CodeRAGToolWindow.showSearchResults(project, results)
        } catch (e: Exception) {
            com.intellij.openapi.ui.Messages.showErrorDialog(
                project,
                "Search failed: ${e.message}",
                "CodeRAG Search"
            )
        }
    }
}

class SearchCodeDialog(project: Project) : DialogWrapper(project) {
    private val queryField = JTextField(30)
    private val projectService = CodeRAGProjectService.getInstance(project)
    
    init {
        title = "CodeRAG Search"
        init()
    }
    
    override fun createCenterPanel(): JComponent {
        val panel = JPanel()
        panel.add(JLabel("Search query:"))
        panel.add(queryField)
        return panel
    }
    
    fun getQuery(): String = queryField.text
    
    fun getProjectId(): Int? = projectService.getCurrentProjectId()
}



