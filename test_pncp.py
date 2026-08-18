#!/usr/bin/env python3
"""
TESTE DE FUMACA - consulta o PNCP procurando "show" / "apresentacao musical".

Roda as duas rotas para voce ver na pratica qual entrega mais:

  ROTA 1  /api/search/                      -> busca textual
  ROTA 2  /api/consulta/v1/contratacoes/... -> modalidade 9 (Inexigibilidade)
                                               e 12 (Credenciamento), filtro local

    pip install httpx
    python test_pncp.py
    python test_pncp.py --dias 15 --uf SP
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx  # noqa: E402

import keywords  # noqa: E402
from classifier import triar  # noqa: E402
from sources import pncp  # noqa: E402

TERMOS = ["show", "apresentacao musical", "show musical", "apresentação musical"]


def linha(c="-", n=78):
    print(c * n)


def mostrar(op, i):
    print(f"\n[{i}] {op.categoria}  score={op.score}  alvo={op.genero_alvo}")
    print(f"    {op.municipio}/{op.uf} | {op.modalidade}")
    print(f"    {op.orgao[:70]}")
    print(f"    {op.objeto[:200]}")
    print(f"    valor={op.valor_estimado} limite={op.data_limite}")
    print(f"    {op.link or op.link_origem}")
    if op.hits.get("A"):
        print(f"    hits A: {op.hits['A'][:3]}")


async def rota_busca(client, args):
    linha("=")
    print("ROTA 1 - BUSCA TEXTUAL  (https://pncp.gov.br/api/search/)")
    linha("=")
    todos = []
    for termo in TERMOS:
        for status in ("recebendo_proposta", None):
            ops = await pncp.buscar_por_termo(
                client, termo, tipos_documento="edital",
                status=status, paginas=2, tam_pagina=20,
            )
            print(f"  q={termo!r:28} status={str(status):18} -> {len(ops)} itens")
            todos.extend(ops)
            if ops:
                break
    return todos


async def rota_consulta(client, args):
    linha("=")
    print("ROTA 2 - API OFICIAL DE CONSULTA (filtro local por keyword)")
    linha("=")
    hoje = date.today()
    inicio = hoje - timedelta(days=args.dias)
    todos = []
    for mod in (9, 12, 8):
        ops = await pncp.consultar_contratacoes(
            client, mod, inicio, hoje, uf=args.uf or None, max_paginas=args.max_paginas
        )
        artisticos = [o for o in ops if keywords.avaliar(o.texto_match())["hits"]["A"]]
        print(f"  modalidade {mod:>2} ({pncp.config.MODALIDADES.get(mod)}): "
              f"{len(ops):>5} contratacoes -> {len(artisticos)} com sinal artistico")
        todos.extend(ops)
    return todos


async def run(args):
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        # sanity check de conectividade
        try:
            r = await client.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao",
                                 params={"dataInicial": "20260101", "dataFinal": "20260102",
                                         "codigoModalidadeContratacao": 9,
                                         "pagina": 1, "tamanhoPagina": 1},
                                 headers=pncp.HEADERS)
            print(f"[ping] consulta -> HTTP {r.status_code} "
                  f"({len(r.content)} bytes)")
        except Exception as e:  # noqa: BLE001
            print(f"[ping] FALHOU: {e}")
            print("Verifique conexao/proxy. O PNCP as vezes bloqueia UA vazio.")
            return

        b1 = await rota_busca(client, args)
        b2 = await rota_consulta(client, args)

    brutos = b1 + b2
    linha("=")
    print(f"TOTAL BRUTO: {len(brutos)}")
    aprovadas = triar(brutos)
    print(f"APROVADAS PELO MOTOR DE FILTROS: {len(aprovadas)}")
    linha("=")
    for i, op in enumerate(aprovadas[:args.limite], 1):
        mostrar(op, i)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "teste_pncp_resultado.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump([o.to_dict() for o in aprovadas], f, ensure_ascii=False, indent=2)
    print(f"\nJSON completo -> {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dias", type=int, default=7)
    p.add_argument("--uf", type=str, default="")
    p.add_argument("--limite", type=int, default=15)
    p.add_argument("--max-paginas", type=int, default=10)
    asyncio.run(run(p.parse_args()))
