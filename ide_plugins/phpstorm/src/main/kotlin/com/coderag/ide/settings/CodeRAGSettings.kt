package com.coderag.ide.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.*

/**
 * CodeRAG plugin settings
 */
@State(
    name = "CodeRAGSettings",
    storages = [Storage("CodeRAG.xml")]
)
@Service
class CodeRAGSettings : PersistentStateComponent<CodeRAGSettings.State> {
    data class State(
        var baseUrl: String = "http://localhost:8000",
        var timeout: Int = 30000,
        var showInlineAnnotations: Boolean = true,
        var annotationSeverity: String = "medium" // low, medium, high
    )
    
    private var state = State()
    
    override fun getState(): State = state
    
    override fun loadState(state: State) {
        this.state = state
    }
    
    var baseUrl: String
        get() = state.baseUrl
        set(value) {
            state.baseUrl = value
        }
    
    var timeout: Int
        get() = state.timeout
        set(value) {
            state.timeout = value
        }
    
    var showInlineAnnotations: Boolean
        get() = state.showInlineAnnotations
        set(value) {
            state.showInlineAnnotations = value
        }
    
    var annotationSeverity: String
        get() = state.annotationSeverity
        set(value) {
            state.annotationSeverity = value
        }
    
    companion object {
        fun getInstance(): CodeRAGSettings {
            return ApplicationManager.getApplication().getService(CodeRAGSettings::class.java)
        }
    }
}



