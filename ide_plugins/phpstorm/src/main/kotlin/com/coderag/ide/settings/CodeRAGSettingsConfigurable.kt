package com.coderag.ide.settings

import com.intellij.openapi.options.Configurable
import javax.swing.JComponent
import javax.swing.JPanel
import javax.swing.JTextField
import javax.swing.JCheckBox

/**
 * Settings UI for CodeRAG plugin
 */
class CodeRAGSettingsConfigurable : Configurable {
    private val panel = JPanel()
    private val baseUrlField = JTextField(30)
    private val showAnnotationsCheckbox = JCheckBox("Show inline annotations")
    
    init {
        // TODO: Build UI panel
    }
    
    override fun getDisplayName(): String = "CodeRAG"
    
    override fun createComponent(): JComponent {
        val settings = CodeRAGSettings.getInstance()
        baseUrlField.text = settings.baseUrl
        showAnnotationsCheckbox.isSelected = settings.showInlineAnnotations
        
        panel.add(javax.swing.JLabel("API Base URL:"))
        panel.add(baseUrlField)
        panel.add(showAnnotationsCheckbox)
        
        return panel
    }
    
    override fun isModified(): Boolean {
        val settings = CodeRAGSettings.getInstance()
        return baseUrlField.text != settings.baseUrl ||
               showAnnotationsCheckbox.isSelected != settings.showInlineAnnotations
    }
    
    override fun apply() {
        val settings = CodeRAGSettings.getInstance()
        settings.baseUrl = baseUrlField.text
        settings.showInlineAnnotations = showAnnotationsCheckbox.isSelected
        
        // Update service
        com.coderag.ide.services.CodeRAGService.getInstance().setBaseUrl(settings.baseUrl)
    }
    
    override fun reset() {
        val settings = CodeRAGSettings.getInstance()
        baseUrlField.text = settings.baseUrl
        showAnnotationsCheckbox.isSelected = settings.showInlineAnnotations
    }
}



