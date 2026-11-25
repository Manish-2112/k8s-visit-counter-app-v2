# Production Non-Root Nginx Image (listens on unprivileged port 8080)
FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx index.html style.css app.js /usr/share/nginx/html/

EXPOSE 8080
