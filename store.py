import json
import sqlite3
from datetime import datetime
from typing import Iterable, List

from config import DB_PATH
from models import Oportunidade

SCHEMA = """
CREATE TABLE IF NOT EXISTS oportunidades (
    uid TEXT PRIMARY KEY,
    fonte TEXT, id_externo TEXT, categoria TEXT, score INTEGER,
    municipio TEXT, uf TEXT, orgao TEXT, objeto TEXT,
    valor_estimado REAL, data_publicacao TEXT, data_limite TEXT,
    link TEXT, genero_alvo INTEGER,
    alertado_em TEXT, visto_em TEXT, payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_cat ON oportunidades(categoria);
CREATE INDEX IF NOT EXISTS idx_uf ON oportunidades(uf);
CREATE INDEX IF NOT EXISTS idx_pub ON oportunidades(data_publicacao);
"""


def conn():
    c = sqlite3.connect(DB_PATH)
    c.executescript(SCHEMA)
    return c


def filtrar_novas(ops: Iterable[Oportunidade]) -> List[Oportunidade]:
    """Remove duplicatas internas e o que ja foi alertado antes."""
    c = conn()
    vistos_lote = set()
    novas = []
    for op in ops:
        if op.uid in vistos_lote:
            continue
        vistos_lote.add(op.uid)
        row = c.execute("SELECT 1 FROM oportunidades WHERE uid=?", (op.uid,)).fetchone()
        if row:
            continue
        novas.append(op)
    c.close()
    return novas


def salvar(ops: Iterable[Oportunidade], alertado: bool = False) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    c = conn()
    with c:
        for op in ops:
            c.execute(
                """INSERT OR REPLACE INTO oportunidades
                   (uid,fonte,id_externo,categoria,score,municipio,uf,orgao,objeto,
                    valor_estimado,data_publicacao,data_limite,link,genero_alvo,
                    alertado_em,visto_em,payload)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (op.uid, op.fonte, op.id_externo, op.categoria, op.score,
                 op.municipio, op.uf, op.orgao, op.objeto[:4000],
                 op.valor_estimado, op.data_publicacao, op.data_limite, op.link,
                 int(op.genero_alvo), agora if alertado else None, agora,
                 json.dumps(op.to_dict(), ensure_ascii=False)),
            )
    c.close()
