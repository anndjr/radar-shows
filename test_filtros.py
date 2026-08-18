#!/usr/bin/env python3
"""
Teste OFFLINE do motor de filtros (nao precisa de internet nem httpx).
Roda com: python test_filtros.py
Se algum caso falhar, ele imprime e sai com codigo 1.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keywords  # noqa: E402

# (texto, deve_aprovar, categoria_esperada_ou_None)
CASOS = [
    # --- devem passar ---
    ("Inexigibilidade de licitacao para contratacao de show musical da dupla sertaneja "
     "Zé e Zico para a Festa do Peao de Boiadeiro, com fundamento no art. 74, II da Lei 14.133/2021",
     True, "INEXIGIBILIDADE_ART74"),
    ("Edital de Credenciamento de artistas e grupos musicais locais para apresentacoes "
     "artisticas no Circuito Cultural Municipal, art. 79 da Lei 14.133/21",
     True, "CREDENCIAMENTO_ART79"),
    ("Chamamento publico para selecao de projetos culturais - PNAB / Lei Aldir Blanc, "
     "fomento a musica",
     True, "FOMENTO_CULTURAL"),
    ("Contratacao de atracoes musicais nacionais para o aniversario do municipio e "
     "Exposicao Agropecuaria 2026", True, None),
    ("Contratacao de banda musical para apresentacao de musica ao vivo na Festa Junina", True, None),
    ("Aviso de inexigibilidade - cache artistico do cantor sertanejo, carta de exclusividade "
     "do empresario exclusivo", True, "INEXIGIBILIDADE_ART74"),
    # lote misto: tem palco/som MAS tambem tem artista -> nao pode ser descartado
    ("Contratacao de show musical e locacao de palco, som e iluminacao para o Reveillon",
     True, None),

    # --- devem ser descartados ---
    ("Locacao de palco, sonorizacao e iluminacao para eventos do calendario oficial", False, None),
    ("Contratacao de servico de seguranca desarmada e brigadistas para a Festa do Peao", False, None),
    ("Aquisicao de link de internet banda larga para as escolas municipais", False, None),
    ("Credenciamento de instituicoes financeiras para consignacao em folha", False, None),
    ("Locacao de banheiro quimico e tendas para exposicao agropecuaria", False, None),
    ("Aquisicao de fogos de artificio para o reveillon municipal", False, None),
    ("Contratacao de empresa para fornecimento de alimentacao e coffee break no evento cultural",
     False, None),
    ("Credenciamento de oficinas mecanicas para manutencao da frota", False, None),
]


def main():
    falhas = 0
    print(f"{'ok':>3} {'score':>6} {'categoria':<24} texto")
    print("-" * 100)
    for texto, esperado, cat_esp in CASOS:
        r = keywords.avaliar(texto)
        aprovado = r["aprovado"]
        ok = aprovado == esperado and (cat_esp is None or r["categoria"] == cat_esp)
        if not ok:
            falhas += 1
        print(f"{'PASS' if ok else 'FAIL':>4} {r['score']:>6} {r['categoria']:<24} {texto[:60]}")
        if not ok:
            print(f"      -> esperado aprovar={esperado} cat={cat_esp}; "
                  f"obtido aprovar={aprovado} cat={r['categoria']}")
            print(f"      -> hits: A={len(r['hits']['A'])} B={len(r['hits']['B'])} "
                  f"C={len(r['hits']['C'])} NEG={len(r['hits']['NEG'])}")
    print("-" * 100)
    print(f"{len(CASOS) - falhas}/{len(CASOS)} casos ok")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
