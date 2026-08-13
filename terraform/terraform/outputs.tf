output "main_ivc_inbound_flow_id" {
  value = genesys_architect_inbound_flow.main_ivr.id
}

output "general_queue_id" {
  value = genesys_queue.general_queue.id
}

output "vip_skill_id" {
  value = genesys_routing_skill.vip_skill.id
}

output "holiday_group_arn" {
  value = genesys_architect_schedule_group.holiday_group.arn
}

output "welcome_prompt_version" {
  value = genesys_architect_prompt.welcome_prompt.version
}