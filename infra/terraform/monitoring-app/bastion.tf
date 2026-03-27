# ── Bastion: tambah /etc/hosts + nginx config via SSM ─────────────────────────

resource "aws_ssm_document" "bastion_setup" {
  name          = "ics-ms-monitoringapps-bastion-setup"
  document_type = "Command"

  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Configure bastion nginx for monitoring-app"
    mainSteps = [
      {
        action = "aws:runShellScript"
        name   = "configure_nginx"
        inputs = {
          runCommand = [
            # 1. Tambah /etc/hosts jika belum ada
            "grep -q 'ics-ms-monitoringapps' /etc/hosts || echo '${aws_instance.monitoringapps.private_ip} ics-ms-monitoringapps' >> /etc/hosts",
            # 2. Tulis nginx config
            "cat > /etc/nginx/sites-available/ics-ms-monitoringapps << 'NGINXEOF'",
            "${templatefile("${path.module}/bastion-nginx.conf.tpl", {})}",
            "NGINXEOF",
            # 3. Enable site jika belum
            "ln -sf /etc/nginx/sites-available/ics-ms-monitoringapps /etc/nginx/sites-enabled/ics-ms-monitoringapps",
            # 4. Test config
            "nginx -t",
            # 5. Reload nginx
            "systemctl reload nginx",
            "echo 'Bastion nginx configured for monitoring-app'",
          ]
        }
      }
    ]
  })
}

resource "aws_ssm_association" "bastion_setup" {
  name = aws_ssm_document.bastion_setup.name

  targets {
    key    = "InstanceIds"
    values = [var.bastion_instance_id]
  }

  # Jalankan sekali saat apply
  apply_only_at_cron_interval = false

  depends_on = [aws_instance.monitoringapps]
}
