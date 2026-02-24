# Tutorial de Implantação com Portainer: API de Análise de Imagens (Trade AI)

Como você já possui o **Portainer** instalado na sua VPS, o processo de subir os contêineres fica extremamente visual e fácil, eliminando a necessidade de rodar comandos via terminal.

O Portainer gerencia os serviços através da funcionalidade "**Stacks**", que é a interface visual para o arquivo `docker-compose.yml`.

---

## 🚀 1. Opções para subir o código no Portainer

Como o nosso `docker-compose.yml` utiliza a instrução `build: .` (que precisa do `Dockerfile` e do código-fonte local), a maneira mais recomendada de operar pelo Portainer é conectando o seu repositório Git.

### Passo 1.1: Acessar a criação de Stack
1. Abra o **Portainer** e acesse o seu ambiente (geralmente "local").
2. No menu lateral esquerdo, clique em **Stacks**.
3. Clique no botão azul **+ Add stack** no canto superior direito.
4. Dê um nome para a stack (ex: `tradeapi-stack`).

### Passo 1.2: Escolher o Método (Repository)
A melhor forma de gerenciar os builds é baixar direto do seu repositório:
1. Na seção "Build method", selecione a aba **Repository**.
2. Cole a **URL do seu repositório Git** onde este projeto está hospedado.
3. Em "Repository reference", coloque a branch principal (ex: `refs/heads/main`).
4. Em "Compose path", deixe como `docker-compose.yml`.

*(Ative a opção "Authentication" se o seu repositório for privado e insira suas credenciais)*

### Passo 1.3: Variáveis de Ambiente (Environment variables)
O nosso projeto requer chaves de API secretas e configurações. Abaixo dessa opção, clique em **Add environment variable** e adicione as suas chaves do `.env`:

*   **API_KEY**: `(sua-chave-secreta-para-acesso-aos-endpoints)`
*   **OPENAI_API_KEY**: `sk-proj-...`
*   *(Opcional)* **DATABASE_URL**: `postgresql://user:password@postgres:5432/analise_imagens`

### Passo 1.4: Construir a Imagem Base (Para Docker Swarm)
Como o Portainer em modo Swarm não compila o código sozinho (ignorando a instrução `build:`), você precisa construir a imagem na sua máquina **uma única vez** antes de iniciar tudo.

1. Acesse sua VPS via terminal (SSH).
2. Vá até a pasta onde está este código baixado:
   ```bash
   cd /caminho/para/api-analise-imagens
   ```
3. Rode o comando de Build da imagem informando o nome `analise-imagens`:
   ```bash
   docker build -t analise-imagens:latest .
   ```
   *(Aguarde 1 a 2 minutos até ele baixar e instalar o Python/Pacotes).*

### Passo 1.5: Fazer o Deploy no Portainer
1. Volte na tela de criação de Stack no Portainer.
2. Mais abaixo, ative a opção **"Enable relative path volumes"** (isso permite mapear pastas corretamente).
3. Clique no botão azul gigante **Deploy the stack**.

O Portainer fará o download das instruções, usará a nossa imagem recém construída (`analise-imagens:latest`) e inicializará nossa API, Celery Worker, Redis, MinIO e Postgres.

A nossa API ficará acessível **internamente** na porta **8000** da sua VPS ou para a rede do Docker. Se no seu `docker-compose.yml` houver um `ports: - "8000:8000"`, ela ficará exposta para a internet no IP da VPS.

---

## ☁️ 2. Mapeando um Domínio da Cloudflare para a API (O "Name")

Entendido! Como você gerencia tudo direto pelo painel web da Cloudflare em nuvem, faremos o mapeamento padrão via DNS. O fluxo é muito simples: **O Navegador bate na Cloudflare -> A Cloudflare Bate no seu IP da VPS**.

### Passo 2.1: Criar o Apontamento DNS (O Subdomínio)
1. Faça login na sua conta da **Cloudflare**.
2. Escolha o seu domínio (ex: `suaempresa.com.br`).
3. Vá no menu lateral e clique em **DNS > Records**.
4. Clique no botão azul **Add record**:
   *   **Type**: Selecione `A`
   *   **Name**: Digite o prefixo desejado. Por exemplo, digite **`api-trade`** (que vai virar `api-trade.mcbot.api.br`).
   *   **IPv4 address**: Cole o IP público da sua **VPS**.
   *   **Proxy status**: Deixe a nuvem laranja ativada ☁️ (Isso garante o HTTPS "cadeado verde" e segurança).
5. Clique em **Save**.

### Passo 2.2: O Roteamento de Portas (VPS / Proxy Reverso)
A Cloudflare espera que o seu servidor (VPS) escute tráfego web nas portas **80** (HTTP) e **443** (HTTPS). 

Porém, nossa API está rodando na porta **8000** do Docker. Como resolvemos isso? Você tem duas opções:

#### **Opção A: Ajustar a Porta Diretamente no `docker-compose.yml` (Mais Rápida e Simples)**
Se você **NÃO TEM** outros sites rodando na mesma VPS e quer que a API seja o serviço principal, você pode simplesmente mapear a porta `80` pro Container da API.

No seu repositório, modifique o `docker-compose.yml`, na parte da `api`:
```yaml
  api:
    build: .
    ports:
      - "80:8000" # Mapeia a porta 80 do VPS para a 8000 interna da API
```
Se você fizer isso e der "Update Stack" no Portainer, ao acessar `http://api-trade.mcbot.api.br/docs`, a API abrirá perfeitamente e a Cloudflare forçará o HTTPS automaticamente (`https://`) para os visitantes.

#### **Opção B: Usar o Traefik (Se você já tiver ele instalado)**
Como o erro demonstrou que a sua porta 80 já está em uso pelo **Traefik**, você NÃO pode usar o Nginx Proxy Manager (pois darão conflito). A ótima notícia é que o Traefik é excelente e **já está resolvendo esse papel na sua máquina!**

A única coisa que você precisa fazer é adicionar os **Labels** (Etiquetas) corretos no serviço da `api` dentro do seu `docker-compose.yml`, informando ao Traefik qual domínio essa API deve responder.

1. No seu `docker-compose.yml`, altere a seção do serviço `api`:
   ```yaml
   services:
     api:
       build: .
       restart: always
       # ...  Outras configurações (depends_on, env_file) permanecem ...
       labels:
         - "traefik.enable=true"
         
         # 1. Cria o Router indicando seu subdomínio na Nuvem
         - "traefik.http.routers.api_trade.rule=Host(`api-trade.mcbot.api.br`)"
         
         # 2. Aponta para onde o Serviço da API escuta DENTRO do container
         - "traefik.http.services.api_trade.loadbalancer.server.port=8000"
         
         # 3. (OPCIONAL) Se o seu Traefik gera SSL automático via Let's Encrypt
         - "traefik.http.routers.api_trade.tls.certresolver=YOUR_RESOLVER_NAME_HERE"
   ```
2. Adicione sua rede do Traefik:
   Se o seu Traefik existe numa rede global (muito comum se chamar `network_public` ou `web`), é preciso conectar a API nela. No **final** do seu `docker-compose.yml`:
   ```yaml
   networks:
     analise_network:
     # Referencie a rede do seu Traefik aqui. Exemplo:
     network_public:
       external: true
   ```
   E dentro do serviço da `api`, adicione a rede para que o container possa ver o portão de entrada do Traefik:
   ```yaml
   services:
     api:
       networks:
         - analise_network
         - network_public
   ```

3. Dê Update na sua Stack do Projeto Trade AI no Portainer e a mágica acontece. O Traefik pegará o tráfego do domínio e fará o passe direto para nossa porta `8000` sem você precisar clicar em nenhum painel.
