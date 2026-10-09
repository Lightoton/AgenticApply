---
name: python-verify
description: >-
  Use this skill to run syntax checks, byte-compilation, and tests for the AgenticApply Python project.
---

# Python Verification Workflow

## Инструкция по проверке:

1. Проверить синтаксис всех ключевых модулей:
   ```sh
   python -m py_compile main.py
   python -m py_compile core/config.py
   python -m py_compile core/state.py
   ```
2. Проверить корректность загрузки конфигурации:
   ```sh
   python -c "from core.config import settings; print('Configuration loaded successfully')"
   ```
3. Проверить состояние базы данных и контейнеров (если развернуты):
   ```sh
   docker compose ps
   ```
4. Если написаны тесты:
   ```sh
   pytest -v
   ```
