```hcl
provider "genesyscloud" {
  client_id     = var.genesyscloud_client_id
  client_secret = var.genesyscloud_client_secret
  base_path     = "/api/v2"
  region        = var.genesyscloud_region
}

resource "genesyscloud_routing_queue" "general_queue" {
  name        = "General Queue"
  description = "Mapped from Avaya Split SPL-001"
}

resource "genesyscloud_routing_skill" "vip_skill" {
  name        = "VIP_Skill"
  description = "Mapped from Avaya Skill SK-004 (under review)"
}

resource "genesyscloud_routing_skill" "customer_service_skill" {
  name        = "Customer_Service_Skill"
  description = "Mapped from Avaya Vector VDN-44801 (high complexity)"
}

resource "genesyscloud_routing_schedule" "holiday_schedule" {
  name     = "Holiday_Schedule_03"
  schedule = "holiday"
  # Add actual holiday date ranges here based on Holiday Table configuration
}

resource "genesyscloud_routing_schedule_group" "holiday_schedule_group" {
  name = "Holiday Schedule Group"
  schedules = [genesyscloud_routing_schedule.holiday_schedule.id]
}

resource "genesyscloud_architect_flow" "main_ivrc_flow" {
  name        = "Main_IVR_Flow"
  description = "Mapped from Avaya Vector VDN-44801 (Main IVR - Customer Service)"
  type        = "inbound"
  # Flow configuration (abbreviated):
  # - Play welcome_prompt greeting
  # - Route to general_queue after menu interaction
  # - Reference vip_skill for VIP routing
}

resource "genesyscloud_architect_flow" "sales_inquiry_flow" {
  name        = "Sales_Inquiry_Flow"
  description = "Mapped from Avaya Vector VDN-44802"
  type        = "inbound"
}

resource "genesyscloud_architect_flow" "payment_flow" {
  name        = "Payment_Processing_Flow"
  description = "Mapped from Avaya Vector VDN-44810 (under review)"
  type        = "inbound"
}

# Prompts (example for one prompt; repeat for others)
resource "genesyscloud_prompt" "welcome_prompt" {
  name        = "welcome_prompt"
  description = "Mapped from ann_welcome_44801.wav"
  language    = "en-US"
  audio {
    media_v2 = {
      upload = {
        key = var.welcome_prompt_s3_key
      }
    }
  }
}

# Custom build for unsupported adjunct route
resource "genesyscloud_integration" "crmsystem_integration" {
  name        = "Custom_CRM_Integration"
  description = "Rebuilt from Avaya Adjunct Route ADJ-001 (ASAI link)"
  integration_type = "custom"
  # Configuration for external CTI data dip integration
  config {
    # Integration-specific config
  }
}
```

Notes:
1. Variables like `genesyscloud_client_id`, `genesyscloud_region`, and `welcome_prompt_s3_key` must be defined in a `variables.tf`
2. Payment flow and Sales inquiry flow require additional configuration based on original Avaya Vector logic
3. Holiday schedule requires actual date ranges in `genesyscloud_routing_schedule`
4. Custom integration requires full implementation of Data Action equivalent to ASAI link
5. VIP_Skill needs to be linked to appropriate agent groups in UI or via additional Terraform resources