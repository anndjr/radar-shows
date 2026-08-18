"""
Motor de palavras-chave / regex para triagem de oportunidades artisticas.

REGRA DE OURO: todo texto passa por `norm()` antes do match (minusculas + sem
acento). Portanto os padroes abaixo NAO devem conter acentos.

Pesos: quanto maior, mais forte o sinal. O score final e a soma dos hits
(cada padrao conta uma vez, nao importa quantas ocorrencias).
"""

import re
import unicodedata
from typing import Dict, List, Tuple


def norm(texto: str) -> str:
    """minusculas, sem acento, espacos colapsados."""
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[\u2018\u2019\u201c\u201d]", '"', s)
    return re.sub(r"\s+", " ", s).strip()


def _c(patterns: List[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns]


# ---------------------------------------------------------------------------
# TIER A - Sinal artistico forte. Sem pelo menos 1 hit aqui, nada e aprovado.
# ---------------------------------------------------------------------------
TIER_A = _c([
    r"\bapresentac(ao|oes) (artistica|artisticas|musical|musicais|de banda)",
    r"\bshow(s)? (musical|musicais|artistico|artisticos|de|com)\b",
    r"\bshow(s)? (pirotecnico|de fogos)",  # capturado aqui e barrado no negativo
    r"\bespetaculo (musical|artistico)",
    r"\bapresentacao de (show|banda|dupla|artista|cantor)",
    r"\bcache(s)? (artistico|artisticos|de artista|musical)",
    r"\bcontratac(ao|oes) (de |da |do )?(banda|artista|cantor|cantora|dupla|grupo musical|atracao|atracoes|show)",
    r"\bbanda(s)? (musical|musicais|de baile|sertaneja|sertanejas)\b",
    r"\bdupla(s)? sertaneja(s)?\b",
    r"\bgrupo(s)? (musical|musicais|artistico|artisticos)\b",
    r"\batrac(ao|oes) (artistica|artisticas|musical|musicais|nacional|nacionais|regional|regionais)",
    r"\bcredenciamento (de |para )?(artistas?|musicos?|bandas?|artistico|cultural|de grupos)",
    r"\bservico(s)? (artistico|artisticos|de sonorizacao artistica)",
    r"\bservico(s)? de apresentac(ao|oes) (artistica|musical)",
    r"\bapresentacao de (musica|musicas) ao vivo",
    r"\bmusica ao vivo\b",
    r"\bartista(s)? (local|locais|regional|regionais|nacional|nacionais|consagrado|consagrados)",
    r"\bexclusividade (artistica|do artista|de representacao)",
    r"\bempresario exclusivo\b",
    r"\bcarta de exclusividade\b",
    r"\bshow(s)?\b.{0,40}\b(sertanej|forro|pagode|gospel|axe|piseiro|arrocha)",
    r"\b(sertanej|forro|piseiro|arrocha|moda de viola|musica de raiz)\w*\b",
    r"\bapresentacao de (dj|djs)\b",
    r"\bpalco.{0,20}\bartista",  # "artistas que subirao ao palco"
])

# ---------------------------------------------------------------------------
# TIER B - Contexto de evento. Reforca, mas nao aprova sozinho.
# ---------------------------------------------------------------------------
TIER_B = _c([
    r"\bfesta do peao(de boiadeiro)?\b",
    r"\brodeio(s)?\b",
    r"\bcavalgada\b",
    r"\bexposic(ao|oes) agropecuaria\b",
    r"\bexpo(show|feira|agro|fest)\w*\b",
    r"\baniversario (do |de |da )?(municipio|cidade|emancipacao)",
    r"\bfestividade(s)?\b",
    r"\bfesta(s)? (junina|juninas|julina|de padroeir|do padroeir|tradicional|tradicionais|popular)",
    r"\barraia\w*\b|\bquermesse\b|\bmicareta\b",
    r"\bcarnaval\b|\breveillon\b|\bvirada do ano\b",
    r"\bfestival (de |da |do )?(musica|cultura|inverno|verao|sertanejo)",
    r"\bcircuito cultural\b|\bcirculacao (artistica|cultural)\b",
    r"\bevento(s)? (cultural|culturais|festivo|festivos)\b",
    r"\bcalendario (de eventos|oficial de eventos)\b",
    r"\bfeira (agropecuaria|cultural|do produtor)\b",
    r"\bsemana (do municipio|cultural)\b",
])

# ---------------------------------------------------------------------------
# TIER C - Fomento / edital de cultura (PNAB, LPG, leis de incentivo)
# ---------------------------------------------------------------------------
TIER_C_FOMENTO = _c([
    r"\bpnab\b|\bpolitica nacional aldir blanc\b",
    r"\baldir blanc\b",
    r"\b(lei )?paulo gustavo\b|\bl\.?p\.?g\.?\b",
    r"\bedital de fomento\b|\bfomento (cultural|a cultura|as artes)\b",
    r"\blei (de )?incentivo (a )?(cultura|cultural)\b",
    r"\bchamamento publico\b.{0,60}\b(cultur|artist|music)",
    r"\bpremiac(ao|oes)\b.{0,40}\b(cultur|artist|music)",
    r"\bapoio (a projetos|a iniciativas) (cultura|culturais|artisticos)",
    r"\bmecenato\b|\brouanet\b|\bproac\b|\bfundo (municipal|estadual) de cultura\b",
    r"\binscric(ao|oes) de projetos (cultura|culturais|artisticos)",
])

# ---------------------------------------------------------------------------
# NEGATIVOS - so barram quando NAO ha hit em TIER_A (ver classifier.py).
# Evita jogar fora lote misto ("contratacao de banda e locacao de som").
# ---------------------------------------------------------------------------
NEGATIVOS = _c([
    r"\bbanda larga\b|\blink de internet\b|\bbanda de frequencia\b",
    r"\bloca(cao|coes)? (de |do |da )?(palco|som|sonorizacao|iluminacao|tenda|tendas|"
    r"gerador|arquibancada|banheiro quimico|estrutura|grade|gradil|toldo|praticavel|"
    r"telao|painel de led|camarim|stand|container)",
    r"\bmontagem e desmontagem\b",
    r"\bestrutura(s)? (metalica|metalicas|para eventos|de palco)\b",
    r"\bseguranca (patrimonial|desarmada|armada|privada)\b",
    r"\bbrigadista\b|\bbombeiro civil\b|\bambulancia\b|\bposto medico\b",
    r"\balimenta(cao|coes)\b|\bbuffet\b|\bcoffee break\b|\bagua mineral\b|\bmarmita\b",
    r"\bmaterial (de expediente|escolar|de limpeza|permanente|grafico)\b",
    r"\blimpeza (urbana|predial)\b|\bcoleta de residuos\b",
    r"\bloca(cao|coes)? de veiculo\b|\btransporte escolar\b|\bfretamento\b",
    r"\bcombustivel\b|\bpneu(s)?\b|\bpeca(s)? automotiva",
    r"\buniforme(s)?\b|\bcamiseta(s)?\b|\btrofeu(s)?\b|\bmedalha(s)?\b",
    r"\bfogos de artificio\b|\bpirotecnic\w*\b",
    r"\bdivulgacao\b.{0,20}\b(carro de som|radio)\b",
    r"\bcarro de som\b",
    r"\bcredenciamento (de |para )?(leiloeiro|instituicao financeira|clinica|"
    r"laboratorio|medico|oficina mecanica|hotel|hospital|profissionais de saude)",
    r"\bbanda de musica (municipal|escolar)\b.{0,30}\b(instrumento|manutencao|reparo)",
    r"\bmanutencao\b|\breforma\b|\bpavimentacao\b|\bobra(s)?\b",
    r"\bpalco\b.{0,15}\bloca",
])

# ---------------------------------------------------------------------------
# SUBTIPOS - classificacao da natureza da oportunidade
# ---------------------------------------------------------------------------
CAT_INEXIGIBILIDADE = _c([
    r"\binexigibilidade\b",
    r"\bart(igo)?\.? ?74\b",
    r"\binciso ii\b.{0,30}\b74\b",
    r"\b74[^\d]{0,6}ii\b",
    r"\bexclusividade\b",
])
CAT_CREDENCIAMENTO = _c([
    r"\bcredenciamento\b",
    r"\bart(igo)?\.? ?79\b",
    r"\bpre-?qualificacao\b",
])
CAT_DISPENSA = _c([r"\bdispensa (de licitacao|eletronica)?\b", r"\bart(igo)?\.? ?75\b"])
CAT_OFICINA = _c([
    r"\boficina(s)? (de musica|musical|artistica|de violao)",
    r"\baula(s)? de musica\b|\bprofessor de musica\b|\bmonitor(ia)? cultural\b",
])

# Genero-alvo (nao filtra, apenas pontua prioridade)
GENERO_ALVO = _c([
    r"\bsertanej\w*\b", r"\bdupla sertaneja\b", r"\bmoda de viola\b",
    r"\bmusica de raiz\b", r"\bcaipira\b", r"\bpiseiro\b", r"\bforro\b",
    r"\bagro\w*\b", r"\brodeio\b", r"\bfesta do peao\b",
])

PESOS = {"A": 12, "B": 4, "C": 9, "NEG": -10, "GENERO": 6}


def _hits(texto: str, patterns: List[re.Pattern]) -> List[str]:
    return [p.pattern for p in patterns if p.search(texto)]


def avaliar(texto_bruto: str) -> Dict:
    """Retorna dict com score, hits por tier e categoria sugerida."""
    t = norm(texto_bruto)
    a, b, c = _hits(t, TIER_A), _hits(t, TIER_B), _hits(t, TIER_C_FOMENTO)
    neg = _hits(t, NEGATIVOS)
    gen = _hits(t, GENERO_ALVO)

    score = (
        len(a) * PESOS["A"]
        + len(b) * PESOS["B"]
        + len(c) * PESOS["C"]
        + (PESOS["GENERO"] if gen else 0)
    )
    # Negativo pesa sempre, mas so e fatal se nao houver Tier A nem Tier C.
    if neg:
        score += len(neg) * PESOS["NEG"]

    tem_sinal_forte = bool(a) or bool(c)
    aprovado = tem_sinal_forte and score >= 10

    if _hits(t, CAT_INEXIGIBILIDADE) and tem_sinal_forte:
        categoria = "INEXIGIBILIDADE_ART74"
    elif _hits(t, CAT_CREDENCIAMENTO) and tem_sinal_forte:
        categoria = "CREDENCIAMENTO_ART79"
    elif c:
        categoria = "FOMENTO_CULTURAL"
    elif _hits(t, CAT_OFICINA):
        categoria = "OFICINA_AULA"
    elif _hits(t, CAT_DISPENSA) and tem_sinal_forte:
        categoria = "DISPENSA"
    elif b and a:
        categoria = "EVENTO_MUNICIPAL"
    else:
        categoria = "OUTRO_ARTISTICO" if tem_sinal_forte else "DESCARTADO"

    return {
        "score": score,
        "aprovado": aprovado,
        "categoria": categoria,
        "genero_alvo": bool(gen),
        "hits": {"A": a, "B": b, "C": c, "NEG": neg},
    }


# Termos usados nas buscas full-text (PNCP /api/search e Querido Diario).
# Curtos de proposito: a API de busca nao gosta de frase longa.
TERMOS_BUSCA: Tuple[str, ...] = (
    "show musical",
    "apresentacao artistica",
    "apresentacao musical",
    "banda musical",
    "credenciamento de artistas",
    "cache artistico",
    "atracao musical",
    "dupla sertaneja",
    "festa do peao",
    "evento cultural",
    "chamamento publico cultural",
    "fomento cultural",
)
