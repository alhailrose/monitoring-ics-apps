output "instance_id" {
  description = "EC2 instance ID of ics-ms-monitoringapps"
  value       = aws_instance.monitoringapps.id
}

output "private_ip" {
  description = "Private IP of ics-ms-monitoringapps"
  value       = aws_instance.monitoringapps.private_ip
}

output "instance_profile_arn" {
  description = "IAM Instance Profile ARN — share with customers for AssumeRole trust policy"
  value       = aws_iam_instance_profile.ics-ms-monitoringapps.arn
}
