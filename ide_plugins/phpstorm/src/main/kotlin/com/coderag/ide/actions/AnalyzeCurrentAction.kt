package com.coderag.ide.actions

import com.coderag.ide.services.CodeRAGProjectService
import com.coderag.ide.services.CodeRAGService
import com.coderag.ide.ui.CodeRAGToolWindow
import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.psi.PsiElement
import com.jetbrains.php.lang.psi.elements.PhpClass
import com.jetbrains.php.lang.psi.elements.Method

/**
 * Action to analyze current method or class
 */
class AnalyzeCurrentAction : AnAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val psiFile = e.getData(CommonDataKeys.PSI_FILE) ?: return
        
        val caretModel = editor.caretModel
        val offset = caretModel.offset
        val psiElement = psiFile.findElementAt(offset) ?: return
        
        // Find containing method or class
        val containingElement = findContainingElement(psiElement)
        if (containingElement == null) {
            Messages.showInfoMessage(
                project,
                "Please place cursor inside a method or class",
                "CodeRAG Analysis"
            )
            return
        }
        
        // Get file path and line number
        val virtualFile = psiFile.virtualFile
        val filePath = virtualFile.path
        val lineNumber = psiFile.document?.getLineNumber(offset) ?: 0
        
        // Find project ID
        val projectService = CodeRAGProjectService.getInstance(project)
        var projectId = projectService.getCurrentProjectId()
        if (projectId == null) {
            projectId = projectService.findProjectId(project.basePath ?: "")
            if (projectId != null) {
                projectService.setCurrentProjectId(projectId)
            }
        }
        
        if (projectId == null) {
            Messages.showErrorDialog(
                project,
                "Could not find CodeRAG project. Please configure project mapping in settings.",
                "CodeRAG Analysis"
            )
            return
        }
        
        // Analyze entity
        analyzeEntity(project, projectId, filePath, lineNumber)
    }
    
    private fun findContainingElement(element: PsiElement): PsiElement? {
        var current: PsiElement? = element
        while (current != null) {
            if (current is Method || current is PhpClass) {
                return current
            }
            current = current.parent
        }
        return null
    }
    
    private fun analyzeEntity(project: Project, projectId: Int, filePath: String, lineNumber: Int) {
        val service = CodeRAGService.getInstance()
        val client = service.getClient()
        
        try {
            val entity = client.findEntity(projectId, filePath, lineNumber)
            
            // Show in tool window
            CodeRAGToolWindow.show(project, entity)
        } catch (e: Exception) {
            Messages.showErrorDialog(
                project,
                "Failed to analyze entity: ${e.message}",
                "CodeRAG Analysis"
            )
        }
    }
}



