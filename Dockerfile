# Dockerfile
FROM nginx:latest

WORKDIR /usr/share/nginx/html

# Pacotes para atualização via Git
RUN apt-get update \
  && apt-get install -y --no-install-recommends git rsync ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Remove o conteúdo padrão do Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copia os arquivos do site para o diretório público
COPY . /usr/share/nginx/html

# Entrypoint customizado para puxar atualizações automáticas (opcional)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expõe a pasta estática como volume para facilitar edições com bind mount
VOLUME ["/usr/share/nginx/html"]

# Expõe a porta HTTP
EXPOSE 80

# Sincroniza com repositório remoto (se REPO_URL definido) e inicia o Nginx
ENTRYPOINT ["/entrypoint.sh"]
