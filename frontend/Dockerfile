FROM nginx:alpine

# Copier les fichiers statiques
COPY index.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Configuration Nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Fixer les permissions
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
