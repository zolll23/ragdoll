# CodeRAG PyCharm Plugin

PyCharm plugin for CodeRAG code analysis and refactoring.

## Features

- **Code Analysis**: Analyze methods and classes with AI-powered analysis
- **Natural Language Search**: Search code using natural language queries
- **Refactoring Suggestions**: Get SOLID violations and code quality suggestions
- **Inline Annotations**: See code metrics and issues directly in the editor
- **Tool Window**: Detailed analysis view in a dedicated tool window

## Installation

1. Copy plugin files to PyCharm plugins directory
2. Restart PyCharm
3. Configure API URL in Settings → CodeRAG

## Configuration

1. Open Settings → CodeRAG
2. Set API Base URL (default: `http://localhost:8000`)
3. Configure inline annotation preferences

## Usage

### Analyze Current Code

1. Place cursor inside a method or class
2. Right-click → "Analyze with CodeRAG" (or `Ctrl+Alt+A`)
3. View results in CodeRAG tool window

### Search Code

1. Tools → "Search Code..." (or `Ctrl+Alt+S`)
2. Enter natural language query
3. View results in tool window

### Refactoring Suggestions

1. Place cursor in code
2. Right-click → "Show Refactoring Suggestions"
3. View suggestions with severity and locations

## Requirements

- PyCharm 2023.3 or later
- Python 3.8+
- CodeRAG backend running (default: `http://localhost:8000`)
- Project must be indexed in CodeRAG

## Development

PyCharm plugins are written in Python using the PyCharm SDK.

### Project Structure

```
src/main/python/
├── actions/          # IDE actions
├── services/         # Services
├── settings/         # Settings
└── ui/              # UI components
```

## License

See main CodeRAG repository license.



