#!/usr/bin/env python3
"""
Radar de Shows - pipeline completo.

Uso:
    python main.py                      # ciclo completo (PNCP + Querido Diario)
    python main.py --dias 7             # janela de 7 dias
    python main.py --sem-qd             # so PNCP
    python main.py --sem-alerta         # nao dispara Telegram
    python main.py --uf SP,MG,GO
"""

import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources"))

import config  # noqa: E402
import store  # noqa: E402
from classifier import triar  # noqa: E402
from sources import pncp, querido_diario  # noqa: E402
import notify  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("radar")


async def ciclo(dias: int, usar_qd: bool, alertar: bool, score_min: int):
    log.info("=== coleta iniciada (janela=%s dias) ===", dias)

    tarefas = [pncp.coletar_pncp(dias)]
    if usar_qd:
        tarefas.append(querido_diario.coletar_qd(dias))

    blocos = await asyncio.gather(*tarefas, return_exceptions=True)
    brutos = []
    for b in blocos:
        if isinstance(b, Exception):
            log.error("fonte falhou: %s", b)
        else:
            brutos.extend(b)
    log.info("brutos coletados: %s", len(brutos))

    aprovadas = triar(brutos, score_minimo=score_min)
    log.info("aprovadas pelo filtro: %s", len(aprovadas))

    novas = store.filtrar_novas(aprovadas)
    log.info("novas (nao alertadas antes): %s", len(novas))

    payload = {
        "gerado_em": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "total_brutos": len(brutos),
        "total_aprovados": len(aprovadas),
        "total_novos": len(novas),
        "oportunidades": [o.to_dict() for o in novas],
    }
    config.JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("JSON salvo em %s", config.JSON_OUT)

    if alertar and novas:
        await notify.disparar(novas)
    store.salvar(novas, alertado=alertar)

    # resumo no terminal
    for o in novas[:25]:
        print("-" * 78)
        print(o.resumo_alerta())
    return novas


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dias", type=int, default=config.DIAS_JANELA)
    p.add_argument("--sem-qd", action="store_true")
    p.add_argument("--sem-alerta", action="store_true")
    p.add_argument("--score-min", type=int, default=config.SCORE_MINIMO)
    p.add_argument("--uf", type=str, default="")
    a = p.parse_args()

    if a.uf:
        config.UFS_FOCO = [u.strip().upper() for u in a.uf.split(",") if u.strip()]

    asyncio.run(ciclo(a.dias, not a.sem_qd, not a.sem_alerta, a.score_min))


if __name__ == "__main__":
    main()
