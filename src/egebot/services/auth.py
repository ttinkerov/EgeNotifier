from __future__ import annotations

from hashlib import md5

from loguru import logger

from egebot.content.federal_subjects import describe_subject, subject_exists
from egebot.core.rustest import CaptchaPayload, RustestClient
from egebot.domain.models import AuthDraft, ExamScore, SignInStatus, TgAccount
from egebot.services.scores import ScoresService
from egebot.storage.repositories.accounts import AccountRepository
from egebot.storage.repositories.auth_drafts import AuthDraftRepository


def digest_name(full_name: str) -> str | None:
    parts = full_name.split()
    if len(parts) < 2:
        return None
    normalized = "".join(parts).lower().replace("ё", "е").replace("й", "и").replace("-", "")
    return md5(normalized.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        drafts: AuthDraftRepository,
        accounts: AccountRepository,
        rustest: RustestClient,
        scores: ScoresService,
    ) -> None:
        self._drafts = drafts
        self._accounts = accounts
        self._rustest = rustest
        self._scores = scores

    async def save_name(self, telegram_id: int, full_name: str) -> bool:
        name_hash = digest_name(full_name)
        if not name_hash:
            return False
        await self._drafts.update(telegram_id, step="region", name_digest=name_hash)
        return True

    async def save_region(self, telegram_id: int, code_text: str) -> tuple[bool, str | None]:
        if len(code_text) != 2 or not code_text.isdigit():
            return False, None
        code = int(code_text)
        if not subject_exists(code):
            return False, None
        await self._drafts.update(telegram_id, step="document", subject_code=code)
        return True, describe_subject(code)

    async def save_document(self, telegram_id: int, document: str) -> bool:
        if " " in document or not document.isdigit():
            return False
        if len(document) not in (6, 12):
            return False
        await self._drafts.update(telegram_id, step="captcha", document_ref=document)
        return True

    async def request_captcha(self, telegram_id: int) -> CaptchaPayload | None:
        captcha = await self._rustest.fetch_captcha()
        if captcha is None:
            return None
        await self._drafts.update(
            telegram_id,
            step="captcha",
            challenge_id=captcha.challenge_id,
            challenge_reply=None,
        )
        return captcha

    async def save_captcha_answer(self, telegram_id: int, answer: str) -> bool:
        if len(answer) != 6 or not answer.isdigit():
            return False
        await self._drafts.update(telegram_id, step="login", challenge_reply=answer)
        return True

    async def complete_login(self, telegram_id: int) -> tuple[SignInStatus, list[ExamScore] | None]:
        draft = await self._drafts.get(telegram_id)
        if draft is None:
            return SignInStatus.BAD_CREDENTIALS, None

        status, token = await self._rustest.sign_in(draft)
        if status is not SignInStatus.OK or not token:
            return status, None

        assert draft.subject_code is not None
        existing = await self._accounts.get(telegram_id)
        await self._accounts.save(
            TgAccount(
                telegram_id=telegram_id,
                subject_code=draft.subject_code,
                session_token=token,
                alerts_enabled=True,
                spoiler_scores=existing.spoiler_scores if existing else False,
                snapshot_hash=existing.snapshot_hash if existing else None,
            )
        )
        fetch = await self._rustest.fetch_scores(token)
        exams = fetch.exams if fetch.is_ok else None
        if exams:
            await self._scores.seed_snapshot(telegram_id, exams)
        await self._drafts.delete(telegram_id)
        logger.info("Login completed for user {}", telegram_id)
        return SignInStatus.OK, exams

    async def reset_captcha_step(self, telegram_id: int) -> None:
        await self._drafts.update(
            telegram_id,
            step="captcha",
            challenge_id=None,
            challenge_reply=None,
        )
