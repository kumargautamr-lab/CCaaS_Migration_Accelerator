variable "genesys_region" {
  description = "Genesys Cloud region for deployment"
  type        = string
  default     = "use1"
}

variable "environment_name" {
  description = "Target Genesys environment identifier"
  type        = string
  default     = "AvayaMigration"
}

variable "agent_language" {
  description = "Default language for prompts"
  type        = string
  default     = "en-US"
}