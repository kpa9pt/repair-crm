# Repair CRM

[![Docker](https://img.shields.io/badge/Docker-20.10+-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)


Система для управления ремонтами и заказами в мастерской мототехники.

---

## 📌 О проекте

Repair CRM — backend-система для обработки заявок на ремонт.  
Проект построен как API-first приложение с административной панелью.

**Portable deployment:** достаточно Docker и свободных портов 80/443.

---

## ⚙️ Возможности

- CRUD заявок на ремонт
- Фильтрация и пагинация
- REST API (Swagger UI)
- Административная панель (SQLAdmin)
- Docker-окружение для разработки
- CI/CD (GitHub Actions + GHCR)
- Автоматический HTTPS (Let's Encrypt)

---

## 🧱 Технологии

- Python 3.14 / FastAPI
- PostgreSQL / SQLAlchemy (async)
- Alembic / pytest
- Docker / Docker Compose
- Nginx / Certbot
- GitHub Container Registry

---

## 📋 Требования

- Docker (20.10+)
- Docker Compose (2.20+)
- Свободные порты: 80, 443 (для HTTPS)

---

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/kpa9pt/repair-crm.git
cd repair-crm

# 2. Запустить проект (.env создастся автоматически)
make up

# 3. Остановить проект
make down
```

---

## 🌐 После запуска доступны сервисы:

|   Сервис	   |           URL           |
|:-----------:|:-----------------------:|
| API Gateway |    	http://localhost    |
| Swagger UI  | 	http://localhost/docs  |
| Admin panel | 	http://localhost/admin |

---

## 🔧 Переменные окружения

При первом запуске файл .env создаётся автоматически из .env.example:
```bash
cp .env.example .env   # если нужно отредактировать вручную
```
Основные переменные:

| Переменная      | 	Значение по умолчанию                                                | 	Описание                               |
|:----------------|:----------------------------------------------------------------------|:----------------------------------------|
| DATABASE_URL    | 	postgresql+asyncpg://postgres:<br>postgres@postgres:5432/repair_crm	 | Подключение к БД                        |
| ADMIN_USERNAME	 | admin	                                                                | Логин админ-панели                      |
| ADMIN_PASSWORD	 | (смотри .env.example)	                                                | Пароль админ-панели                     |
| DOMAIN_NAME	    | localhost	                                                            | Домен (для продакшена укажите реальный) |


> Для HTTPS укажите реальный домен и настройте DNS запись на IP вашего сервера. Certbot автоматически получит сертификат.

---

## 🛠️ Основные команды

```bash
make up          # запустить все сервисы
make down        # остановить и удалить контейнеры
make build       # пересобрать и запустить
make test        # запустить все тесты
make logs        # посмотреть логи
make help        # показать все команды
```

---

## 🧪 Тестирование

```bash
make test
```

Тесты запускаются в Docker-окружении с автоматическим поднятием инфраструктуры и пересозданием базы данных.

---

## 🔐 Административный доступ

Доступ к админ-панели:
- URL: http://localhost/admin
- Login: admin
- Password: admin123

> Админ-панель — основной инструмент для управления заявками.


---

## 🚀 Деплой на VPS

- Клонируйте репозиторий на сервер
- Настройте .env (укажите DOMAIN_NAME и пароли)
- Выполните make up

---

## 🤖 Автоматический CI/CD (опционально)

В репозитории настроены GitHub Actions:

- Build and Push to GHCR — сборка образа при пуше в main
- Deploy to VDS — автоматический деплой на сервер

Для работы CI/CD нужны секреты (смотри .github/workflows/deploy.yml).


---

## 🧭 Архитектура

```text
Nginx (порты 80/443) → Gateway (FastAPI) → PostgreSQL
                ↓
         Certbot (HTTPS)
```

---

## 🎯 Дальнейшее развитие

- [ ] **Модель "Техника"** — единицы техники с историей ремонтов
- [ ] **Telegram бот** — уведомления о новых заявках
- [ ] **React фронтенд** — полноценный интерфейс для менеджеров
- [ ] **Blue/Green деплой** — zero-downtime обновления
- [ ] **Мобильное приложение (iOS)** — для механиков в поле

---

## 📄 Лицензия

MIT

---