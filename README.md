# EgeNotifier

**Telegram-бот для проверки результатов ЕГЭ с push-уведомлениями**

Телеграмм бот, который помогает школьникам и родителям оперативно узнавать результаты ЕГЭ.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-00A4FF?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

## Возможности

- ⚡ **Push-уведомления** при появлении или изменении результатов
- 🎯 **Подбор вузов** по сумме баллов (бюджет / платное)
- 📊 Красивое отображение баллов + автосумма
- 📈 История изменений по каждому предмету
- 🔐 Удобная авторизация без постоянного ввода данных

## Скриншоты и демонстрация

![Демонстрация работы бота](https://imgur.com/a/7YH6HCu)
![Возможность скрывать результаты](https://imgur.com/a/MAjmCfq)
![Подбор вузов](https://imgur.com/a/nhO4pZ5)

## Как запустить

```bash
git clone https://github.com/ttinkerov/EgeNotifier.git
cd EgeNotifier
cp .env.example .env
```

Заполни `.env` (токен бота, PostgreSQL, свой Telegram ID).

```bash
pip install -e .
py main.py
```
