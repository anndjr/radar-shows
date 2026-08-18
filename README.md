# Radar de Shows — monitor de contratações artísticas públicas (Brasil)

Monitora, filtra e classifica oportunidades de contratação de shows ao vivo e projetos
musicais em todo o território nacional, com foco em sertanejo/agro.

---

## 1. Duas correções importantes no plano original

**(a) A API oficial do PNCP não tem busca por palavra-chave.**
O endpoint de dados abertos (`/api/consulta/v1/contratacoes/publicacao`) exige
`codigoModalidadeContratacao` + intervalo de datas e devolve *tudo*. Não existe
parâmetro `q`. Quem faz busca textual é o endpoint que o próprio portal usa no
front-end: `https://pncp.gov.br/api/search/?q=...`. Ele é público mas **não é
contrato estável** — pode mudar de schema sem aviso.

Por isso o coletor usa **as duas rotas**:

| Rota | Para quê | Risco |
|---|---|---|
| `/api/search/?q=` | descoberta rápida por palavra-chave | schema instável |
| `/api/consulta/v1/contratacoes/publicacao` | varredura exaustiva das modalidades 9 e 12, filtro local | volume alto, mas confiável |

A rota 2 é a que garante cobertura: **modalidade 9 = Inexigibilidade** e
**12 = Credenciamento** são exatamente o seu alvo, e o volume nacional dessas duas
por dia é perfeitamente processável.

**(b) Querido Diário não cobre o Brasil.**
A cobertura é parcial (alguns milhares de diários, concentrados em capitais e cidades
médias, com raspagem intermitente). Para inexigibilidade de show em cidade de 8 mil
habitantes, o **PNCP é mais confiável** — a publicação lá é obrigação legal desde 2023.
Trate o QD como fonte complementar de contexto, não como primária.

**Sobre BEC/SP, Compras.gov.br e portais estaduais:** todos alimentam o PNCP por
obrigação legal. Fazer scraping deles no MVP é trabalho duplicado com alto custo de
manutenção. Só vale a pena depois, e só para capturar o **anexo do edital em PDF**
(que às vezes tem detalhe de cachê que não está no objeto resumido).

---

## 2. Arquitetura

```
                   ┌─────────────────────────────────────┐
   AGENDADOR       │  cron / systemd timer / GH Actions  │  2x/dia
   (scheduler)     └──────────────┬──────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
 ┌──────────────┐        ┌─────────────────┐       ┌────────────────┐
 │ PNCP search  │        │ PNCP consulta   │       │ Querido Diário │
 │ (full-text)  │        │ mod 9,12,8,3,10 │       │ (complementar) │
 └──────┬───────┘        └────────┬────────┘       └───────┬────────┘
        └────────────────┬────────┴────────────────────────┘
                         ▼
              ┌────────────────────────┐
              │  NORMALIZAÇÃO          │  models.Oportunidade
              │  (schema canônico)     │  todas as fontes → 1 formato
              └──────────┬─────────────┘
                         ▼
              ┌────────────────────────┐
              │  MOTOR DE FILTROS      │  keywords.py
              │  Tier A / B / C / NEG  │  score + categoria
              └──────────┬─────────────┘
                         ▼
              ┌────────────────────────┐
              │  DEDUPE + PERSISTÊNCIA │  store.py (SQLite)
              │  uid = sha1(fonte:id)  │  não realerta
              └──────────┬─────────────┘
                         ├──────────────► data/oportunidades.json
                         ▼
              ┌────────────────────────┐
              │  ALERTAS               │  notify.py
              │  Telegram / Webhook    │
              └────────────────────────┘
```

### Lógica do motor de filtros (o coração do sistema)

Todo texto passa por `norm()` → minúsculas, sem acento. Os padrões regex não têm acento.

- **Tier A** (peso 12) — sinal artístico forte: `apresentação artística`, `show musical`,
  `cachê artístico`, `dupla sertaneja`, `credenciamento de artistas`, `carta de
  exclusividade`, `empresário exclusivo`…
- **Tier B** (peso 4) — contexto de evento: `festa do peão`, `rodeio`, `exposição
  agropecuária`, `aniversário do município`, `réveillon`, `arraiá`…
- **Tier C** (peso 9) — fomento: `PNAB`, `Aldir Blanc`, `Paulo Gustavo`, `edital de
  fomento`, `chamamento público cultural`…
- **Gênero-alvo** (bônus 6) — `sertanejo`, `moda de viola`, `piseiro`, `rodeio`, `agro`
- **Negativos** (−10) — palco, som, iluminação, tenda, gerador, segurança, alimentação,
  banda **larga**, fogos, credenciamento de oficina mecânica/instituição financeira…

**Regra de ouro que evita o erro mais comum:** o negativo **não descarta sozinho**.
Um objeto do tipo *"contratação de show musical e locação de palco e som"* é um lote
misto e continua sendo oportunidade. O descarte só acontece quando **não há nenhum
hit de Tier A nem de Tier C**. Isso está coberto no `test_filtros.py`.

Categorias de saída: `INEXIGIBILIDADE_ART74`, `CREDENCIAMENTO_ART79`,
`FOMENTO_CULTURAL`, `EVENTO_MUNICIPAL`, `DISPENSA`, `OFICINA_AULA`, `OUTRO_ARTISTICO`.

---

## 3. Instalação

```bash
pip install httpx
cd radar
python test_filtros.py     # valida o motor offline — deve dar 15/15
python test_pncp.py        # bate na API de verdade
```

Variáveis de ambiente (todas opcionais):

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="-1001234567890"
export RADAR_UFS="SP,MG,GO,MS,MT,PR"   # vazio = Brasil inteiro
export RADAR_DIAS=3
export RADAR_SCORE_MIN=10
```

Execução:

```bash
python main.py                    # ciclo completo
python main.py --dias 15 --uf SP  # janela maior, só SP
python main.py --sem-alerta       # dry run
```

Agendamento (cron, 2x/dia):

```cron
0 8,18 * * * cd /caminho/radar && /usr/bin/python3 main.py >> data/radar.log 2>&1
```

---

## 4. Arquivos

| Arquivo | Papel |
|---|---|
| `keywords.py` | motor de regex — **onde você vai mexer 90% do tempo** |
| `config.py` | endpoints, modalidades, UFs, credenciais via env |
| `models.py` | `Oportunidade` — schema canônico + `to_json()` + `uid` |
| `classifier.py` | aplica o motor, triagem e ordenação por prioridade |
| `sources/pncp.py` | cliente async das 2 rotas do PNCP |
| `sources/querido_diario.py` | cliente do QD |
| `store.py` | SQLite: dedupe e histórico |
| `notify.py` | Telegram (HTML) + webhook genérico |
| `main.py` | orquestração / CLI |
| `test_pncp.py` | teste de fumaça contra a API real |
| `test_filtros.py` | 15 casos, inclui falsos positivos clássicos |

---

## 5. JSON de saída

```json
{
  "gerado_em": "2026-08-18T09:12:00",
  "total_brutos": 3184,
  "total_aprovados": 46,
  "total_novos": 11,
  "oportunidades": [
    {
      "uid": "a1b2c3d4e5f60718",
      "fonte": "pncp",
      "id_externo": "12345678000199-1-000123/2026",
      "categoria": "INEXIGIBILIDADE_ART74",
      "score": 58,
      "genero_alvo": true,
      "municipio": "Barretos", "uf": "SP",
      "orgao": "PREFEITURA MUNICIPAL DE ...",
      "objeto": "Contratação de show musical ...",
      "valor_estimado": 150000.0,
      "modalidade": "Inexigibilidade",
      "amparo_legal": "Lei 14.133/2021, Art. 74, II",
      "data_publicacao": "2026-08-17",
      "data_limite": "",
      "link": "https://pncp.gov.br/app/editais/...",
      "hits": { "A": ["..."], "B": ["..."], "C": [], "NEG": [] }
    }
  ]
}
```

---

## 6. Ajuste fino (primeira semana)

1. Rode `python main.py --dias 30 --sem-alerta --score-min 0`.
2. Abra `data/oportunidades.json`, ordene por score e leia os 100 primeiros.
3. Todo falso positivo que passar → adicione o padrão em `NEGATIVOS`.
4. Toda oportunidade real que ficou com score baixo → veja qual Tier A faltou e
   adicione o padrão.
5. Depois de ~2 semanas de curadoria, você tem base rotulada suficiente para trocar
   o score por um classificador (`scikit-learn` + TF-IDF, ou embeddings). **Não comece
   por ML** — regex bem feito resolve 90% e é auditável.

## 7. Limitação conhecida importante

**Inexigibilidade é publicada depois da decisão.** Quando o aviso do art. 74, II sai,
o artista já foi escolhido. Essa fonte serve para **inteligência de mercado**: quais
prefeituras contratam, quanto pagam, em que época, por qual produtora. O que é
*acionável em tempo real* são as categorias `CREDENCIAMENTO_ART79`, `FOMENTO_CULTURAL`
e `EVENTO_MUNICIPAL` — nessas você ainda pode se inscrever.

Prioridade de leitura dos alertas, portanto:
`CREDENCIAMENTO` > `FOMENTO` > `EVENTO_MUNICIPAL` > `INEXIGIBILIDADE` (histórico).

## 8. Boas práticas / legal

- `User-Agent` identificável já está configurado em `config.USER_AGENT` — **coloque seu
  e-mail real**. Isso evita bloqueio e é postura correta com serviço público.
- Concorrência limitada por semáforo (padrão 6) e backoff exponencial em 429/5xx.
- Dados de contratação pública são abertos por lei; não há problema em coletar.
- O endpoint `/api/search/` não é contrato oficial: se quebrar, a rota 2 mantém o
  sistema funcionando. É de propósito.
