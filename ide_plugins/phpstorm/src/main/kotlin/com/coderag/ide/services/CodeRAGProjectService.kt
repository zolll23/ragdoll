package com.coderag.ide.services

import com.coderag.ide.client.CodeRAGClient
import com.intellij.openapi.components.Service
import com.intellij.openapi.project.Project

/**
 * Project-level service for CodeRAG
 * Manages project-specific state and cached data
 */
@Service(Service.Level.PROJECT)
class CodeRAGProjectService(private val project: Project) {
    private var currentProjectId: Int? = null
    private var projectCache: Map<String, Any>? = null
    
    fun getCurrentProjectId(): Int? = currentProjectId
    
    fun setCurrentProjectId(projectId: Int) {
        currentProjectId = projectId
        projectCache = null
    }
    
    fun findProjectId(projectPath: String): Int? {
        // Try to find project by matching path
        val client = CodeRAGService.getInstance().getClient()
        try {
            val projects = client.listProjects()
            return projects.firstOrNull { 
                projectPath.contains(it.path) || it.path.contains(projectPath)
            }?.id
        } catch (e: Exception) {
            return null
        }
    }
    
    companion object {
        fun getInstance(project: Project): CodeRAGProjectService {
            return project.getService(CodeRAGProjectService::class.java)
        }
    }
}



