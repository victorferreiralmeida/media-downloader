# Arquitetura do Sistema

Este documento descreve a arquitetura geral do sistema, apresentando os principais componentes e o fluxo de dados da aplicação.

---

## Visão Geral

O sistema oferece duas interfaces (desktop e web) sobre uma camada de download compartilhada:

- **Desktop** — CustomTkinter (`src/main.py`)
- **Web** — HTML/CSS/JS no GitHub Pages (`frontend/`)
- **API** — FastAPI na VPS (`backend/app.py`)
- **Core** — `src/downloader.py` (yt-dlp + FFmpeg)
- **Integração externa** — YouTube via yt-dlp

---

## Arquitetura dual (desktop + web)

```text
                    ┌─────────────────┐
                    │  src/downloader │
                    │  (yt-dlp+FFmpeg)│
                    └────────┬────────┘
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ src/main.py│  │ backend/   │  │  YouTube   │
     │ (Desktop)  │  │ app.py     │  │            │
     └─────┬──────┘  └─────┬──────┘  └────────────┘
           │               │
           ▼               ▼
     File System      Temp + Stream
     (usuário)       (navegador)
```

---

## Fluxo desktop

```text
Usuário → CustomTkinter UI → Downloader → YouTube
                                            ↓
                                       File System
```

---

## Fluxo web

```text
Usuário → GitHub Pages (frontend) → API FastAPI (VPS) → Downloader → YouTube
                                              ↓
                                         Arquivo temp
                                              ↓
                                    Download no navegador
```

### Endpoints da API

| Endpoint | Função |
|----------|--------|
| `POST /api/info` | Preview do vídeo |
| `POST /api/download` | Inicia job de download |
| `GET /api/progress/{id}` | Progresso via SSE |
| `GET /api/file/{id}` | Entrega o arquivo |

Playlists são entregues como arquivo ZIP na versão web.

---

## Hospedagem

| Componente | Onde roda |
|------------|-----------|
| Frontend | GitHub Pages (`/frontend`) |
| Backend | VPS (systemd + Nginx + SSL) |
| Desktop | Máquina do usuário (.exe ou Python) |

O desktop **não depende** da VPS. A versão web exige backend com FFmpeg instalado.

---

## Segurança (web)

- Rate limiting por IP (`slowapi`)
- Um download ativo por vez no servidor
- Limite de duração do vídeo (`MAX_DURATION_SECONDS`)
- Limpeza automática de arquivos temporários (`JOB_TTL_SECONDS`)
- CORS restrito ao domínio do GitHub Pages
