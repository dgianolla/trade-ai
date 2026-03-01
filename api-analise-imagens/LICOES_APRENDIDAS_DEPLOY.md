# Lições Aprendidas: Deploy Trade AI API (Swarm & Portainer)

Este documento centraliza os erros, causas e comandos de correção aprendidos durante a saga de deploy da API de Análise de Imagens no Docker Swarm via Portainer.

## 1. O Problema do "No such image" no Swarm (GHCR Privado)
**O que aconteceu:** O Portainer tenta baixar a imagem do Github (`ghcr.io`), mas o Swarm "esquece" de repassar a senha de autenticação para o worker, resultando em erro `401 Unauthorized` ou "No such image".
**A Solução Definitiva:** Logar o servidor VPS diretamente no Github usando um Personal Access Token (PAT).

**Comandos na VPS (Acesso via SSH `root@managerMC:~#`):**
```bash
# 1. Faça login direto na máquina usando o seu Username e o Token ghp_... como senha:
docker login ghcr.io -u dgianolla

# 2. Force o download da imagem direto no HD do servidor para "pular" o erro do Portainer:
docker pull ghcr.io/dgianolla/trade-ai:latest
```
*No Portainer:* Desmarque a chave "Pull latest image version" e clique em "Update the Stack" ou "Pull and Redeploy". O Portainer usará a imagem que você acabou de baixar localmente no disco.

## 2. Erro de Disco Lotado ("no space left on device")
**O que aconteceu:** A instalação padrão do `easyocr` (OCR) tentou baixar dependências colossais de IA da NVIDIA (Nvidia CUDA), gerando uma imagem Docker com mais de 4.4GB. Isso esgotou o armazenamento do servidor (HD da VPS) instantaneamente durante a extração.
**A Solução:** Forçar a instalação do ecossistema PyTorch na versão "CPU-only" dentro do `Dockerfile` (*--index-url https://download.pytorch.org/whl/cpu*) *antes* do requirements, derrubando o peso da imagem para rodar em servidores comuns sem placa de vídeo.

**Comandos de Limpeza de Lixo na VPS (Para esvaziar a falha):**
```bash
# Limpa todas as imagens baixadas pela metade, paradas ou sem uso (Libera todos os Gigabytes travados):
docker system prune -a --force

# Limpa apenas os volumes orfãos (se precisar de uma faxina geral no armazenamento):
docker volume prune --force
```

## 3. Crash do Container: PostgreSQL Externo (DATABASE_URL)
**O que aconteceu:** O Portainer acusa "Exit Code" e rejeita a tarefa (Task Rejected) instantes após recriar o container da API.
**A Causa:** O construtor interno do Python (`alembic upgrade head`) tentou se conectar no banco de dados e descobriu que a URL passada para o `DATABASE_URL` era um hospedeiro desconhecido.
**A Solução:** 
1. Garantir que no Portainer da API, a variável ambiente aponte para o *Nome do Serviço* interno com a stack da rede externa (ex: `postgress_postgres`).
2. Exemplo exato para conectar no banco que isolamos:
`postgresql://postgres:SuaSenhaAqui@postgress_postgres:5432/analise_imagens`
3. Garantir que o banco de dados `analise_imagens` realmente foi criado de forma manual, como fizemos rodando `CREATE DATABASE analise_imagens` no console isolado do PostgreSQL.

## 4. O Celery / FastAPI quebrando de imediato
**O que aconteceu:** O Worker do Celery, Flower ou API despencou com log de erro "ValidationError do Pydantic" informando falta do campo `API_KEY`.
**A Causa:** Criamos uma trava de segurança `API_KEY: str` onde o código bloqueia imediatamente do ar se as variáveis não estiverem setadas no Docker. Só tínhamos colocado a chave no container `api` principal, esquecendo de atualizar o YAML dos sub-containers.
**A Solução:** Mapear a injeção do ambiente `- API_KEY=${API_KEY}` para todos os containers dentro do arquivo YAML `docker-compose.yml`, além de garantir que setou essa chave lá visualmente no formulário Portainer antes de clicar no deploy.

## 5. Como resetar o Github Actions ou fazer Push 
Se o seu Portainer travar ao ler o Github, ou você precisar gerar uma imagem emergencial do zero no servidor (Forçar update de código a partir do Mac):

```bash
# Comandos do Mac (ou Dev Container)
git add .
git commit -m "fix(manutencao): forca o trigger da action de deploy com alteracoes"
git push
```
Após o push ser confirmado verdinho no site do Github Actions, vá no Portainer da sua API e aperte com vontade o botão **"Pull and Redeploy"**!
