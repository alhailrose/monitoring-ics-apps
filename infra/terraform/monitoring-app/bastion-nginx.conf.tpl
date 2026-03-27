# File: /etc/nginx/sites-available/msmonitoring
# Deploy ke bastion setelah terraform apply
#
# 1. Tambah /etc/hosts entry:
#    echo "<PRIVATE_IP> ics-ms-monitoringapps" >> /etc/hosts
#
# 2. Copy file ini ke:
#    /etc/nginx/sites-available/msmonitoring
#
# 3. Issue cert:
#    certbot --nginx -d msmonitoring.bagusganteng.app --non-interactive --agree-tos -m admin@bagusganteng.app
#
# 4. Enable & reload:
#    ln -s /etc/nginx/sites-available/msmonitoring /etc/nginx/sites-enabled/
#    nginx -t && systemctl reload nginx

limit_req_zone $binary_remote_addr zone=monitoring_app:10m rate=60r/s;

server {
    listen 80;
    server_name msmonitoring.bagusganteng.app;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name msmonitoring.bagusganteng.app;

    access_log /var/log/nginx/msmonitoring.bagusganteng.app.access.log;
    error_log  /var/log/nginx/msmonitoring.bagusganteng.app.error.log;

    ssl_certificate     /etc/letsencrypt/live/msmonitoring.bagusganteng.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/msmonitoring.bagusganteng.app/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/msmonitoring.bagusganteng.app/chain.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    client_max_body_size 20M;

    location / {
        limit_req zone=monitoring_app burst=20 nodelay;

        proxy_pass http://ics-ms-monitoringapps:80;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";

        proxy_read_timeout    600s;
        proxy_connect_timeout  30s;
        proxy_send_timeout    600s;
        proxy_redirect        off;
        proxy_cache_bypass    $http_upgrade;

        add_header X-Content-Type-Options    nosniff always;
        add_header X-Frame-Options           SAMEORIGIN always;
        add_header Referrer-Policy           strict-origin-when-cross-origin always;
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    }
}
