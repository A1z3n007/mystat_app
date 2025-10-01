# 📦 mystat-desktop

Лёгкое **десктоп-приложение на PyQt5** для работы со студенческим кабинетом MyStat:
домашки, расписание, статистика, быстрый аплоад файлов и удобный вход без браузера.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-%E2%9C%94-41CD52)
![License](https://img.shields.io/badge/License-MIT-informational)

> ⚠️ Проект **неофициальный**, создан в учебных целях.

---

## ✨ Основные фичи

- 🔐 **Встроенный логин-диалог** (без WebEngine): филиал (город), логин/e-mail, пароль, «запомнить меня».
- 🧭 **Город (branch) динамически**: все запросы используют выбранный филиал, а не захардкоженный.
- 💾 **SQLite** для хранения токена и настроек (`utils/db.py`).
- ☁️ **Аплоад файлов** в FS и отправка ДЗ из приложения.
- 🧹 **Автокэш иконок по URL** (не нужно паковать папки с иконками) — `utils/icons.py`.
- 🗑️ Удаление отправленного ДЗ (если доступно).
- 🗓️ Расписание, активность, «лидерборд», базовые графики (если ты используешь их в `main_window.py`).
- 🎨 Единая тема оформления (`frontend/theme.py`) в стиле MyStat.

---

## 🗂️ Структура проекта

mystat-desktop/
├─ main.py
├─ backend/
│ └─ mystat_api.py # запросы к API MyStat + логин
├─ frontend/
│ ├─ main_window.py # основное окно приложения
│ ├─ login_dialog.py # диалог входа (город + логин + пароль)
│ ├─ theme.py # QSS тема
│ └─ fs_sniffer.py # (опц.) перехват Bearer для FS через WebEngine
├─ utils/
│ ├─ db.py # лёгкая key-value БД (SQLite)
│ └─ icons.py # загрузка и кэш иконок по URL
├─ app.db # SQLite (создаётся автоматически)
├─ requirements.txt
└─ README.md


---

## 🛠️ Стек

- **Python** 3.10+
- **PyQt5** (QtWidgets, QtGui, QtCore)
- **requests**
- (опц.) **PyQtWebEngine** — только если используешь `fs_sniffer.py`

---

## 🔑 Авторизация

Окно входа открывается автоматически, если токен не сохранён.

Поля: Филиал (город), Логин/E-mail, Пароль, чекбокс «Запомнить меня».

При успешном входе токен и город сохраняются в app.db.

В backend/mystat_api.py функция login_with_credentials поддерживает оба варианта:
login_with_credentials(login, password) и login_with_credentials(city, login, password).

---

## 🌐 Иконки по URL

Чтобы иконки не пропадали в сборке, используем utils/icons.py:
from utils.icons import qicon_from_url

self.btn_home.setIcon(qicon_from_url("https://cdn-icons-png.flaticon.com/512/25/25694.png"))
self.btn_schedule.setIcon(qicon_from_url("https://cdn-icons-png.flaticon.com/512/747/747310.png"))
self.btn_hw.setIcon(qicon_from_url("https://cdn-icons-png.flaticon.com/512/906/906334.png"))
Иконки будут кешироваться в utils/_icon_cache/.

---

## ⚙️ Конфиг и БД

Лёгкий key-value слой в utils/db.py.
Полезные ключи:
mystat_token — токен пользователя
mystat_city — текущий филиал
fs_bearer, fs_directory, fs_host — настройки файлового сервиса

---

##📦 Сборка .exe (PyInstaller)

Самый простой способ (Windows):
pyinstaller --noconsole --name mystatdesk --onefile main.py
Рекомендации:

Иконки грузятся по сети → не нужно добавлять папку icons/ в datas.

Если используешь собственные локальные ресурсы (QSS, png и пр.), добавь:
--add-data "frontend/styles.qss;frontend"
Если используешь WebEngine (опциональный перехватчик FS), смотри раздел «Проблемы».

---

## 🔒 Безопасность

Токены хранятся локально в app.db (SQLite). Не коммить в репозиторий.

Не публикуй/не шерь токены и приватные URL.

Проект учебный; полагайся на свою организационную политику безопасности.

---

## 🤝 Контрибьютинг

PR и Issue приветствуются:

соблюдай PEP8,

понятные коммиты,

без секретов в коде и истории.

---

## 🙌 Благодарности

Дизайн вдохновлён веб-интерфейсом MyStat.

Иконки — Flaticon и др. открытые наборы.

---

## 🚀 Быстрый старт (dev)

```bash
# 1) создаём окружение
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1

# 2) зависимости
pip install -r requirements.txt

# 3) запуск
python main.py
