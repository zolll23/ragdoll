// Simple i18n implementation
import { useState, useEffect } from 'react'

const translations = {
  EN: {
    // Navigation
    home: "Home",
    search: "Search",
    projects: "Projects",
    providers: "LLM Providers",
    
    // Projects
    addProject: "Add Project",
    projectName: "Project Name",
    path: "Path",
    language: "Language",
    uiLanguage: "Interface Language",
    create: "Create",
    cancel: "Cancel",
    reindex: "Reindex",
    delete: "Delete",
    noProjects: "No projects yet. Create your first project to start indexing.",
    
    // Progress
    indexing: "Indexing...",
    progress: "Progress",
    filesIndexed: "Files indexed",
    totalFiles: "Total files",
    entities: "Entities",
    completed: "Completed",
    currentFile: "Current file",
    
    // Search
    searchPlaceholder: "Search for methods, classes, or ask questions...",
    searchButton: "Search",
    selectProject: "Select Project",
    selectProjectFirst: "Please select a project first",
    found: "Found",
    results: "result(s)",
    noResults: "Enter a search query to find code",
    examples: "Examples:",
    example1: "find all methods for sending messages",
    example2: "methods with complexity O(n^2) or higher",
    example3: "violations of Liskov Substitution Principle",
    example4: "controllers for user management",
    
    // Home
    title: "CodeRAG - Intelligent Code Analysis",
    subtitle: "RAG system for PHP/Python code with AI-powered indexing and semantic search",
    startSearching: "Start Searching",
    
    // Features
    semanticSearch: "Semantic Search",
    semanticSearchDesc: "Find methods by functionality using natural language queries",
    codeAnalysis: "Code Analysis",
    codeAnalysisDesc: "Detect SOLID violations, complexity, and design patterns",
    similarityDetection: "Similarity Detection",
    similarityDetectionDesc: "Find similar code blocks for refactoring opportunities",
    fastIndexing: "Fast Indexing",
    fastIndexingDesc: "Incremental indexing tracks code changes automatically",
    
    // Entities
    entities: "Entities",
    entitiesList: "Entities List",
    searchEntities: "Search entities...",
    allTypes: "All Types",
    showing: "Showing",
    of: "of",
    noEntities: "No entities found",
    hasAnalysis: "Has analysis",
    selectEntity: "Select an entity to view analysis",
    analysisDetails: "Analysis Details",
    description: "Description",
    dependencies: "Dependencies",
    imports: "Imports",
    extends: "Extends",
    implements: "Implements",
    methodCalls: "Method Calls",
    notIndexed: "Not indexed",
    noDependencies: "No dependencies found",
    designPatterns: "Design Patterns",
    architecturalRoles: "Architectural Roles",
    solidViolations: "SOLID Violations",
    testability: "Testability",
    testable: "Testable",
    notTestable: "Not Testable",
    score: "Score",
    testabilityIssues: "Testability Issues",
    suggestion: "Suggestion",
    // Extended Metrics
    codeMetrics: "Code Metrics",
    linesOfCode: "Lines of Code",
    parameters: "Parameters",
    cyclomaticComplexity: "Cyclomatic Complexity",
    cognitiveComplexity: "Cognitive Complexity",
    maxNestingDepth: "Max Nesting Depth",
    couplingScore: "Coupling Score",
    cohesionScore: "Cohesion Score",
    securityIssues: "Security Issues",
    nPlusOneQueries: "N+1 Queries",
    godObject: "God Object",
    longParameterList: "Long Parameter List",
    detected: "Detected",
    viewEntities: "View Entities",
    code: "Code",
    backToSearch: "Back to Search",
    entityNotFound: "Entity not found",
    noAnalysis: "No analysis available for this entity",
    reindexFailed: "Reindex Failed",
    reindexFailedStarted: "Reindexing failed analyses started",
    reindexFailedConfirm: "Reindex all entities with failed analysis?",
    reindexingFailed: "Reindexing failed entities",
    failedEntities: "Failed entities",
    reindexed: "Reindexed",
    failedAnalysis: "Failed analysis",
    withoutAnalysis: "Without analysis",
    deleteEntities: "Delete Entities",
    deleteEntitiesStarted: "Entity deletion started",
    deleteAllEntitiesConfirm: "Delete all entities from this project? This cannot be undone.",
    stopIndexing: "Stop Indexing",
    resumeIndexing: "Resume Indexing",
    startIndexing: "Start Indexing",
    indexingStopped: "Indexing stopped",
    indexingResumed: "Indexing resumed",
    indexingStarted: "Indexing started",
    
    // Providers
    llmProviders: "LLM Providers",
    manageProviders: "Manage AI model providers and their configurations",
    addProvider: "Add Provider",
    editProvider: "Edit Provider",
    providerType: "Provider Type",
    selectProvider: "Select Provider",
    displayName: "Display Name",
    baseUrl: "Base URL",
    apiKey: "API Key",
    active: "Active",
    inactive: "Inactive",
    default: "Default",
    leaveEmptyToKeep: "Leave empty to keep current",
    update: "Update",
    deleteProviderConfirm: "Are you sure you want to delete this provider?",
    noProviders: "No providers configured. Add your first provider to start.",
    models: "Models",
    availableModels: "Available Models",
    edit: "Edit",
    defaultModel: "Default Model",
    selectModel: "Select Model",
    model: "Model",
    refreshModels: "Refresh Models",
    saveProviderFirst: "Please save the provider first to load available models",
    saveProviderToLoadModels: "Save provider first, then edit to load available models",
    currentProvider: "Current Provider",
    noDefaultProvider: "No default provider set. Set a provider as default to use it for indexing.",
    
    // Metric descriptions
    metricDescription: "Metric Description",
    close: "Close",
    locDescription: "Lines of Code (LOC) is a simple metric that counts the number of lines in the source code. It provides a basic measure of code size and complexity. Higher LOC values generally indicate larger, potentially more complex codebases.",
    parametersDescription: "Parameter Count measures the number of parameters a method or function accepts. Methods with many parameters (typically >5) can be harder to understand, test, and maintain. This may indicate a need for refactoring, such as introducing parameter objects.",
    cyclomaticComplexityDescription: "Cyclomatic Complexity measures the number of linearly independent paths through a program's source code. It's calculated by counting decision points (if, while, for, case, etc.) plus 1. Lower values (1-10) indicate simpler, more maintainable code. Higher values (>20) suggest complex logic that may need refactoring.",
    cognitiveComplexityDescription: "Cognitive Complexity measures how difficult code is to understand by humans. Unlike cyclomatic complexity, it penalizes nested structures more heavily. It considers nesting depth, control flow structures, and logical operators. Lower values indicate more readable code.",
    maxNestingDepthDescription: "Max Nesting Depth measures the deepest level of nested control structures (if, for, while, etc.) in the code. High nesting depth (>4) makes code harder to read and understand. It's often a sign that code should be refactored to reduce nesting, possibly by extracting methods or using early returns.",
    couplingScoreDescription: "Coupling Score measures how tightly a module is connected to other modules. High coupling means a module depends heavily on other modules, making the code harder to change, test, and maintain. Lower coupling (closer to 0) indicates better modularity and independence.",
    cohesionScoreDescription: "Cohesion Score measures how well the elements within a module work together to achieve a single, well-defined purpose. High cohesion (closer to 1.0) means all elements in a module are related and focused on a single responsibility. Low cohesion suggests the module may be doing too many things and should be split.",
    securityIssuesDescription: "Security Issues identifies potential security vulnerabilities in the code, such as SQL injection risks, XSS (Cross-Site Scripting) vulnerabilities, hardcoded secrets, and insecure dependencies. Each issue includes its type, severity, location, and suggested remediation.",
    nPlusOneQueriesDescription: "N+1 Queries is a performance anti-pattern where an application makes N+1 database queries instead of a single optimized query. This typically occurs when iterating over a collection and making a separate query for each item. It can severely impact performance and should be fixed by using eager loading or batch queries.",
    godObjectDescription: "God Object is an anti-pattern where a single class or object knows or does too much. It violates the Single Responsibility Principle and makes code hard to maintain, test, and understand. A God Object typically has high LOC, many methods, and high coupling. It should be broken down into smaller, focused classes.",
    longParameterListDescription: "Long Parameter List is a code smell that occurs when a method has too many parameters (typically >5). This makes the method harder to understand, test, and maintain. Common solutions include introducing parameter objects, using builder patterns, or refactoring to reduce the number of parameters.",
  },
  RU: {
    // Navigation
    home: "Главная",
    search: "Поиск",
    projects: "Проекты",
    providers: "LLM Провайдеры",
    
    // Projects
    addProject: "Добавить проект",
    projectName: "Название проекта",
    path: "Путь",
    language: "Язык",
    uiLanguage: "Язык интерфейса",
    create: "Создать",
    cancel: "Отмена",
    reindex: "Реиндексировать",
    delete: "Удалить",
    noProjects: "Проектов пока нет. Создайте первый проект для начала индексации.",
    
    // Progress
    indexing: "Индексация...",
    progress: "Прогресс",
    filesIndexed: "Файлов проиндексировано",
    totalFiles: "Всего файлов",
    entities: "Сущностей",
    tokensUsed: "Использовано токенов",
    completed: "Завершено",
    currentFile: "Текущий файл",
    
    // Search
    searchPlaceholder: "Поиск методов, классов или задайте вопрос...",
    searchButton: "Поиск",
    selectProject: "Выберите проект",
    selectProjectFirst: "Пожалуйста, сначала выберите проект",
    found: "Найдено",
    results: "результат(ов)",
    noResults: "Введите поисковый запрос для поиска кода",
    examples: "Примеры:",
    example1: "найти все методы отправки сообщения",
    example2: "методы со сложностью O(n^2) или выше",
    example3: "нарушения принципа Барбары Лисков",
    example4: "контроллеры для управления пользователями",
    
    // Home
    title: "CodeRAG - Интеллектуальный анализ кода",
    subtitle: "RAG система для анализа PHP/Python кода с индексацией и семантическим поиском на основе ИИ",
    startSearching: "Начать поиск",
    
    // Features
    semanticSearch: "Семантический поиск",
    semanticSearchDesc: "Поиск методов по функциональности с использованием естественного языка",
    codeAnalysis: "Анализ кода",
    codeAnalysisDesc: "Обнаружение нарушений SOLID, сложности и паттернов проектирования",
    similarityDetection: "Поиск похожих участков",
    similarityDetectionDesc: "Поиск похожих блоков кода для рефакторинга",
    fastIndexing: "Быстрая индексация",
    fastIndexingDesc: "Инкрементальная индексация отслеживает изменения кода автоматически",
    
    // Entities
    entities: "Сущности",
    tokensUsed: "Использовано токенов",
    entitiesList: "Список сущностей",
    searchEntities: "Поиск сущностей...",
    allTypes: "Все типы",
    showing: "Показано",
    of: "из",
    noEntities: "Сущности не найдены",
    hasAnalysis: "Есть анализ",
    selectEntity: "Выберите сущность для просмотра анализа",
    analysisDetails: "Детали анализа",
    description: "Описание",
    dependencies: "Зависимости",
    imports: "Импорты",
    extends: "Наследуется от",
    implements: "Реализует",
    methodCalls: "Вызовы методов",
    notIndexed: "Не проиндексировано",
    noDependencies: "Зависимости не найдены",
    designPatterns: "Паттерны проектирования",
    architecturalRoles: "Архитектурные роли",
    solidViolations: "Нарушения SOLID",
    testability: "Тестируемость",
    testable: "Тестируемо",
    notTestable: "Не тестируемо",
    score: "Оценка",
    testabilityIssues: "Проблемы тестируемости",
    suggestion: "Предложение",
    // Extended Metrics
    codeMetrics: "Метрики кода",
    linesOfCode: "Строк кода",
    parameters: "Параметры",
    cyclomaticComplexity: "Цикломатическая сложность",
    cognitiveComplexity: "Когнитивная сложность",
    maxNestingDepth: "Макс. глубина вложенности",
    couplingScore: "Связанность",
    cohesionScore: "Сцепленность",
    securityIssues: "Проблемы безопасности",
    nPlusOneQueries: "N+1 запросы",
    godObject: "Божественный объект",
    longParameterList: "Длинный список параметров",
    detected: "Обнаружено",
    viewEntities: "Просмотр сущностей",
    code: "Код",
    backToSearch: "Вернуться к поиску",
    entityNotFound: "Сущность не найдена",
    similarCode: "Похожий код",
    similarCodeSearch: "Поиск похожего кода",
    pair: "Пара",
    of: "из",
    similarity: "Схожесть",
    noSimilarCodeFound: "Похожий код не найден",
    previous: "Предыдущий",
    next: "Следующий",
    noAnalysis: "Анализ недоступен для этой сущности",
    reindexFailed: "Реиндексировать неудачные",
    reindexFailedStarted: "Реиндексация неудачных анализов запущена",
    reindexFailedConfirm: "Реиндексировать все сущности с неудачным анализом?",
    reindexingFailed: "Реиндексация неудачных сущностей",
    failedEntities: "Неудачных сущностей",
    reindexed: "Реиндексировано",
    failedAnalysis: "Неудачных анализов",
    withoutAnalysis: "Без анализа",
    deleteEntities: "Удалить сущности",
    deleteEntitiesStarted: "Удаление сущностей запущено",
    deleteAllEntitiesConfirm: "Удалить все сущности из этого проекта? Это действие нельзя отменить.",
    stopIndexing: "Остановить индексацию",
    resumeIndexing: "Возобновить индексацию",
    startIndexing: "Запустить индексацию",
    indexingStopped: "Индексация остановлена",
    indexingResumed: "Индексация возобновлена",
    indexingStarted: "Индексация запущена",
    
    // Providers
    llmProviders: "LLM Провайдеры",
    manageProviders: "Управление провайдерами AI моделей и их конфигурациями",
    addProvider: "Добавить провайдер",
    editProvider: "Редактировать провайдер",
    providerType: "Тип провайдера",
    selectProvider: "Выберите провайдер",
    displayName: "Отображаемое имя",
    baseUrl: "Базовый URL",
    apiKey: "API ключ",
    active: "Активен",
    inactive: "Неактивен",
    default: "По умолчанию",
    leaveEmptyToKeep: "Оставьте пустым, чтобы сохранить текущий",
    update: "Обновить",
    deleteProviderConfirm: "Вы уверены, что хотите удалить этого провайдера?",
    noProviders: "Провайдеры не настроены. Добавьте первого провайдера для начала.",
    models: "Модели",
    availableModels: "Доступные модели",
    edit: "Редактировать",
    defaultModel: "Модель по умолчанию",
    selectModel: "Выберите модель",
    model: "Модель",
    refreshModels: "Обновить модели",
    saveProviderFirst: "Сначала сохраните провайдер, чтобы загрузить доступные модели",
    saveProviderToLoadModels: "Сначала сохраните провайдер, затем отредактируйте для загрузки моделей",
    currentProvider: "Текущий провайдер",
    noDefaultProvider: "Провайдер по умолчанию не установлен. Установите провайдер как используемый по умолчанию для индексации.",
    
    // Metric descriptions
    metricDescription: "Описание метрики",
    close: "Закрыть",
    locDescription: "Строки кода (LOC) — простая метрика, подсчитывающая количество строк в исходном коде. Дает базовую оценку размера и сложности кода. Большие значения LOC обычно указывают на более крупную и потенциально более сложную кодовую базу.",
    parametersDescription: "Количество параметров измеряет число параметров, которые принимает метод или функция. Методы с большим количеством параметров (обычно >5) сложнее понимать, тестировать и поддерживать. Это может указывать на необходимость рефакторинга, например, введения объектов параметров.",
    cyclomaticComplexityDescription: "Цикломатическая сложность измеряет количество линейно независимых путей через исходный код программы. Вычисляется подсчетом точек принятия решений (if, while, for, case и т.д.) плюс 1. Низкие значения (1-10) указывают на более простой и поддерживаемый код. Высокие значения (>20) предполагают сложную логику, которая может потребовать рефакторинга.",
    cognitiveComplexityDescription: "Когнитивная сложность измеряет, насколько сложен код для понимания человеком. В отличие от цикломатической сложности, она более строго наказывает вложенные структуры. Учитывает глубину вложенности, структуры управления потоком и логические операторы. Низкие значения указывают на более читаемый код.",
    maxNestingDepthDescription: "Максимальная глубина вложенности измеряет самый глубокий уровень вложенных управляющих структур (if, for, while и т.д.) в коде. Высокая глубина вложенности (>4) делает код сложнее для чтения и понимания. Часто это признак того, что код следует рефакторить для уменьшения вложенности, возможно, путем извлечения методов или использования ранних возвратов.",
    couplingScoreDescription: "Связанность измеряет, насколько тесно модуль связан с другими модулями. Высокая связанность означает, что модуль сильно зависит от других модулей, что усложняет изменение, тестирование и поддержку кода. Низкая связанность (ближе к 0) указывает на лучшую модульность и независимость.",
    cohesionScoreDescription: "Сцепленность измеряет, насколько хорошо элементы внутри модуля работают вместе для достижения единой, четко определенной цели. Высокая сцепленность (ближе к 1.0) означает, что все элементы модуля связаны и сосредоточены на одной ответственности. Низкая сцепленность предполагает, что модуль может делать слишком много вещей и должен быть разделен.",
    securityIssuesDescription: "Проблемы безопасности выявляют потенциальные уязвимости в коде, такие как риски SQL-инъекций, уязвимости XSS (межсайтовый скриптинг), захардкоженные секреты и небезопасные зависимости. Каждая проблема включает тип, серьезность, местоположение и предложения по исправлению.",
    nPlusOneQueriesDescription: "N+1 запросы — это антипаттерн производительности, при котором приложение выполняет N+1 запросов к базе данных вместо одного оптимизированного запроса. Обычно это происходит при итерации по коллекции и выполнении отдельного запроса для каждого элемента. Это может серьезно повлиять на производительность и должно быть исправлено с помощью жадной загрузки или пакетных запросов.",
    godObjectDescription: "Божественный объект — это антипаттерн, при котором один класс или объект знает или делает слишком много. Это нарушает принцип единственной ответственности и усложняет поддержку, тестирование и понимание кода. Божественный объект обычно имеет высокий LOC, много методов и высокую связанность. Его следует разбить на более мелкие, сфокусированные классы.",
    longParameterListDescription: "Длинный список параметров — это запах кода, возникающий, когда метод имеет слишком много параметров (обычно >5). Это усложняет понимание, тестирование и поддержку метода. Распространенные решения включают введение объектов параметров, использование паттернов строителя или рефакторинг для уменьшения количества параметров.",
  }
}

let currentLanguage = localStorage.getItem('ui_language') || 'EN'

export const i18n = {
  t: (key) => {
    return translations[currentLanguage]?.[key] || translations.EN[key] || key
  },
  setLanguage: (lang) => {
    if (translations[lang]) {
      currentLanguage = lang
      localStorage.setItem('ui_language', lang)
      window.dispatchEvent(new Event('languageChange'))
    }
  },
  getLanguage: () => currentLanguage,
}

export const useLanguage = () => {
  const [lang, setLang] = useState(i18n.getLanguage())

  useEffect(() => {
    const handleLanguageChange = () => {
      setLang(i18n.getLanguage())
    }
    window.addEventListener('languageChange', handleLanguageChange)
    return () => {
      window.removeEventListener('languageChange', handleLanguageChange)
    }
  }, [])

  return {
    lang,
    setLanguage: i18n.setLanguage,
    t: i18n.t
  }
}

export default i18n

