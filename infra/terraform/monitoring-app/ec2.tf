# ── Monitoring App EC2 (private subnet) ──────────────────────────────────────

resource "aws_instance" "monitoringapps" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = data.aws_subnet.private_a.id
  key_name               = aws_key_pair.monitoringapps.key_name
  iam_instance_profile   = aws_iam_instance_profile.ics-ms-monitoringapps.name
  vpc_security_group_ids = [
    data.aws_security_group.private.id,
    data.aws_security_group.efs_client.id,
  ]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    delete_on_termination = true
    encrypted             = true
  }

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    app_dir = "/opt/monitoring-app"
  })

  tags = {
    Name        = "ics-ms-monitoringapps"
    Environment = "development"
    ManagedBy   = "terraform"
  }

  lifecycle {
    ignore_changes = [ami, user_data]
  }
}
