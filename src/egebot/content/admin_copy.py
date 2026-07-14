ADMIN_ONLY = "Команда доступна только администраторам."

ADMIN_STATS_HEADER = "*📊 Статистика бота*\n"

ADMIN_BROADCAST_ASK = (
    "Отправь текст рассылки одним сообщением.\n"
    "Отмена — /cancel"
)

ADMIN_BROADCAST_CANCELLED = "Рассылка отменена."

ADMIN_BROADCAST_EMPTY = "Пустое сообщение. Рассылка отменена."

ADMIN_PORTAL_DOWN = (
    "⚠️ *Портал проверки ЕГЭ недоступен*\n"
    "Подряд неудачных запросов: *{failures}*\n"
    "Watcher ушёл в backoff."
)

ADMIN_PORTAL_RECOVERED = "✅ Портал проверки ЕГЭ снова отвечает."

ADMIN_CATALOG_RELOADED = "Каталог вузов перезагружен: *{count}* программ."

ADMIN_CATALOG_INVALID = "Не удалось перезагрузить каталог:\n`{error}`"


def format_stats(
    *,
    version: str,
    total_users: int,
    active_sessions: int,
    with_scores: int,
    alerts_enabled: int,
    spoiler_enabled: int,
    pending_auth: int,
    score_events: int,
) -> str:
    return (
        f"{ADMIN_STATS_HEADER}\n"
        f"Версия: `{version}`\n\n"
        f"Пользователей: *{total_users}*\n"
        f"Активных сессий: *{active_sessions}*\n"
        f"С баллами: *{with_scores}*\n"
        f"Уведомления вкл: *{alerts_enabled}*\n"
        f"Спойлер вкл: *{spoiler_enabled}*\n"
        f"Незавершённый вход: *{pending_auth}*\n"
        f"Событий в истории: *{score_events}*"
    )


def format_broadcast_result(sent: int, blocked: int, failed: int, total: int) -> str:
    return (
        "*Рассылка завершена*\n\n"
        f"Всего: *{total}*\n"
        f"Доставлено: *{sent}*\n"
        f"Заблокировали бота: *{blocked}*\n"
        f"Ошибок: *{failed}*"
    )
