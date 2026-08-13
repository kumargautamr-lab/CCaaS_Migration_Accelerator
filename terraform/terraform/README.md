# Genesys Cloud Migration Artifacts

## Resources Created
- **Inbound Flows**: 
  - `main_ivr` (from VDN-44801)
  - `sales_inquiry` (from VDN-44802)
  - `payment_processing` (from VDN-44810 - awaiting review)
- **Queues**:
  - `general_queue` (from SPL-001)
- **Skills**:
  - `vip_skill` (from SK-004, in review)
- **Prompts**:
  - `welcome_prompt` (from ann_welcome_44801.wav)
- **Schedules**:
  - `holiday_group` (from HolidayTable_03)

## Outstanding Items
1. `CRM_DataDip (ASAI)` requires custom Data Action rebuild (see TODO in main.tf)
2. `Payment Processing` flow requires manual validation before production
3. `VIP_EAS_Skill` mapping has lower confidence score (72%) - review recommended
===FILE: terraform/.gitignore
*.tfstate
*.tfstate.backup
.terraform/
.DS_Store
__pycache__/
===FILE: terraform/provider.tf
terraform {
  required_providers {
    genesyscloud = {
      source  = "mygenesys/genesyscloud"
      version = "~> 1.0"
    }
  }
}

provider "genesyscloud" {
  client_id     = var.genesys_client_id
  client_secret = var.genesys_client_secret
  region        = var.genesys_region
}

variable "genesys_client_id" {}
variable "genesys_client_secret" {}
===FILE: terraform/locals.tf
locals {
  flow_header = "Avaya-to-Genesys Migration Artifacts"
  flow_prefix = "Migrated_"
  environment_tags = {
    Migrated = "true"
    Source   = "Avaya-Aura"
  }
}
===FILE: terraform/tags.tf
resource "genesys_tag" "migration_tag" {
  name        = "Avaya-Migration-2024"
  description = "Tagging for migrated resources"
}

resource "genesys_resource_tag" "main_ivr_tag" {
  resource_id = genesys_architect_inbound_flow.main_ivr.id
  tag_id      = genesys_tag.migration_tag.id
  resource_type = "FLOW"
}

resource "genesys_resource_tag" "payment_flow_tag" {
  resource_id = genesys_architect_inbound_flow.payment_processing.id
  tag_id      = genesys_tag.migration_tag.id
  resource_type = "FLOW"
}
===FILE: terraform/alerts.tf
resource "genesys_wfm_adherence_monitor" "payment_check" {
  name        = "Payment Flow Review Monitor"
  description = "Triggers alert if payment flow requires manual review after 2024-04-01"
  enabled     = true
  schedule    = "0 4 * * 1"  # Weekly Monday at 04:00 UTC
  condition {
    property    = "payment_processing_status"
    operator    = "eq"
    value       = "needs_review"
  }
  notification_targets = [
    genesys_user_group.administrators.id
  ]
}