from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from egebot.domain.universities import STUDY_FIELD_LABELS, StudyField

KEY_UNIVERSITIES = "🎓 Подбор вузов"
KEY_SETTINGS = "⚙️ Настройки"
KEY_SIGN_IN = "🔐 Войти"
KEY_SCORES = "📊 Мои баллы"
KEY_HISTORY = "📈 История"
KEY_FAQ = "❓ FAQ"
KEY_CALENDAR = "📅 Календарь"
KEY_EXIT = "🚪 Выйти"


def guest_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=KEY_SIGN_IN)],
            [KeyboardButton(text=KEY_FAQ), KeyboardButton(text=KEY_CALENDAR)],
        ],
        resize_keyboard=True,
    )


def member_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=KEY_SCORES), KeyboardButton(text=KEY_HISTORY)],
            [KeyboardButton(text=KEY_UNIVERSITIES)],
            [KeyboardButton(text=KEY_SETTINGS), KeyboardButton(text=KEY_FAQ)],
            [KeyboardButton(text=KEY_CALENDAR)],
            [KeyboardButton(text=KEY_EXIT)],
        ],
        resize_keyboard=True,
    )


def subjects_toggle(collapsed: bool = True) -> InlineKeyboardMarkup:
    label = "Показать коды субъектов" if collapsed else "Свернуть список"
    action = "geo:expand" if collapsed else "geo:collapse"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=label, callback_data=action)]],
    )


def refresh_scores() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="↻ Обновить", callback_data="scores:refresh"),
                InlineKeyboardButton(text="📈 История", callback_data="scores:history"),
            ],
        ],
    )


def settings_keyboard(spoiler_enabled: bool) -> InlineKeyboardMarkup:
    if spoiler_enabled:
        label = "🔒 Спойлер баллов: вкл"
    else:
        label = "👁 Спойлер баллов: выкл"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="settings:spoiler:toggle")],
        ],
    )


def captcha_again() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Новая капча", callback_data="captcha:new")]],
    )


def retry_auth() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Повторить", callback_data="auth:retry")],
            [InlineKeyboardButton(text="С начала", callback_data="auth:reset")],
        ],
    )


def uni_funding() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎓 Бюджет", callback_data="uni:funding:budget"),
                InlineKeyboardButton(text="💳 Платное", callback_data="uni:funding:paid"),
            ],
            [InlineKeyboardButton(text="Любое", callback_data="uni:funding:any")],
        ],
    )


def uni_regions() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Москва", callback_data="uni:region:77"),
                InlineKeyboardButton(text="МО", callback_data="uni:region:50"),
            ],
            [
                InlineKeyboardButton(text="СПб", callback_data="uni:region:78"),
                InlineKeyboardButton(text="Казань", callback_data="uni:region:16"),
            ],
            [
                InlineKeyboardButton(text="Екатеринбург", callback_data="uni:region:66"),
                InlineKeyboardButton(text="Новосибирск", callback_data="uni:region:54"),
            ],
            [
                InlineKeyboardButton(text="Н. Новгород", callback_data="uni:region:52"),
                InlineKeyboardButton(text="Томск", callback_data="uni:region:70"),
            ],
            [
                InlineKeyboardButton(text="Краснодар", callback_data="uni:region:23"),
                InlineKeyboardButton(text="Воронеж", callback_data="uni:region:36"),
            ],
            [InlineKeyboardButton(text="🌍 Любой регион", callback_data="uni:region:any")],
        ],
    )


def uni_fields() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for field in StudyField:
        rows.append([
            InlineKeyboardButton(
                text=STUDY_FIELD_LABELS[field],
                callback_data=f"uni:field:{field.value}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def uni_restart() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Подобрать снова", callback_data="uni:restart")],
        ],
    )
