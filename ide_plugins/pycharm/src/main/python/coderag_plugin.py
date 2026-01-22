"""
CodeRAG PyCharm Plugin
Main plugin entry point
"""
from typing import Any, Optional
from pathlib import Path

# PyCharm SDK imports (these would be available in PyCharm plugin environment)
# from com.jetbrains.python import PythonFileType
# from com.intellij.openapi.actionSystem import AnAction, AnActionEvent
# from com.intellij.openapi.project import Project

try:
    # Plugin SDK imports (when running in PyCharm)
    from com.intellij.openapi.components import ApplicationComponent
    from com.intellij.openapi.actionSystem import AnAction, AnActionEvent
    from com.intellij.openapi.project import Project
    PYCHARM_AVAILABLE = True
except ImportError:
    # Fallback for development/testing
    PYCHARM_AVAILABLE = False


class CodeRAGPlugin(ApplicationComponent if PYCHARM_AVAILABLE else object):
    """Main plugin component"""
    
    def __init__(self):
        self.client = None
        self.base_url = "http://localhost:8000"
    
    def initComponent(self):
        """Initialize plugin"""
        self.load_settings()
        self.init_client()
    
    def load_settings(self):
        """Load plugin settings"""
        # TODO: Load from PyCharm settings
        pass
    
    def init_client(self):
        """Initialize API client"""
        import sys
        shared_path = Path(__file__).parent.parent.parent.parent / "shared"
        if shared_path.exists():
            sys.path.insert(0, str(shared_path))
        
        try:
            from python_client import CodeRAGClient
            self.client = CodeRAGClient(base_url=self.base_url)
        except ImportError:
            print("Warning: CodeRAG client not available")
    
    def get_client(self):
        """Get API client"""
        return self.client


class AnalyzeCurrentAction(AnAction if PYCHARM_AVAILABLE else object):
    """Action to analyze current method or class"""
    
    def actionPerformed(self, e: AnActionEvent):
        """Handle action"""
        project = e.getProject()
        if not project:
            return
        
        # Get current file and cursor position
        # TODO: Implement analysis logic
        pass


class SearchCodeAction(AnAction if PYCHARM_AVAILABLE else object):
    """Action to search code"""
    
    def actionPerformed(self, e: AnActionEvent):
        """Handle action"""
        project = e.getProject()
        if not project:
            return
        
        # TODO: Show search dialog and perform search
        pass


# Plugin metadata (for PyCharm plugin.xml equivalent)
PLUGIN_METADATA = {
    "id": "com.coderag.ide.pycharm",
    "name": "CodeRAG",
    "version": "1.0.0",
    "description": "CodeRAG plugin for PyCharm",
    "vendor": "CodeRAG",
    "actions": [
        {
            "id": "CodeRAG.AnalyzeCurrent",
            "class": "coderag_plugin.AnalyzeCurrentAction",
            "text": "Analyze with CodeRAG",
            "description": "Analyze current method or class"
        },
        {
            "id": "CodeRAG.SearchCode",
            "class": "coderag_plugin.SearchCodeAction",
            "text": "Search Code...",
            "description": "Search code using natural language"
        }
    ]
}



