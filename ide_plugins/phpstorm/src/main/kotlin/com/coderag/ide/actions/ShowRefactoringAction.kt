package com.coderag.ide.actions

import com.coderag.ide.services.CodeRAGProjectService
import com.coderag.ide.services.CodeRAGService
import com.coderag.ide.ui.CodeRAGToolWindow
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages

/**
 * Action to show refactoring suggestions
 */
class ShowRefactoringAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val psiFile = e.getData(CommonDataKeys.PSI_FILE) ?: return
        
        val caretModel = editor.caretModel
        val offset = caretModel.offset
        
        // Get entity ID from previous analysis or find entity
        val projectService = CodeRAGProjectService.getInstance(project)
        val projectId = projectService.getCurrentProjectId() ?: return
        
        val virtualFile = psiFile.virtualFile
        val filePath = virtualFile.path
        val lineNumber = psiFile.document?.getLineNumber(offset) ?: 0
        
        val service = CodeRAGService.getInstance()
        val client = service.getClient()
        
        try {
            val entity = client.findEntity(projectId, filePath, lineNumber)
            val suggestions = client.getRefactoringSuggestions(entity.entity.id)
            
            CodeRAGToolWindow.showRefactoringSuggestions(project, suggestions)
        } catch (e: Exception) {
            Messages.showErrorDialog(
                project,
                "Failed to get refactoring suggestions: ${e.message}",
                "CodeRAG Refactoring"
            )
        }
    }
}



