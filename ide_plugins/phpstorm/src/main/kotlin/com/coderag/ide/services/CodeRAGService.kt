package com.coderag.ide.services

import com.coderag.ide.client.CodeRAGClient
import com.coderag.ide.settings.CodeRAGSettings
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service

/**
 * Application-level service for CodeRAG
 * Manages API client and global settings
 */
@Service
class CodeRAGService {
    private var client: CodeRAGClient? = null
    private var baseUrl: String = "http://localhost:8000"
    
    init {
        loadSettings()
    }
    
    fun getClient(): CodeRAGClient {
        if (client == null || client?.baseUrl != baseUrl) {
            client = CodeRAGClient(baseUrl)
        }
        return client!!
    }
    
    fun setBaseUrl(url: String) {
        baseUrl = url
        client = CodeRAGClient(baseUrl)
    }
    
    fun getBaseUrl(): String = baseUrl
    
    private fun loadSettings() {
        val settings = CodeRAGSettings.getInstance()
        baseUrl = settings.baseUrl
    }
    
    companion object {
        fun getInstance(): CodeRAGService {
            return ApplicationManager.getApplication().getService(CodeRAGService::class.java)
        }
    }
}

