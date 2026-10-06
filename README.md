# EduPlatform — версия SQLite

Четыре приложения: accounts, education, assignments и notifications.
Сохранены группы, занятия, материалы, задания, оценки, посещаемость,
чат, руки, опросы, уведомления и Telegram-бот.
В архиве нет тестовых файлов, демоданных, секретов и виртуального окружения.

## База данных

SQLite встроена в Python. Отдельный сервер базы, логин и пароль не нужны.
Локально данные сохраняются в data/db.sqlite3 рядом с manage.py.
Каталог создаётся автоматически, таблицы создаёт команда migrate.
SQLITE_DIR позволяет задать другой каталог базы.
Загруженные файлы хранятся отдельно в private_media.
Начальная база пустая: старые данные автоматически не импортируются.

В Docker все процессы (init, web, worker, bot) используют один том sqlite_data,
подключённый к /app/data. Файлы пользователей сохраняются в томе media.
Redis по-прежнему нужен для событий WebSocket между процессами.

## Зависимости

В requirements.txt семь основных библиотек:
Django — страницы, модели, формы и авторизация;
channels — WebSocket; channels-redis — события через Redis;
aiogram — Telegram; python-dotenv — .env;
uvicorn — сервер; websockets — WebSocket для сервера.
Служебные зависимости устанавливает pip автоматически.

## Подготовка

Распакуйте архив в новую папку. Откройте терминал в папке с manage.py.
Создайте настройки:

```powershell
Copy-Item .env.example .env
notepad .env
```

Замените SECRET_KEY случайной строкой. Получить её можно в PowerShell:

```powershell
[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
```

Для локальной работы оставьте DEBUG=1.

## Запуск через Docker Desktop

Запустите Docker Desktop и дождитесь готовности Linux Engine.

```powershell
docker compose up --build -d
docker compose ps
docker compose exec web python manage.py createsuperuser
```

Контейнер init применяет миграции и завершается с кодом 0 — это нормально.
Сайт: http://localhost:8000/; админка: http://localhost:8000/admin/.
Учителя и ученики регистрируются на сайте, готовых аккаунтов нет.

## Запуск Python на компьютере

Нужен Python 3.12. Redis можно оставить в Docker:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d redis
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe -m uvicorn config.asgi:application --host 127.0.0.1 --port 8000 --reload
```

В другом терминале, из той же папки:

```powershell
.\.venv\Scripts\python.exe manage.py runworker
```

Используйте Uvicorn: обычный runserver в этой сборке не обслуживает WebSocket.
Не запускайте локальный сервер и контейнер web на одном порту одновременно.
Локальный запуск и Docker используют разные файлы базы и каталоги загрузок.

## Telegram

Создайте бота через @BotFather. Заполните TELEGRAM_BOT_TOKEN и
TELEGRAM_BOT_USERNAME (без @) в .env. Для Docker:

```powershell
docker compose --profile telegram up --build -d
```

При локальном запуске дополнительно выполните в отдельном терминале:

```powershell
.\.venv\Scripts\python.exe manage.py runbot
```

На сайте откройте Профиль → Подключить Telegram.
Без токена сайт работает, но Telegram-сообщения не отправляются.

## Одновременная работа и сохранность данных

SQLite допускает одного писателя одновременно. atomic-транзакции используют
режим IMMEDIATE и ждут освобождения записи до 20 секунд. Это сохраняет
последовательность изменений заданий, оценок и получения сообщений из очереди.
При большой нагрузке всё ещё возможна ошибка database is locked.
Для учебного запуска достаточно одного web, одного worker и одного bot.

Не удаляйте data/db.sqlite3, если нужны записи. Для резервной копии остановите
все процессы приложения и скопируйте каталог data вместе с private_media.
Для Docker сохраняйте содержимое томов sqlite_data и media после остановки
процессов приложения. Обычный docker compose down сохраняет тома;
docker compose down -v удаляет базу и загруженные файлы.

## Код и ограничения

Описание модулей находится в docs/ARCHITECTURE.md.
Миграции нужны для создания таблиц: не удаляйте их.
Локальная учебная сборка использует DEBUG=1 и HTTP. При DEBUG=0 требуется
отдельная настройка выдачи статики. Посещаемость отражает соединение со страницей.
Повторная отправка Telegram после аварии иногда может дать дубль.
Реальная доставка Telegram требует вашего токена.
