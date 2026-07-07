# GitHub Pages

O frontend estático fica na pasta [`frontend/`](../frontend/).

## Configuração

1. Faça push do repositório para o GitHub.
2. Vá em **Settings → Pages → Build and deployment**.
3. Em **Source**, selecione:
   - Branch: `main`
   - Folder: `/frontend`
4. Salve. O site ficará disponível em:

   `https://SEU-USUARIO.github.io/media-downloader/`

## Conectar ao backend

Edite [`frontend/config.js`](../frontend/config.js) antes do deploy:

```javascript
window.API_BASE = "https://api.seudominio.com";
```

## CORS no backend

Na VPS, defina a variável de ambiente apontando para seu GitHub Pages:

```
CORS_ORIGINS=https://SEU-USUARIO.github.io
```

O backend também aceita automaticamente qualquer subdomínio `*.github.io` via regex.

## Testar localmente

Com a API rodando em `localhost:8000`:

```bash
cd frontend
python -m http.server 5500
```

Abra `http://localhost:5500` — `config.js` já aponta para `http://localhost:8000` por padrão.

## Arquivo `.nojekyll`

O arquivo `frontend/.nojekyll` evita que o GitHub Pages ignore arquivos que começam com `_`.
