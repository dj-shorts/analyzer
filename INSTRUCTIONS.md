# Инструкция по созданию GitHub Issues

## Подготовка

### 1. Создание GitHub Personal Access Token

1. Перейдите в GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Нажмите "Generate new token (classic)"
3. Выберите следующие права:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org and team membership)
   - `project` (Full control of user projects)
4. Скопируйте созданный токен

### 2. Поиск PROJECT_ID

Выполните команду для поиска ID проекта "MVP Analyzer":

```bash
node find_project_id.mjs YOUR_GITHUB_TOKEN
```

Найдите строку с PROJECT_ID и скопируйте значение.

## Запуск

### Вариант 1: Автоматический (рекомендуется)

```bash
./run_create_issues.sh YOUR_GITHUB_TOKEN [PROJECT_ID]
```

Если PROJECT_ID не указан, скрипт попытается найти его автоматически.

### Вариант 2: Ручной

```bash
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN"
export PROJECT_ID="YOUR_PROJECT_ID"

node create_gh_issues_from_json.mjs \
  --repo "dj-shorts/analyzer" \
  --token "$GITHUB_TOKEN" \
  --file "BACKLOG_MVP_ANALYZER.json" \
  --labels "area:analyzer,type:feature" \
  --project-id "$PROJECT_ID"
```

## Что будет создано

Скрипт создаст 26 issues в репозитории `dj-shorts/analyzer` на основе файла `BACKLOG_MVP_ANALYZER.json`:

- **Epic A**: Базовый анализатор (7 issues)
- **Epic B**: Квантизация по битам (2 issues)  
- **Epic C**: Анализ движения (1 issue)
- **Epic D**: Экспорт видео (3 issues)
- **Epic E**: CLI интеграция (3 issues)
- **Epic F**: Тестирование (3 issues)
- **Epic G**: Мониторинг (1 issue)
- **Epic H**: Упаковка (2 issues)
- **Epic I**: Эксперименты (2 issues)

Каждый issue будет:
- Добавлен в проект "MVP Analyzer"
- Помечен лейблами `area:analyzer` и `type:feature`
- Содержать информацию о приоритете, оценке времени и зависимостях

## Проверка

После выполнения скрипта проверьте:
1. [Проект MVP Analyzer](https://github.com/orgs/dj-shorts/projects/1/views/1)
2. Репозиторий [dj-shorts/analyzer](https://github.com/dj-shorts/analyzer/issues)

## Отладка

Если что-то пошло не так:

1. Проверьте права токена
2. Убедитесь, что репозиторий `dj-shorts/analyzer` существует
3. Проверьте, что у вас есть права на создание issues в организации
4. Запустите с флагом `--dry-run` для тестирования без создания issues:

```bash
node create_gh_issues_from_json.mjs \
  --repo "dj-shorts/analyzer" \
  --token "$GITHUB_TOKEN" \
  --file "BACKLOG_MVP_ANALYZER.json" \
  --labels "area:analyzer,type:feature" \
  --dry-run
```
