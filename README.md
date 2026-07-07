# Media Downloader

![Python](https://img.shields.io/badge/Python-3.x-blue)
![CustomTkinter](https://img.shields.io/badge/Desktop-CustomTkinter-purple)
![FastAPI](https://img.shields.io/badge/API-FastAPI-green)
![yt-dlp](https://img.shields.io/badge/Download-yt--dlp-red)
![FFmpeg](https://img.shields.io/badge/Converter-FFmpeg-orange)
![Platform](https://img.shields.io/badge/Platform-Desktop%20%2B%20Web-lightgrey)

Aplicação para baixar músicas e vídeos do YouTube em MP3 ou MP4. Disponível como **app desktop** (Windows) e **site web** (GitHub Pages + API na VPS).

![YouTube Downloader](https://i.ibb.co/pjtCQKtP/youtubedownloader.png)

## Estrutura do projeto

```
media-downloader/
├── src/
│   ├── main.py          # App desktop (CustomTkinter)
│   └── downloader.py    # Lógica compartilhada (yt-dlp + FFmpeg)
├── backend/
│   ├── app.py           # API FastAPI
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Site (GitHub Pages)
│   ├── style.css
│   ├── app.js
│   └── config.js        # URL da API
└── deploy/              # Configs VPS e GitHub Pages
```

## Versão desktop

### Pré-requisitos

1. [FFmpeg](https://www.ffmpeg.org/download.html) instalado e no PATH (Windows: ex. `C:\ffmpeg\bin`)
2. Python 3.10+

### Instalação

```bash
pip install yt_dlp requests customtkinter pillow
```

### Executar

```bash
cd src
python main.py
```

### Uso

- Cole o link do vídeo ou playlist
- Clique em **Info** para ver detalhes
- Escolha **MP3** ou **MP4**
- Opcional: formatação automática de nomes e pasta de destino

## Versão web

### Arquitetura

- **Frontend:** GitHub Pages (`frontend/`)
- **Backend:** VPS com FastAPI + yt-dlp + FFmpeg

### Rodar localmente (desenvolvimento)

**API:**

```bash
pip install -r backend/requirements.txt
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

**Frontend:**

```bash
cd frontend
python -m http.server 5500
```

Abra `http://localhost:5500`. O `config.js` já aponta para `http://localhost:8000`.

### Deploy

- **GitHub Pages:** veja [deploy/github-pages.md](deploy/github-pages.md)
- **VPS:** veja [deploy/README.md](deploy/README.md)

Antes do deploy, edite `frontend/config.js`:

```javascript
window.API_BASE = "https://api.seudominio.com";
```

## API (endpoints)

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Status da API |
| POST | `/api/info` | Informações do vídeo/playlist |
| POST | `/api/download` | Inicia download (retorna `job_id`) |
| GET | `/api/progress/{job_id}` | Progresso via SSE |
| GET | `/api/file/{job_id}` | Baixa o arquivo pronto |
| DELETE | `/api/job/{job_id}` | Remove job e arquivos temporários |

Documentação interativa: `http://localhost:8000/docs`

## Aviso legal

Uso pessoal e educacional. Baixar conteúdo do YouTube pode violar os Termos de Serviço da plataforma. Use com responsabilidade.
