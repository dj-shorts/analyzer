#!/usr/bin/env python3
"""
Скрипт для создания и управления GitHub Issues через API.
Используется для переноса Epic B issues в Project Backlog.
"""

import json
import requests
import os
from typing import Dict, List, Optional

class GitHubIssuesManager:
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_url = f"https://api.github.com/repos/{owner}/{repo}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "dj-shorts-analyzer"
        }
    
    def create_issue(self, title: str, body: str, labels: List[str] = None, 
                     assignees: List[str] = None) -> Dict:
        """Создать новый issue"""
        data = {
            "title": title,
            "body": body,
            "labels": labels or [],
            "assignees": assignees or []
        }
        
        response = requests.post(
            f"{self.base_url}/issues",
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create issue: {response.status_code} - {response.text}")
    
    def get_issues(self, state: str = "open") -> List[Dict]:
        """Получить список issues"""
        response = requests.get(
            f"{self.base_url}/issues",
            headers=self.headers,
            params={"state": state}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get issues: {response.status_code} - {response.text}")
    
    def update_issue(self, issue_number: int, **kwargs) -> Dict:
        """Обновить issue"""
        response = requests.patch(
            f"{self.base_url}/issues/{issue_number}",
            headers=self.headers,
            json=kwargs
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to update issue: {response.status_code} - {response.text}")
    
    def add_issue_to_project(self, issue_number: int, project_id: int, 
                            column_id: int) -> Dict:
        """Добавить issue в проект (требует GraphQL API)"""
        # Это требует GraphQL API и более сложной реализации
        # Пока что возвращаем заглушку
        return {"message": "Project integration requires GraphQL API implementation"}

def main():
    """Основная функция для создания Epic B issues"""
    
    # Получить токен из переменной окружения
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Ошибка: Необходимо установить переменную окружения GITHUB_TOKEN")
        print("   export GITHUB_TOKEN=your_github_token")
        return
    
    # Параметры репозитория
    owner = "TerryBerk"
    repo = "dj-shorts"
    
    manager = GitHubIssuesManager(token, owner, repo)
    
    # Epic B Issues данные
    epic_b_issues = [
        {
            "title": "[EPIC_B_BEAT_QUANT] B1 — Локальный BPM и сетка ударов",
            "body": """Оценить BPM и биты (`librosa.beat.beat_track`) в окне ±30–45s.

**Критерии приёмки**
- Возврат времён ударов, BPM, confidence [0..1]
- На синтетике 4/4 ошибка ≤100ms

**Зависимости:** A6

**Статус:** ✅ ЗАВЕРШЕНО
- Реализован модуль `src/analyzer/beats.py` с классами `BeatTracker` и `BeatQuantizer`
- Интеграция с librosa для beat tracking (`librosa.beat.beat_track`)
- Оценка BPM и confidence на основе консистентности битов
- Генерация регулярной сетки битов для квантизации
- Добавлены зависимости: `librosa>=0.10.0`, `soundfile>=0.12.0`
- Комплексные unit-тесты для всех компонентов""",
            "labels": ["area:analyzer", "type:feature", "epic:beat-quantization", "status:completed"]
        },
        {
            "title": "[EPIC_B_BEAT_QUANT] B2 — Квантизация старта и длины клипа",
            "body": """Старт переносится на ближайший удар/бар **перед** `t_start`; длина = `N*bar` (N∈{8,12,16}).

**Критерии приёмки**
- `aligned=true` при успешной квантизации
- Фоллбек при низкой уверенности

**Зависимости:** B1

**Статус:** ✅ ЗАВЕРШЕНО
- Квантизация старта клипа к ближайшему биту перед оригинальным временем
- Квантизация длительности к границам баров (2, 4, 6, 8, 12, 16 баров)
- Адаптивная логика выбора количества баров в зависимости от исходной длительности
- Проверка разумности квантизации с fallback на оригинальные значения
- Интеграция в основной pipeline анализа
- Реальное видео протестировано с успешной квантизацией всех 6 клипов""",
            "labels": ["area:analyzer", "type:feature", "epic:beat-quantization", "status:completed"]
        }
    ]
    
    print("🚀 Создание Epic B issues в GitHub...")
    
    try:
        for issue_data in epic_b_issues:
            print(f"📝 Создание issue: {issue_data['title']}")
            
            issue = manager.create_issue(
                title=issue_data["title"],
                body=issue_data["body"],
                labels=issue_data["labels"]
            )
            
            print(f"✅ Issue создан: #{issue['number']} - {issue['title']}")
            print(f"🔗 URL: {issue['html_url']}")
            print()
        
        print("🎉 Все Epic B issues успешно созданы!")
        print("\n📋 Следующие шаги:")
        print("1. Перейдите в GitHub Project Backlog")
        print("2. Перенесите созданные issues из 'No Status' в 'ToDo'")
        print("3. При начале работы с каждым issue ставьте его в 'In Progress'")
        print("4. При завершении работы ставьте в 'Done'")
        
    except Exception as e:
        print(f"❌ Ошибка при создании issues: {e}")

if __name__ == "__main__":
    main()