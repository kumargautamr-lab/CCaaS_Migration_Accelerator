resource "genesys_architect_prompt" "welcome_prompt" {
  name        = "welcome_prompt"
  description = "Welcome message from Avaya VDN-44801"
}

resource "genesys_queue" "general_queue" {
  name        = "General Queue"
  description = "Mapped from Avaya General_Split_1"
}

resource "genesys_routing_skill" "vip_skill" {
  name        = "VIP Skill"
  description = "Mapped from Avaya VIP_EAS_Skill"
}

resource "genesys_architect_schedule_group" "holiday_group" {
  name        = "Holiday Schedule Group"
  description = "Mapped from Avaya HolidayTable_03"
  timezone    = "America/New_York"
  schedules   = [] # Populate with holiday schedule entries
}

resource "genesys_architect_inbound_flow" "main_ivr" {
  name        = "Main Inbound Flow"
  description = "Mapped from Avaya Main_IVR_v3 (VDN-44801)"
  body = <<JSON
{
  "$": {
    "name": "Main Inbound Flow",
    "type": "inbound",
    "version": 1,
    "definition": {
      "workflow": {
        "$": {
          "$value": [
            {
              "id": "Play Welcome",
              "name": "Play Welcome",
              "type": "com.genesys.playprompt",
              "parameters": {
                "prompt": {
                  "id": "${genesys_architect_prompt.welcome_prompt.id}",
                  "type": "Prompt"
                }
              }
            },
            {
              "id": "Route General",
              "name": "Route General",
              "type": "com.genesys.routetotarget",
              "parameters": {
                "target": {
                  "id": "${genesys_queue.general_queue.id}",
                  "type": "QUEUE"
                }
              }
            }
          ]
        }
      }
    }
  }
}
JSON
}

resource "genesys_architect_inbound_flow" "sales_inquiry" {
  name        = "Sales Inquiry Inbound Flow"
  description = "Mapped from Avaya Sales Inquiry Vector (VDN-44802)"
  body = <<JSON
{
  "$": {
    "name": "Sales Inquiry Inbound Flow",
    "type": "inbound",
    "version": 1
  }
}
JSON
}

resource "genesys_architect_inbound_flow" "payment_processing" {
  name        = "Payment Processing Inbound Flow"
  description = "Mapped from Avaya Payment Vector (VDN-44810) - Manual Review Required"
  body = <<JSON
{
  "$": {
    "name": "Payment Processing Inbound Flow",
    "type": "inbound",
    "version": 1
  }
}
JSON
}

# TODO: CRM_DataDip (ASAI) requires custom Data Action rebuild - unsupported by Terraform