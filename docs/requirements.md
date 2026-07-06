## Requisitos do Sistema

Este documento apresenta os requisitos do sistema de forma estruturada, descrevendo as funcionalidades que a aplicação deve oferecer (requisitos funcionais) e as características de qualidade e restrições que devem ser atendidas (requisitos não funcionais). O objetivo é fornecer uma visão clara e organizada do comportamento esperado do sistema, servindo como base para o desenvolvimento, validação e manutenção da aplicação.

## Requisitos Funcionais

| ID    | Descrição |
|-------|----------|
| RF01  | O sistema deve permitir que o usuário insira um link de vídeo do YouTube. |
| RF02  | O sistema deve validar se o link fornecido é válido. |
| RF03  | O sistema deve exibir as informações do vídeo (título, duração, etc.) antes do download. |
| RF04  | O sistema deve permitir ao usuário escolher o formato de download (MP3 ou MP4). |
| RF05  | O sistema deve permitir ao usuário selecionar o diretório de destino para salvar os arquivos. |
| RF06  | O sistema deve realizar o download do conteúdo no formato selecionado. |
| RF07  | O sistema deve permitir o download de múltiplos vídeos a partir de uma playlist. |
| RF08  | O sistema deve permitir a formatação automática dos nomes dos arquivos, incluindo enumeração automática e remoção de caracteres especiais. |
| RF09  | O sistema deve exibir o progresso do download em tempo real. |
| RF10  | O sistema deve informar ao usuário quando o download for concluído. |

---

## Requisitos Não Funcionais

| ID     | Descrição |
|--------|----------|
| RNF01  | O sistema deve estar disponível como aplicação desktop e como site web (API + frontend estático). |
| RNF02  | A interface deve ser simples, intuitiva e de fácil utilização. |
| RNF03  | O sistema deve apresentar tempo de resposta adequado ao processar links e iniciar downloads. |
| RNF04  | O sistema deve garantir a integridade dos arquivos baixados. |
| RNF05  | O sistema deve operar de forma segura, sem expor o usuário a riscos como downloads maliciosos. |
| RNF06  | O sistema deve ser compatível com os principais sistemas operacionais desktop (Windows, Linux ou macOS). |
| RNF07  | O sistema deve suportar downloads de arquivos de diferentes tamanhos sem falhas. |
| RNF08  | O sistema deve manter estabilidade durante múltiplos downloads consecutivos ou em lote. |
