# ModelTrace Desktop (Streamlit) — Design

**Data:** 2026-06-25
**Atividade:** Fazer CRUD de coleções importantes — interface Streamlit, popular as principais coleções, telas de INSERT/FIND/UPDATE/DELETE, prints em diretório do repositório.

## Contexto

O projeto `Projeto NoSQL` é o **ModelTrace**: backend FastAPI + camada documental
`DocumentStore` (implementações `JsonDocumentStore` e `MongoDocumentStore`) +
frontend web Next.js. O banco JSON local fica em `backend/.data/modeltrace.json`
e já está populado.

A documentação do próprio projeto (`docs/modelagem-banco-json.md`) define a
"versão simplificada" com **10 coleções principais**, que adotamos aqui:
`organizations`, `users`, `projects`, `models`, `model_versions`, `predictions`,
`metrics_snapshots`, `alerts`, `api_keys`, `audit_events`.

## Objetivo

Criar uma **nova pasta** `desktop_app/` que é uma versão do projeto rodando como
**aplicativo Python desktop** (Streamlit), com o frontend deixando de ser web.

## Arquitetura

```
Streamlit (UI multipágina)  ->  SyncDocumentStore  ->  data/modeltrace_desktop.json
```

- Sem servidor FastAPI: num app Streamlit o "front" e o acesso a dados rodam no
  mesmo processo Python.
- O `DocumentStore` original é assíncrono (por causa do FastAPI/`motor`).
  Streamlit é síncrono e re-executa o script a cada interação, então **adaptamos**
  para um `SyncDocumentStore` que lê/grava o mesmo formato JSON (mesma semântica de
  filtros e de `$set`/`$inc`). Suporte opcional a MongoDB via `pymongo`.
- **Banco próprio do app**: `desktop_app/data/modeltrace_desktop.json`, populado a
  partir dos dados reais do backend. Assim o CRUD de demonstração (DELETE/UPDATE)
  não altera o dataset do site web.

## Decisões

| Tema | Decisão |
|------|---------|
| Banco | Cópia própria, populada a partir de `backend/.data/modeltrace.json` |
| Coleções | As 10 principais (versão simplificada da doc) |
| Camada de dados | `SyncDocumentStore` síncrono próprio (adaptação do JSON store) |
| Volume | `predictions` e `audit_events` aparados para ~150 docs cada (performance/prints) |
| Navegação | 1 página Streamlit por coleção (atende "print de cada tela") |
| IDs | `<prefixo>_<hex12>` no mesmo padrão observado (org_, user_, proj_, model_, version_, pred_, metric_, alert_, key_, audit_) |

## Estrutura

```
desktop_app/
├─ app.py                 # Tela inicial: resumo do banco, contagens, botão Popular/Resetar
├─ core/
│  ├─ store.py            # SyncDocumentStore + get_nested/set_nested
│  ├─ collections.py      # metadados das 10 coleções (rótulo, ícone, campos, colunas)
│  ├─ ids.py              # geração de _id no padrão da coleção
│  └─ seed.py             # copia as 10 coleções do backend, apara grandes
├─ ui/
│  └─ crud.py             # motor reutilizável INSERT/FIND/UPDATE/DELETE + render_page
├─ pages/                 # 10 telas (1 por coleção)
├─ data/modeltrace_desktop.json
├─ screenshots/           # entrega do item 4
├─ requirements.txt       # streamlit, pandas
├─ run_app.bat            # streamlit run app.py
└─ README.md
```

## Telas (cada coleção)

Quatro abas cobrindo o CRUD:

- **FIND** — por `_id`, por `campo = valor`, ou todos; tabela (pandas) + JSON.
- **INSERT** — formulário (campos principais) ou JSON completo; `_id` automático.
- **UPDATE** — seleciona `_id`, aplica `$set` (campo) ou substitui JSON.
- **DELETE** — seleciona `_id`, com confirmação.

## Entregáveis da atividade

1. Interface Streamlit ✅
2. Criar e popular principais coleções ✅ (`core/seed.py`, idempotente + botão na home)
3. Telas INSERT/FIND/UPDATE/DELETE ✅
4. Prints de cada tela/coleção → `desktop_app/screenshots/` ✅

## Riscos / mitigação

- **Escrita concorrente no JSON**: app single-user; `threading.Lock` no store.
- **Mutação do dataset real**: evitada usando banco próprio do app.
- **Streamlit não instalado**: adicionado em `requirements.txt`; instalado no setup.
