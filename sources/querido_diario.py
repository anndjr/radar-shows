"""
Coletor Querido Diario (Open Knowledge Brasil).

API: https://queridodiario.ok.org.br/api/gazettes
  querystring, published_since (YYYY-MM-DD), published_until,
  territory_ids (IBGE, repetivel), size, offset, sort_by, excerpt_size

LIMITE REAL: o QD nao cobre os 5.570 municipios. A cobertura e parcial
(alguns milhares de diarios, concentrados em capitais e cidades medias, e
varios com raspagem intermitente). Trate como fonte COMPLEMENTAR ao PNCP,
nao como fonte primaria. Para inexigibilidade de show em cidade pequena,
o PNCP e mais confiavel porque a publicacao la e obrigatoria por lei.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

import httpx

import config
from models import Oportunidade

log = logging.getLogger("radar.qd")
HEADERS = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}


def _map(g: Dict) -> Oportunidade:
    excerto = " ".join(g.get("excerpts") or [])[:4000]
    return Oportunidade(
        fonte="querido_diario",
        id_externo=str(g.get("file_checksum") or g.get("txt_url") or g.get("url")),
        titulo=f"DOM {g.get('territory_name','')}/{g.get('state_code','')} {g.get('date','')}",
        objeto=excerto,
        trecho=excerto,
        municipio=g.get("territory_name") or "",
        uf=g.get("state_code") or "",
        orgao=g.get("territory_name") or "",
        data_publicacao=str(g.get("date") or ""),
        link=g.get("url") or g.get("txt_url") or "",
        raw={k: v for k, v in g.items() if k != "excerpts"},
    )


async def buscar_diarios(
    client: httpx.AsyncClient,
    termo: str,
    desde: date,
    ate: date,
    territory_ids: Optional[List[str]] = None,
    size: int = 50,
) -> List[Oportunidade]:
    params = {
        "querystring": f'"{termo}"',
        "published_since": desde.isoformat(),
        "published_until": ate.isoformat(),
        "size": size,
        "offset": 0,
        "sort_by": "descending_date",
        "excerpt_size": 700,
        "number_of_excerpts": 3,
    }
    if territory_ids:
        params["territory_ids"] = territory_ids
    try:
        r = await client.get(f"{config.QD_API}/gazettes", params=params, headers=HEADERS)
        if r.status_code == 204:
            return []
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001
        log.warning("QD falhou para '%s': %s", termo, e)
        return []
    itens = data.get("gazettes") or []
    log.info("QD '%s' -> %s diarios", termo, len(itens))
    return [_map(g) for g in itens]


async def coletar_qd(dias: int = None, termos: Optional[List[str]] = None) -> List[Oportunidade]:
    import keywords

    dias = dias or config.DIAS_JANELA
    ate = date.today()
    desde = ate - timedelta(days=max(dias, 7))
    termos = termos or [
        "inexigibilidade apresentacao artistica",
        "credenciamento de artistas",
        "show musical",
        "cache artistico",
        "chamamento publico cultural",
    ]
    sem = asyncio.Semaphore(config.CONCORRENCIA)
    out: List[Oportunidade] = []

    async with httpx.AsyncClient(timeout=config.TIMEOUT, follow_redirects=True) as client:
        async def _t(termo):
            async with sem:
                return await buscar_diarios(client, termo, desde, ate)

        for bloco in await asyncio.gather(*[_t(t) for t in termos]):
            out.extend(bloco)
    return out
