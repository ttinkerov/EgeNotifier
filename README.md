# EgeNotifier

**Telegram-бот для проверки результатов ЕГЭ с push-уведомлениями**

Телеграмм бот, который помогает школьникам и родителям оперативно узнавать результаты ЕГЭ.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-00A4FF?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

## Возможности

- ⚡ **Push-уведомления** при появлении или изменении результатов
- 🎯 **Подбор вузов** по сумме баллов (бюджет / платное)
- 📈 История изменений по каждому предмету
- 🔐 Удобная авторизация без постоянного ввода данных
- 🔒 Шифрование session token / document_ref в PostgreSQL
- 💾 FSM в Postgres (состояния переживают рестарт)

## Скриншоты и демонстрация

![Демонстрация работы бота](https://i.imgur.com/VrsKTaN.png)
![Возможность скрывать результаты](https://i.imgur.com/AmLXubq.png)
![Подбор вузов](https://i.imgur.com/ZzTJvfT.png)

## Как запустить

```bash
git clone https://github.com/ttinkerov/EgeNotifier.git
cd EgeNotifier
cp .env.default .env
```

Заполни `.env` (токен бота, PostgreSQL, свой Telegram ID, `DATA_ENCRYPTION_KEY`):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

```bash
pip install -e ".[dev]"
python main.py
```

## Каталог вузов

Проверить JSON:

```bash
update-universities path/to/catalog.json --check
```

Установить в `src/egebot/data/universities.json`:

```bash
update-universities path/to/catalog.json
```

В боте админ может перезагрузить каталог из файла на диске без рестарта: `/reload_unis`.

## Тесты

```bash
pytest
```
