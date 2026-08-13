```terraform
terraform {
  required_providers {
    genesyscloud = {
      source  = "registry.terraform.io/mygenesyscloud/genesyscloud"
      version = "1.0.0"
    }
  }
}

provider "genesyscloud" {
}

# ============================================================
# Prompt: welcome_prompt (mapped from ann_welcome_44801.wav)
# ============================================================
resource "genesyscloud_architect_prompt" "welcome_prompt" {
  name        = "welcome_prompt"
  description = "Mapped from Avaya announcement: ann_welcome_44801.wav"
  durations   = {}
  input_port  = {}
  languages   = []
  mappings    = []
  prompts     = [
    {
      language = "en-us"
      voice    = "bryson"
      text     = "Thank you for calling. Please listen carefully as our menu options have changed."
      type     = "tts"
    }
  ]
}

# ============================================================
# Skill: VIP Skill (mapped from VIP_EAS_Skill) — status: Review
# ============================================================
resource "genesyscloud_routing_skill_v2" "vip_skill" {
  name        = "VIP Skill"
  description = "Mapped from Avaya Skill: VIP_EAS_Skill (mapping score 72 — REVIEW)"
}

# ============================================================
# Skill: VIP_EAS_Skill — mapped but needs review. 
# Placeholder until confirmed.
# ============================================================
resource "genesyscloud_routing_skill_v2" "vip_eas_skill_review" {
  name        = "VIP_EAS_Skill_Review"
  description = "Mapped from Avaya Skill: VIP_EAS_Skill — pending review of behavior and scoring logic"
}
```

### Notes:
- `welcome_prompt` uses a TTS placeholder based on typical IVR welcome messages since the original `.wav` file must be manually uploaded to Genesys Cloud.
- `VIP Skill` is provisioned as an ACD Skill due to the low mapping confidence (score=72).
- A duplicate placeholder (`VIP_EAS_Skill_Review`) is included for traceability during stakeholder validation.
- Other items like adjunct routes or unsupported components are excluded per your migration scope.

Let me know if you'd like Terraform definitions for flows, schedules, or queues next.