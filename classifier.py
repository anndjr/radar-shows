from typing import Iterable, List

import keywords
from config import SCORE_MINIMO
from models import Oportunidade


def classificar(op: Oportunidade) -> Oportunidade:
    r = keywords.avaliar(op.texto_match())
    op.score = r["score"]
    op.categoria = r["categoria"]
    op.genero_alvo = r["genero_alvo"]
    op.hits = r["hits"]
    return op


def triar(ops: Iterable[Oportunidade], score_minimo: int = SCORE_MINIMO) -> List[Oportunidade]:
    """Classifica, descarta falsos positivos e ordena por relevancia."""
    aprovadas = []
    for op in ops:
        classificar(op)
        tem_forte = bool(op.hits.get("A")) or bool(op.hits.get("C"))
        if tem_forte and op.score >= score_minimo:
            aprovadas.append(op)

    prioridade = {
        "INEXIGIBILIDADE_ART74": 0,
        "CREDENCIAMENTO_ART79": 1,
        "FOMENTO_CULTURAL": 2,
        "EVENTO_MUNICIPAL": 3,
        "DISPENSA": 4,
        "OUTRO_ARTISTICO": 5,
        "OFICINA_AULA": 6,
    }
    aprovadas.sort(
        key=lambda o: (prioridade.get(o.categoria, 9), -int(o.genero_alvo), -o.score)
    )
    return aprovadas
