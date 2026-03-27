# ── IAM Instance Profile untuk monitoring-app EC2 ────────────────────────────
# EC2 pakai Instance Profile → AWS SDK otomatis ambil credentials tanpa file .aws
# Tidak perlu SSO, tidak perlu access key di server.

resource "aws_iam_role" "ics-ms-monitoringapps" {
  name = "ics-ms-monitoringapps-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Name      = "ics-ms-monitoringapps-role"
    ManagedBy = "terraform"
  }
}

resource "aws_iam_role_policy" "ics-ms-monitoringapps_policy" {
  name = "ics-ms-monitoringapps-policy"
  role = aws_iam_role.ics-ms-monitoringapps.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # STS — untuk get account ID dan AssumeRole ke customer accounts
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity", "sts:AssumeRole"]
        Resource = "*"
      },
      {
        # CloudWatch — baca metrics dan alarms
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData",
          "cloudwatch:DescribeAlarms",
          "cloudwatch:ListMetrics",
        ]
        Resource = "*"
      },
      {
        # EC2 — list instances dan regions
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeRegions",
          "ec2:DescribeInstanceStatus",
        ]
        Resource = "*"
      },
      {
        # RDS — list clusters dan instances
        Effect = "Allow"
        Action = [
          "rds:DescribeDBClusters",
          "rds:DescribeDBInstances",
        ]
        Resource = "*"
      },
      {
        # GuardDuty — baca findings
        Effect = "Allow"
        Action = [
          "guardduty:ListDetectors",
          "guardduty:GetDetector",
          "guardduty:ListFindings",
          "guardduty:GetFindings",
        ]
        Resource = "*"
      },
      {
        # Cost Explorer — baca cost anomalies dan budget
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetAnomalies",
          "ce:GetAnomalyMonitors",
          "budgets:ViewBudget",
          "budgets:DescribeBudget",
        ]
        Resource = "*"
      },
      {
        # Health — baca AWS Health events
        Effect = "Allow"
        Action = [
          "health:DescribeEvents",
          "health:DescribeEventDetails",
          "health:DescribeAffectedEntities",
        ]
        Resource = "*"
      },
      {
        # Backup — cek status backup jobs
        Effect = "Allow"
        Action = [
          "backup:ListBackupJobs",
          "backup:DescribeBackupJob",
        ]
        Resource = "*"
      },
      {
        # SSM — untuk SSO session health (jika digunakan)
        Effect = "Allow"
        Action = [
          "sso:ListAccountRoles",
          "sso:GetRoleCredentials",
        ]
        Resource = "*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "ics-ms-monitoringapps" {
  name = "ics-ms-monitoringapps-profile"
  role = aws_iam_role.ics-ms-monitoringapps.name
}
