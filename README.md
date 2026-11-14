# 🎮 Find My Game

Sistema de recomendação de jogos por **busca semântica**. Você descreve em texto o jogo que procura ("RPG medieval com dragões e magia") e recebe os jogos mais parecidos do catálogo.

Projeto pessoal para estudar o ciclo de ML Engineering de ponta a ponta: ingestão de dados, embeddings, API, frontend, AWS e POO em Python.

## Como funciona

```
 INGESTÃO (AWS Lambda ou local)                       CONSULTA
 ┌──────┐   ┌────────┐   ┌─────────────┐   ┌────────┐      ┌───────────┐   ┌──────────┐
 │ IGDB │──►│ Gêneros│──►│  Embeddings │──►│Storage │◄─────│  FastAPI  │◄──│Streamlit │
 │ API  │   │ id→nome│   │   (Gemini)  │   │S3/disco│      │ Recommender│  │ frontend │
 └──────┘   └────────┘   └─────────────┘   └────────┘      └───────────┘   └──────────┘
   500 jogos mais populares      parquet com vetor por jogo     cosseno: consulta × jogos
```

1. **Ingestão:** busca os jogos mais populares da IGDB (paginado), troca IDs de gênero por nomes, descarta jogos sem resumo e gera um embedding (vetor de 3072 dimensões) de `nome + gêneros + resumo`. Salva tudo em um parquet.
2. **Consulta:** a API carrega o parquet uma vez, gera o embedding da consulta e calcula a similaridade de cosseno com todos os jogos. Devolve o top-k.
3. **Frontend:** tela em Streamlit que chama a API e mostra os resultados em cards.

Os embeddings usam `RETRIEVAL_DOCUMENT` para os jogos e `RETRIEVAL_QUERY` para a consulta, que é como o modelo foi treinado para busca assimétrica.

## Arquitetura (POO)

O código depende de **contratos** (classes abstratas) e não de implementações, então cada peça é trocável e testável com fakes.

| Classe | Arquivo | Papel |
|---|---|---|
| `Settings` | `app/src/config.py` | Config lida do ambiente (dataclass imutável) e fábrica de `Storage` |
| `Game` | `app/src/models.py` | Um jogo (dataclass) |
| `GameSource` → `IGDBClient` | `app/src/sources.py` | Fonte de jogos; IGDB paginada, com rate limit e renovação de token |
| `GenreMapper` | `app/src/genres.py` | IDs de gênero → nomes |
| `EmbeddingProvider` → `GeminiEmbedder`, `FakeEmbedder` | `app/src/embeddings.py` | Gera embeddings; retry e respeito ao limite de cota; fake para testes |
| `Storage` → `LocalStorage`, `S3Storage` | `app/src/storage.py` | Lê e grava o catálogo em parquet (Template Method) |
| `IngestionPipeline` | `app/src/pipeline.py` | Orquestra fonte → gêneros → embeddings → storage |
| `Recommender` | `app/src/recommender.py` | Busca top-k por cosseno (matriz normalizada) |
| `create_app` | `app/src/api.py` | API FastAPI (`/health`, `/recommend`) + handler Lambda (Mangum) |
| `RecommenderAPI` | `frontend/api_client.py` | Cliente HTTP usado pelo frontend |

## Configuração

Requer Python 3.12+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r app/requirements-dev.txt -r frontend/requirements.txt
copy .env.example .env      # e preencha os valores
```

Variáveis do `.env`:

| Variável | Para quê |
|---|---|
| `CLIENT_ID`, `CLIENT_SECRET` | App da Twitch (usado pela IGDB). O secret permite renovar o token sozinho |
| `ACCESS_TOKEN` | Alternativa ao secret (token fixo, expira) |
| `GOOGLE_API_KEY` | Chave do Google AI Studio (embeddings Gemini) |
| `LOCAL_DATA_DIR` | Se definido (ex.: `data`), usa disco em vez do S3. Relativo à raiz do projeto |
| `BUCKET_NAME`, `AWS_*` | Bucket e credenciais do S3 (quando não usa `LOCAL_DATA_DIR`) |

## Rodando localmente

Os módulos de `app/src` usam imports diretos, então execute de dentro dessa pasta.

```powershell
# 1) Gerar o catálogo (IGDB -> Gemini -> data/jogos_embeddings.parquet)
#    Defina LOCAL_DATA_DIR=data no .env
cd app\src
python main.py

# 2) Subir a API  ->  http://localhost:8000/docs
python -m uvicorn api:app --reload

# 3) Em outro terminal, subir o frontend  ->  http://localhost:8501
cd ..\..\frontend
streamlit run app.py
```

Exemplo direto na API:
```powershell
curl -X POST http://localhost:8000/recommend -H "Content-Type: application/json" `
     -d '{"query": "medieval RPG with dragons", "top_k": 3}'
```

> **Plano gratuito do Gemini:** a cota é de ~100 textos de embedding por minuto. A ingestão de 500 jogos leva alguns minutos porque o `GeminiEmbedder` espera o tempo que a API manda quando recebe erro 429.

## Testes

```powershell
python -m pytest app/tests -q
```

Os testes não usam rede nem AWS: injetam `FakeEmbedder`, clientes HTTP falsos e `LocalStorage` em pasta temporária.

## Deploy na AWS (não incluso no MVP)

O código já está preparado, mas o empacotamento não foi feito:
- **Ingestão:** `main.lambda_handler` (evento opcional `{"limit": 500}`). Credenciais do S3 vêm da IAM role.
- **API:** `api.handler` (Mangum) atrás de um API Gateway, lendo o parquet do S3.
- Variáveis de ambiente do Lambda: as mesmas do `.env`, sem `LOCAL_DATA_DIR`.

## Próximos passos

- Empacotar e fazer o deploy no Lambda + API Gateway; testar o `S3Storage` de verdade.
- Rodar a ingestão periodicamente (EventBridge) e evitar reembedar jogos já processados.
- Filtros por gênero e nota, e busca híbrida (palavras-chave + semântica).
- Banco vetorial caso o catálogo passe de ~10 mil jogos.
