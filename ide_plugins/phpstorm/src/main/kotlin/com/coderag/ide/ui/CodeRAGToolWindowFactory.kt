package com.coderag.ide.ui

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory

/**
 * Factory for CodeRAG tool window
 */
class CodeRAGToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        CodeRAGToolWindow.create(project, toolWindow)
    }
}



