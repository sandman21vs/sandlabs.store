# Dockerfile
FROM nginx:latest

WORKDIR /usr/share/nginx/html

# Remove o conteúdo padrão do Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copia os arquivos do site para o diretório público
COPY . /usr/share/nginx/html

# Expõe a pasta estática como volume para facilitar edições com bind mount
VOLUME ["/usr/share/nginx/html"]

# Expõe a porta HTTP
EXPOSE 80
