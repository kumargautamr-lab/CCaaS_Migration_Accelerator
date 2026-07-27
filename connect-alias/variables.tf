variable "aws_region" {
  description = "AWS region for Amazon Connect"
  type        = string
  default     = "us-east-1"
}

variable "agent_passwords" {
  description = "Initial passwords for Connect-managed agent users"
  type        = map(string)
  sensitive   = true
}
