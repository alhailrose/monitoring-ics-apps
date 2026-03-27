variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-3"
}

variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "sandbox-ms"
}

variable "instance_type" {
  description = "EC2 instance type for monitoring app"
  type        = string
  default     = "t3.micro"
}

variable "ssh_public_key_path" {
  description = "Path to SSH public key to upload as EC2 key pair"
  type        = string
  default     = "~/.ssh/ics-ms-monitoringapps.pub"
}

variable "bastion_instance_id" {
  description = "Instance ID of the existing bastion (ics-ms-bastion)"
  type        = string
  default     = "i-0bcbbb416a00444dc"
}
