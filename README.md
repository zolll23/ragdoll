# CodeRAG - Intelligent Code Analysis System

RAG система для анализа PHP/Python кода с использованием ИИ агентов для индексации и семантического поиска.

## Возможности

1. **Поиск методов по функциональности** - семантический поиск по описанию функциональности
2. **Поиск похожих кусков кода** - для рефакторинга (игнорирует имена переменных)
3. **Определение сложности** - асимптотическая сложность методов с поиском по условиям
4. **Анализ SOLID** - определение нарушений принципов SOLID
5. **Архитектурный анализ** - определение роли в DDD/MVC и паттернов проектирования
6. **Тестируемость** - оценка пригодности методов к Unit тестированию
7. **Обычный поиск** - поиск по коду

## Архитектура

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **Базы данных**: 
  - PostgreSQL (pgvector) - метаданные и структурированные данные
  - Qdrant - векторные embeddings
  - Redis - очереди задач
- **Очереди**: Celery
- **LLM**: Поддержка OpenAI, Anthropic, Ollama

## Быстрый старт

### Требования

- Docker и Docker Compose
- (Опционально) OpenAI API ключ или локальный Ollama

### Установка

1. Клонируйте репозиторий:
```bash
git clone <repository>
cd coderag
```

2. Создайте файл `.env` в корне проекта (или используйте переменные окружения):
```bash
# Backend .env
cd backend
cp .env.example .env
# Отредактируйте .env и добавьте API ключи
```

3. Запустите систему:
```bash
make build
make up
```

4. Инициализируйте базу данных:
```bash
make init-db
```

5. Откройте в браузере:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Использование

### Создание проекта

1. Откройте веб-интерфейс: http://localhost:3000
2. Перейдите в "Projects"
3. Нажмите "Add Project"
4. Укажите:
   - Название проекта
   - Путь к каталогу с кодом (должен быть доступен в контейнере)
   - Язык (Python или PHP)

Индексация начнется автоматически в фоновом режиме.

### Поиск

Используйте естественный язык для поиска:

- "найти все методы отправки сообщения в чат"
- "методы со сложностью O(n^2) или выше"
- "нарушения принципа Барбары Лисков"
- "контроллеры для управления пользователями"
- "методы создания бота"

### Добавление проекта для индексации

Перед созданием проекта в веб-интерфейсе, нужно добавить монтирование каталога с кодом:

```bash
make add BASE_PATH=/path/to/your/project
```

Эта команда:
- Добавит монтирование каталога в docker-compose.yml
- Перезапустит контейнеры
- Теперь вы можете создать проект с этим путем в веб-интерфейсе

**Пример:**
```bash
make add BASE_PATH=/home/user/my-python-project
```

После этого в веб-интерфейсе создайте проект с путем `/home/user/my-python-project`.

### Реиндексация

Для обновления индекса после изменений в коде:

```bash
make reindex PROJECT_ID=1
```

Или через API:
```bash
curl -X POST http://localhost:8000/api/projects/1/reindex
```

## Конфигурация

### LLM Провайдеры

Система поддерживает три провайдера:

1. **Ollama** (по умолчанию, локально):
```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:latest
OLLAMA_URL=http://host.docker.internal:11434
```

**Важно:** Убедитесь, что Ollama запущена локально и модель загружена:
```bash
ollama pull qwen3:latest
```

2. **OpenAI**:
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_key
```

3. **Anthropic**:
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229
ANTHROPIC_API_KEY=your_key
```

### Embeddings

Для локального использования:
```env
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Для production (OpenAI):
```env
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072
```

## API

### Endpoints

- `GET /api/projects` - список проектов
- `POST /api/projects` - создать проект
- `POST /api/projects/{id}/reindex` - реиндексировать проект
- `POST /api/search` - поиск по коду
- `GET /api/entities/{id}` - получить сущность
- `GET /api/entities/{id}/analysis` - получить анализ

Полная документация: http://localhost:8000/docs

## Структура проекта

```
coderag/
├── backend/              # FastAPI приложение
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── agents/      # AI агенты
│   │   ├── core/        # Конфигурация
│   │   ├── models/      # Модели БД
│   │   ├── parsers/     # Парсеры кода
│   │   └── services/    # Бизнес-логика
│   └── requirements.txt
├── frontend/            # React приложение
│   └── src/
├── data/                 # Локальные данные БД
│   ├── postgres/        # PostgreSQL данные
│   └── qdrant/          # Qdrant данные
├── docker-compose.yml   # Docker конфигурация
└── Makefile            # Утилиты
```

## Разработка

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Производительность

- Индексация: ~1-5 секунд на файл (зависит от LLM)
- Поиск: <100ms для структурированных запросов, <500ms для семантических
- Поддержка больших проектов: инкрементальная индексация только измененных файлов

## Ограничения

- Парсер кода использует regex (можно улучшить с Tree-sitter)
- Контекст для анализа ограничен размером окна LLM
- Индексация больших проектов может занять время

## Планы развития

- [ ] Улучшение парсера с Tree-sitter
- [ ] Поддержка больше языков (JavaScript, Java, Go)
- [ ] Плагины для IDE (PHPStorm, PyCharm)
- [ ] Улучшенный анализ контекста (зависимости)
- [ ] Веб-хуки для автоматической реиндексации
- [ ] Экспорт результатов анализа

## Лицензия

MIT

