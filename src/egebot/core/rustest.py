from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass

import aiohttp
from loguru import logger

from egebot.config import Settings
from egebot.domain.exam_snapshot import FetchScoresResult
from egebot.domain.models import AuthDraft, ExamScore, SignInStatus

_NETWORK_ERRORS = (
    aiohttp.ClientError,
    asyncio.TimeoutError,
    TimeoutError,
)


@dataclass(slots=True)
class CaptchaPayload:
    challenge_id: str
    image: bytes


class RustestClient:
    def __init__(self, settings: Settings) -> None:
        self._cfg = settings
        self._http: aiohttp.ClientSession | None = None

    async def open(self) -> None:
        if self._http is None:
            self._http = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=True, limit=10),
                headers=self._cfg.rustest_headers,
                timeout=aiohttp.ClientTimeout(total=25, connect=10, sock_read=20),
                cookie_jar=aiohttp.DummyCookieJar(),
            )

    async def close(self) -> None:
        if self._http is not None:
            await self._http.close()
            self._http = None

    def _session(self) -> aiohttp.ClientSession:
        if self._http is None:
            raise RuntimeError("RustestClient is not started")
        return self._http

    async def fetch_captcha(self) -> CaptchaPayload | None:
        try:
            async with self._session().get(
                self._cfg.rustest_captcha_endpoint,
                proxy=self._cfg.proxy_url,
            ) as resp:
                if resp.status != 200:
                    logger.warning("Captcha HTTP {}", resp.status)
                    return None
                data = await resp.json()
                return CaptchaPayload(
                    challenge_id=data["Token"],
                    image=base64.b64decode(data["Image"]),
                )
        except (*_NETWORK_ERRORS, KeyError, TypeError, ValueError) as exc:
            logger.warning("Captcha fetch failed: {}", exc)
            return None

    async def sign_in(self, draft: AuthDraft) -> tuple[SignInStatus, str | None]:
        if not draft.name_digest or draft.subject_code is None or not draft.document_ref:
            return SignInStatus.BAD_CREDENTIALS, None
        if not draft.challenge_reply or not draft.challenge_id:
            return SignInStatus.BAD_CREDENTIALS, None

        doc = draft.document_ref
        if 5 <= len(doc) < 12:
            payload = {
                "Hash": draft.name_digest,
                "Document": doc.rjust(12, "0"),
                "Region": draft.subject_code,
                "Captcha": draft.challenge_reply,
                "Token": draft.challenge_id,
            }
        else:
            payload = {
                "Hash": draft.name_digest,
                "Code": doc,
                "Region": draft.subject_code,
                "Captcha": draft.challenge_reply,
                "Token": draft.challenge_id,
            }

        try:
            async with self._session().post(
                self._cfg.rustest_signin_endpoint,
                data=payload,
                proxy=self._cfg.proxy_url,
            ) as resp:
                if resp.status >= 500:
                    logger.warning("Sign-in HTTP {}", resp.status)
                    return SignInStatus.PORTAL_ERROR, None
                cookie = resp.cookies.get("Participant")
                if cookie is not None:
                    return SignInStatus.OK, cookie.value
                return SignInStatus.BAD_CREDENTIALS, None
        except _NETWORK_ERRORS as exc:
            logger.warning("Sign-in failed: {}", exc)
            if isinstance(exc, (asyncio.TimeoutError, TimeoutError, aiohttp.ServerTimeoutError)):
                return SignInStatus.TIMEOUT, None
            return SignInStatus.PORTAL_ERROR, None

    async def fetch_scores(
        self,
        session_token: str,
        *,
        attempts: int = 3,
    ) -> FetchScoresResult:
        headers = {**self._cfg.rustest_headers, "Cookie": f"Participant={session_token}"}

        for left in range(attempts, 0, -1):
            try:
                async with self._session().get(
                    self._cfg.rustest_scores_endpoint,
                    headers=headers,
                    proxy=self._cfg.proxy_url,
                ) as resp:
                    if resp.status in (401, 403):
                        logger.info("Scores unauthorized HTTP {}", resp.status)
                        return FetchScoresResult.unauthorized()

                    if resp.status != 200:
                        logger.warning("Scores HTTP {}", resp.status)
                        if left == 1:
                            return FetchScoresResult.portal_down()
                        await asyncio.sleep(1.5)
                        continue

                    data = await resp.json(content_type=None)
                    result = data.get("Result") if isinstance(data, dict) else None
                    if result is None:
                        logger.info("Scores response without Result — session invalid")
                        return FetchScoresResult.unauthorized()

                    raw_exams = result.get("Exams") if isinstance(result, dict) else None
                    if raw_exams is None:
                        logger.info("Scores response without Exams — session invalid")
                        return FetchScoresResult.unauthorized()

                    exams = [ExamScore.model_validate(item) for item in raw_exams]
                    if not exams:
                        return FetchScoresResult.empty()
                    return FetchScoresResult.ok(exams)
            except (*_NETWORK_ERRORS,) as exc:
                logger.warning("Scores fetch failed ({} tries left): {}", left - 1, exc)
                if left == 1:
                    return FetchScoresResult.portal_down()
                await asyncio.sleep(1.5)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Scores payload invalid: {}", exc)
                return FetchScoresResult.unauthorized()

        return FetchScoresResult.portal_down()
