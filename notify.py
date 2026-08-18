import asyncio
import logging
from typing import List

import httpx

import config
from models import Oportunidade

log = logging.getLogger("radar.notify")

ICONES = {
    "INEXIGIBILIDADE_ART74": "\U0001F3AF",
    "CREDENCIAMENTO_ART79": "\U0001F4DD",
    "FOMENTO_CULTURAL": "\U0001F4B0",
    "EVENTO_MUNICIPAL": "\U0001F389",
    "DISPENSA": "\u26A1",
    "OUTRO_ARTISTICO": "\U0001F3B5",
    "OFICINA_AULA": "\U0001F3B8",
}


def _msg(op: Oportunidade) -> str:
    ico = ICONES.get(op.categoria, "\U0001F3B5")
    alvo = " \u2B50 SERTANEJO/AGRO" if op.genero_alvo else ""
    valor = (
        f"R$ {op.valor_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if op.valor_estimado else "n/d"
    )
    return (
        f"{ico} <b>{op.categoria}</b> (score {op.score}){alvo}\n"
        f"\U0001F4CD {op.municipio}/{op.uf}\n"
        f"\U0001F3DB {op.orgao[:120]}\n\n"
        f"{op.objeto[:600]}\n\n"
        f"\U0001F4B5 {valor}\n"
        f"\U0001F4CB {op.modalidade}\n"
        f"\u23F0 Limite: {op.data_limite or 'n/d'}\n"
        f"\U0001F517 {op.link or op.link_origem or 'sem link'}"
    )


async def telegram(ops: List[Oportunidade], limite: int = 20) -> None:
    if not (config.TELEGRAM_TOKEN and config.TELEGRAM_CHAT_ID):
        log.info("Telegram nao configurado - pulando")
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient(timeout=30) as c:
        for op in ops[:limite]:
            try:
                r = await c.post(url, json={
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": _msg(op),
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                })
                if r.status_code != 200:
                    log.warning("telegram %s: %s", r.status_code, r.text[:200])
            except Exception as e:  # noqa: BLE001
                log.warning("telegram falhou: %s", e)
            await asyncio.sleep(1.2)  # respeita rate limit do Bot API


async def webhook(ops: List[Oportunidade]) -> None:
    if not config.WEBHOOK_URL:
        return
    async with httpx.AsyncClient(timeout=30) as c:
        try:
            await c.post(config.WEBHOOK_URL,
                         json={"oportunidades": [o.to_dict() for o in ops]})
        except Exception as e:  # noqa: BLE001
            log.warning("webhook falhou: %s", e)


async def disparar(ops: List[Oportunidade]) -> None:
    await asyncio.gather(telegram(ops), webhook(ops))
