from egebot.content.university_catalog import SUBJECT_LABELS
from egebot.domain.universities import (
    STUDY_FIELD_LABELS,
    FundingType,
    MatchResult,
    StudyField,
    UserScores,
)


UNI_INTRO = (
    "*🎓 Подбор вузов*\n\n"
    "Подберу программы по *твоим реальным баллам* с портала ЕГЭ.\n"
    "Учитываются все сданные предметы — хоть 3, хоть 4 и больше."
)

UNI_NEED_AUTH = (
    "Подбор вузов доступен после входа.\n\n"
    "Нажми *🔐 Войти* или /start — подтяну все твои баллы с портала автоматически."
)

UNI_SCORES_EMPTY = (
    "На портале пока нет баллов для подбора.\n"
    "Когда результаты появятся — зайди снова через «🎓 Подбор вузов»."
)

UNI_ASK_FUNDING = "Какой тип места ищешь?"

UNI_ASK_REGION = "В каком регионе хочешь учиться?"

UNI_ASK_FIELD = "Кем хочешь стать / какое направление интересует?"

UNI_NO_MATCHES = (
    "По этим параметрам подходящих программ не нашлось.\n"
    "Попробуй платное место, другой регион или снизь планку направления."
)


def format_user_scores(scores: UserScores) -> str:
    if not scores.subjects:
        return "_баллы не указаны_"
    lines = [
        f"• {SUBJECT_LABELS.get(key, key)} — *{value}*"
        for key, value in sorted(scores.subjects.items(), key=lambda x: x[0])
    ]
    return "\n".join(lines)


def format_match_results(results: list[MatchResult]) -> str:
    pages = format_match_pages(results)
    return pages[0] if pages else UNI_NO_MATCHES


def format_match_pages(results: list[MatchResult], *, page_size: int = 8) -> list[str]:
    if not results:
        return [UNI_NO_MATCHES]

    footer = (
        "\n_Проходной балл — ориентир по прошлым годам. "
        "Показываю все программы, куда ты хотя бы приближаешься. "
        "Проверяй правила приёма на сайте вуза._"
    )
    total = len(results)
    pages: list[str] = []

    for start in range(0, total, page_size):
        chunk = results[start : start + page_size]
        lines = [f"*🏆 Варианты ({start + 1}–{start + len(chunk)} из {total}):*\n"]
        for index, item in enumerate(chunk, start=start + 1):
            funding = "бюджет" if item.program.funding is FundingType.BUDGET else "платное"
            gap = f"+{item.margin}" if item.margin >= 0 else str(item.margin)
            lines.append(
                f"*{index}. {item.program.university}*\n"
                f"{item.program.program}\n"
                f"📍 {item.program.city} · {funding}\n"
                f"Проходной: ~{item.program.passing_total} · твой: *{item.user_total}* ({gap})\n"
                f"Шанс: *{item.probability}%* ({item.probability_label})\n"
            )
        if start + page_size >= total:
            lines.append(footer)
        pages.append("\n".join(lines))

    return pages


def field_label(field: StudyField) -> str:
    return STUDY_FIELD_LABELS[field]
