resource "aws_security_group" "allow_ingress_port" {
  name   = "my-vm-ingress-security-group"

  dynamic "ingress" {
    for_each = tolist(var.ingress_list)
    iterator = port
    content {
      from_port   = port.value
      to_port     = port.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
}

resource "aws_security_group" "allow_egress_ports" {
  name   = "my-vm-egress-security-group"

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "my_vm" {
  ami                    = var.ami_name
  instance_type          = var.bastioninstancetype
  key_name               = var.key_name
  source_dest_check      = false
  vpc_security_group_ids = [ aws_security_group.allow_ingress_port.id, aws_security_group.allow_egress_ports.id ]
  availability_zone      = local.zone
  user_data_base64       = base64encode(<<-EOF
#!/bin/bash

timedatectl set-timezone Europe/Paris || ln -sf /usr/share/zoneinfo/Europe/Paris /etc/localtime

dnf install -y cronie httpd mod_ssl
APACHE_SERVICE="httpd"
SSL_CERT_DIR="/etc/pki/tls/certs"
SSL_KEY_DIR="/etc/pki/tls/private"
APACHE_SSL_CONF="/etc/httpd/conf.d/cron-log-ssl.conf"

systemctl enable crond >/dev/null 2>&1 || systemctl enable cron >/dev/null 2>&1
systemctl restart crond >/dev/null 2>&1 || systemctl restart cron >/dev/null 2>&1

cat > /home/ec2-user/check_urls.sh <<'SCRIPT'
#!/bin/bash
TS=$(date '+%Y-%m-%d %H:%M:%S')

curl -fsS --max-time 2 https://football-predictor-api-rtxx.onrender.com/docs >/dev/null && echo "$TS OK api docs" || echo "$TS KO api docs"
curl -fsS --max-time 2 https://football-predictor-inference-api.onrender.com/docs >/dev/null && echo "$TS OK inference docs" || echo "$TS KO inference docs"
curl -fsS --max-time 2 https://football-predictor-front.onrender.com >/dev/null && echo "$TS OK front" || echo "$TS KO front"
# curl -fsS --max-time 2  https://8100-01kyne3htfkyrjy07tgdspdwhp.cloudspaces.litng.ai/health >/dev/null && echo "$TS OK LLM" || echo "$TS KO LLM"
SCRIPT

chown ec2-user:ec2-user /home/ec2-user/check_urls.sh
chmod 750 /home/ec2-user/check_urls.sh

CRON_LINE="*/10 * * * * /home/ec2-user/check_urls.sh >> /home/ec2-user/cron-url-check.log 2>&1"
(crontab -u ec2-user -l 2>/dev/null | grep -Fv "/home/ec2-user/check_urls.sh"; echo "$CRON_LINE") | crontab -u ec2-user -

touch /home/ec2-user/cron-url-check.log
chown ec2-user:ec2-user /home/ec2-user/cron-url-check.log
chmod 644 /home/ec2-user/cron-url-check.log
chmod 755 /home/ec2-user

cat > /etc/logrotate.d/cron-url-check <<'LOGROTATE'
/home/ec2-user/cron-url-check.log {
  hourly
  rotate 10
  missingok
  notifempty
  compress
  delaycompress
  copytruncate
  create 0644 ec2-user ec2-user
}
LOGROTATE

cat > /etc/systemd/system/cron-url-check-logrotate.service <<'SERVICE'
[Unit]
Description=Run logrotate for cron-url-check.log

[Service]
Type=oneshot
ExecStart=/usr/sbin/logrotate /etc/logrotate.d/cron-url-check
SERVICE

cat > /etc/systemd/system/cron-url-check-logrotate.timer <<'TIMER'
[Unit]
Description=Hourly rotation for cron-url-check.log

[Timer]
OnCalendar=hourly
Persistent=true
Unit=cron-url-check-logrotate.service

[Install]
WantedBy=timers.target
TIMER

systemctl daemon-reload
systemctl enable --now cron-url-check-logrotate.timer

mkdir -p "$SSL_CERT_DIR" "$SSL_KEY_DIR"
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$SSL_KEY_DIR/cron-log.key" \
  -out "$SSL_CERT_DIR/cron-log.crt" \
  -days 365 \
  -subj "/C=FR/ST=IDF/L=Paris/O=football-predictor/CN=$(hostname -f)"

cat > "$APACHE_SSL_CONF" <<'APACHECONF'
Listen 443

<VirtualHost *:443>
  ServerName _default_
  SSLEngine on
  SSLCertificateFile SSL_CERT_PATH
  SSLCertificateKeyFile SSL_KEY_PATH

  Alias /cron-log /home/ec2-user/cron-url-check.log
  <Location /cron-log>
    Require all granted
  </Location>
</VirtualHost>
APACHECONF

sed -i "s|SSL_CERT_PATH|$SSL_CERT_DIR/cron-log.crt|g" "$APACHE_SSL_CONF"
sed -i "s|SSL_KEY_PATH|$SSL_KEY_DIR/cron-log.key|g" "$APACHE_SSL_CONF"

if [ "$APACHE_SERVICE" = "apache2" ]; then
  a2enmod ssl >/dev/null 2>&1 || true
  a2ensite cron-log-ssl.conf >/dev/null 2>&1 || true
  a2dissite 000-default >/dev/null 2>&1 || true
fi

if [ "$APACHE_SERVICE" = "httpd" ] && [ -f /etc/httpd/conf.d/ssl.conf ]; then
  mv /etc/httpd/conf.d/ssl.conf /etc/httpd/conf.d/ssl.conf.disabled
fi

if command -v chcon >/dev/null 2>&1; then
  chcon -t httpd_sys_content_t /home/ec2-user || true
  chcon -t httpd_sys_content_t /home/ec2-user/cron-url-check.log || true
fi

echo "OK" > /var/www/html/index.html

systemctl enable "$APACHE_SERVICE"
systemctl restart "$APACHE_SERVICE"
  EOF
  )
  tags = {
    Name = "my_vm_demo"
  }
}

resource "aws_eip" "lb" {
  domain = "vpc"
}

resource "aws_eip_association" "eip_assoc" {
  instance_id   = aws_instance.my_vm.id
  allocation_id = aws_eip.lb.id
  // depends_on = [time_sleep.wait_30_seconds]
}




