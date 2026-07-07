# Deploy na VPS (Ubuntu 22.04+)

## Pré-requisitos

- VPS com Ubuntu 22.04+ (mínimo 1–2 GB RAM)
- Domínio apontando para o IP da VPS (ex.: `api.seudominio.com`)
- Portas 80 e 443 abertas

## 1. Instalar dependências do sistema

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg nginx certbot python3-certbot-nginx git
```

## 2. Clonar o projeto

```bash
sudo mkdir -p /opt/media-downloader
sudo chown $USER:$USER /opt/media-downloader
git clone https://github.com/SEU-USUARIO/media-downloader.git /opt/media-downloader
cd /opt/media-downloader
```

## 3. Ambiente Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
mkdir -p backend/temp
```

## 4. Variáveis de ambiente

Copie e edite o exemplo:

```bash
cp backend/.env.example backend/.env
```

Defina `CORS_ORIGINS` com a URL do GitHub Pages, por exemplo:

```
CORS_ORIGINS=https://seu-usuario.github.io
```

## 5. Systemd

```bash
sudo cp deploy/media-downloader.service /etc/systemd/system/
sudo nano /etc/systemd/system/media-downloader.service
# Ajuste User, CORS_ORIGINS e caminhos se necessário

sudo systemctl daemon-reload
sudo systemctl enable media-downloader
sudo systemctl start media-downloader
sudo systemctl status media-downloader
```

## 6. Nginx + SSL

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/media-downloader
sudo ln -s /etc/nginx/sites-available/media-downloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

sudo certbot --nginx -d api.seudominio.com
```

## 7. Limpeza de arquivos temporários

A API remove jobs expirados automaticamente (`JOB_TTL_SECONDS`, padrão 1 hora).
Para limpeza manual periódica:

```bash
# crontab -e
0 */6 * * * find /opt/media-downloader/backend/temp -mindepth 1 -mmin +120 -exec rm -rf {} +
```

## Deploy com Docker (alternativa)

```bash
cd /opt/media-downloader
docker build -f backend/Dockerfile -t media-downloader .
docker run -d --name media-downloader -p 8000:8000 \
  -e CORS_ORIGINS=https://seu-usuario.github.io \
  -v media-temp:/app/temp \
  media-downloader
```

## Testar a API

```bash
curl http://127.0.0.1:8000/api/health
```

Documentação interativa: `https://api.seudominio.com/docs`

## Atualizar o frontend

Edite `frontend/config.js` com a URL da API:

```javascript
window.API_BASE = "https://api.seudominio.com";
```
