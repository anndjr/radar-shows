from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Oportunidade:
    """Formato canonico. Toda fonte deve produzir isto."""

    fonte: str                       # "pncp" | "querido_diario" | "compras_gov"
    id_externo: str                  # numeroControlePNCP, id da gazette, etc.
    titulo: str
    objeto: str                      # descricao completa (base do match)
    orgao: str = ""
    cnpj_orgao: str = ""
    municipio: str = ""
    uf: str = ""
    modalidade: str = ""
    amparo_legal: str = ""
    valor_estimado: Optional[float] = None
    data_publicacao: str = ""        # ISO-8601
    data_abertura: str = ""
    data_limite: str = ""            # encerramento de propostas / inscricoes
    link: str = ""
    link_origem: str = ""

    # preenchido pelo classifier
    score: int = 0
    categoria: str = ""
    genero_alvo: bool = False
    hits: Dict[str, List[str]] = field(default_factory=dict)
    trecho: str = ""                 # excerto que casou (util para diarios)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def uid(self) -> str:
        base = f"{self.fonte}:{self.id_externo}"
        return hashlib.sha1(base.encode()).hexdigest()[:16]

    def texto_match(self) -> str:
        return " \n ".join(
            filter(None, [self.titulo, self.objeto, self.modalidade,
                          self.amparo_legal, self.trecho])
        )

    def to_dict(self, incluir_raw: bool = False) -> Dict[str, Any]:
        d = asdict(self)
        d["uid"] = self.uid
        if not incluir_raw:
            d.pop("raw", None)
        return d

    def to_json(self, **kw) -> str:
        return json.dumps(self.to_dict(**kw), ensure_ascii=False, indent=2)

    def resumo_alerta(self) -> str:
        v = (
            f"R$ {self.valor_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if self.valor_estimado else "nao informado"
        )
        estrela = "*" if self.genero_alvo else ""
        return (
            f"{estrela}[{self.categoria}] score {self.score}\n"
            f"{self.municipio}/{self.uf} - {self.orgao}\n"
            f"{self.objeto[:280]}\n"
            f"Valor: {v} | Modalidade: {self.modalidade}\n"
            f"Limite: {self.data_limite or 'n/d'}\n"
            f"{self.link or self.link_origem}"
        )
