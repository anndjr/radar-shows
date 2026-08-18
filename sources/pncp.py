"""
Coletor PNCP.

Duas rotas, porque nenhuma resolve sozinha:

1) /api/search/  -> endpoint que o proprio portal pncp.gov.br usa no front.
   TEM busca textual (`q`). Nao e documentado como dados abertos, pode mudar
   sem aviso. Usar para varredura por palavra-chave.

2) /api/consulta/v1/contratacoes/publicacao -> API oficial de dados abertos.
   NAO tem busca textual. Exige codigoModalidadeContratacao + intervalo de
   datas. Retorna tudo e VOCE filtra localmente. Usar para varredura
   exaustiva das modalidades 9 (Inexigibilidade) e 12 (Credenciamento).

Gotchas tratados aqui:
  - HTTP 204 (No Content) quando nao ha resultado -> nao e erro.
  - datas no formato yyyyMMdd (sem hifen) na API de consulta.
  - paginacao via totalPaginas / paginasRestantes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

import config
from models import Oportunidade

log = logging.getLogger("radar.pncp")

HEADERS = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def _f(v: Any) -> Optional[float]:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


async def _get(client: httpx.AsyncClient, url: str, params: Dict,
               tentativas: int = 4) -> Optional[Dict]:
    for i in range(tentativas):
        try:
            r = await client.get(url, params=params, headers=HEADERS)
            if r.status_code == 204:
                return None
            if r.status_code in (429, 500, 502, 503, 504):
                espera = 2 ** i
                log.warning("HTTP %s em %s - retry em %ss", r.status_code, url, espera)
                await asyncio.sleep(espera)
                continue
            r.raise_for_status()
            return r.json()
        except (httpx.TimeoutException, httpx.TransportError) as e:
            log.warning("rede falhou (%s) - tentativa %s/%s", e, i + 1, tentativas)
            await asyncio.sleep(2 ** i)
        except httpx.HTTPStatusError as e:
            log.error("HTTP %s em %s params=%s", e.response.status_code, url, params)
            return None
    return None


# ---------------------------------------------------------------------------
# 1) BUSCA FULL-TEXT (endpoint do portal)
# ---------------------------------------------------------------------------
def _map_search_item(it: Dict) -> Oportunidade:
    orgao = it.get("orgao_nome") or it.get("orgao") or ""
    return Oportunidade(
        fonte="pncp_search",
        id_externo=str(it.get("numero_controle_pncp") or it.get("id") or it.get("item_url", "")),
        titulo=it.get("title") or it.get("numero_controle_pncp", "") or "",
        objeto=it.get("description") or it.get("objeto") or it.get("title", "") or "",
        orgao=orgao,
        cnpj_orgao=str(it.get("orgao_cnpj") or ""),
        municipio=it.get("municipio_nome") or "",
        uf=it.get("uf") or it.get("uf_sigla") or "",
        modalidade=str(it.get("modalidade_licitacao_nome") or it.get("tipo_nome") or ""),
        valor_estimado=_f(it.get("valor_global") or it.get("valor")),
        data_publicacao=str(it.get("data_publicacao_pncp") or it.get("data") or ""),
        data_limite=str(it.get("data_fim_vigencia") or it.get("data_encerramento_proposta") or ""),
        link=("https://pncp.gov.br" + it["item_url"]) if it.get("item_url", "").startswith("/") else it.get("item_url", ""),
        raw=it,
    )


async def buscar_por_termo(
    client: httpx.AsyncClient,
    termo: str,
    tipos_documento: str = "edital",
    status: Optional[str] = "recebendo_proposta",
    paginas: int = 3,
    tam_pagina: int = 20,
) -> List[Oportunidade]:
    """Busca textual no PNCP. tipos_documento: edital | contrato | ata | pca."""
    out: List[Oportunidade] = []
    for pagina in range(1, paginas + 1):
        params = {
            "q": termo,
            "tipos_documento": tipos_documento,
            "ordenacao": "-data",
            "pagina": pagina,
            "tam_pagina": tam_pagina,
        }
        if status:
            params["status"] = status
        data = await _get(client, config.PNCP_SEARCH, params)
        if not data:
            break
        itens = data.get("items") or data.get("data") or []
        if not itens:
            break
        out.extend(_map_search_item(i) for i in itens)
        if len(itens) < tam_pagina:
            break
    log.info("search '%s' -> %s itens", termo, len(out))
    return out


# ---------------------------------------------------------------------------
# 2) API OFICIAL DE CONSULTA (varredura exaustiva por modalidade)
# ---------------------------------------------------------------------------
def _map_consulta_item(it: Dict) -> Oportunidade:
    org = it.get("orgaoEntidade") or {}
    uni = it.get("unidadeOrgao") or {}
    amp = it.get("amparoLegal") or {}
    ncp = it.get("numeroControlePNCP") or ""
    return Oportunidade(
        fonte="pncp",
        id_externo=str(ncp),
        titulo=f"{it.get('modalidadeNome','')} {it.get('numeroCompra','')}/{it.get('anoCompra','')}",
        objeto=it.get("objetoCompra") or "",
        orgao=org.get("razaoSocial") or "",
        cnpj_orgao=str(org.get("cnpj") or ""),
        municipio=uni.get("municipioNome") or "",
        uf=uni.get("ufSigla") or "",
        modalidade=it.get("modalidadeNome") or "",
        amparo_legal=" ".join(filter(None, [str(amp.get("nome") or ""), str(amp.get("descricao") or "")])),
        valor_estimado=_f(it.get("valorTotalEstimado")),
        data_publicacao=str(it.get("dataPublicacaoPncp") or ""),
        data_abertura=str(it.get("dataAberturaProposta") or ""),
        data_limite=str(it.get("dataEncerramentoProposta") or ""),
        link=f"https://pncp.gov.br/app/editais/{ncp.replace('-', '/')}" if ncp else "",
        link_origem=it.get("linkSistemaOrigem") or "",
        raw=it,
    )


async def consultar_contratacoes(
    client: httpx.AsyncClient,
    modalidade: int,
    data_inicial: date,
    data_final: date,
    uf: Optional[str] = None,
    max_paginas: int = 40,
) -> List[Oportunidade]:
    url = f"{config.PNCP_CONSULTA}/v1/contratacoes/publicacao"
    out: List[Oportunidade] = []
    pagina = 1
    while pagina <= max_paginas:
        params = {
            "dataInicial": _ymd(data_inicial),
            "dataFinal": _ymd(data_final),
            "codigoModalidadeContratacao": modalidade,
            "pagina": pagina,
            "tamanhoPagina": config.TAM_PAGINA,
        }
        if uf:
            params["uf"] = uf
        data = await _get(client, url, params)
        if not data:
            break
        itens = data.get("data") or []
        out.extend(_map_consulta_item(i) for i in itens)
        total_paginas = data.get("totalPaginas") or 1
        if pagina >= total_paginas or not itens:
            break
        pagina += 1
    log.info("consulta mod=%s uf=%s -> %s itens", modalidade, uf or "BR", len(out))
    return out


# ---------------------------------------------------------------------------
# orquestracao
# ---------------------------------------------------------------------------
async def coletar_pncp(dias: int = None) -> List[Oportunidade]:
    dias = dias or config.DIAS_JANELA
    hoje = date.today()
    inicio = hoje - timedelta(days=dias)
    sem = asyncio.Semaphore(config.CONCORRENCIA)
    resultados: List[Oportunidade] = []

    async with httpx.AsyncClient(timeout=config.TIMEOUT, follow_redirects=True) as client:

        async def _task(coro):
            async with sem:
                try:
                    return await coro
                except Exception as e:  # noqa: BLE001
                    log.exception("task falhou: %s", e)
                    return []

        tarefas = []
        # a) varredura exaustiva por modalidade (nacional; ou por UF se configurado)
        alvos_uf = config.UFS_FOCO or [None]
        for mod in config.MODALIDADES_ALVO:
            for uf in alvos_uf:
                tarefas.append(_task(consultar_contratacoes(client, mod, inicio, hoje, uf)))
        # b) varredura textual
        for termo in keywords_termos():
            tarefas.append(_task(buscar_por_termo(client, termo)))

        for bloco in await asyncio.gather(*tarefas):
            resultados.extend(bloco)

    return resultados


def keywords_termos():
    import keywords
    return keywords.TERMOS_BUSCA
