from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


IdentityType = Literal["CONNECT_MANAGED", "SAML", "EXISTING_DIRECTORY"]


class SkillSpec(BaseModel):
    """A Terraform-manageable routing skill: queue + routing profile."""

    name: str = Field(min_length=1, max_length=127)
    description: str = "Generated routing skill"
    channel: Literal["VOICE", "CHAT", "TASK"] = "VOICE"
    concurrency: int = Field(default=1, ge=1, le=10)
    priority: int = Field(default=1, ge=1, le=999)
    delay_seconds: int = Field(default=0, ge=0, le=9999)

    @model_validator(mode="after")
    def validate_voice_concurrency(self) -> "SkillSpec":
        if self.channel == "VOICE" and self.concurrency != 1:
            raise ValueError("VOICE concurrency must be 1")
        return self


class AgentSpec(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str | None = None
    skill_name: str = Field(description="Name of the routing skill assigned to this agent")
    phone_type: Literal["SOFT_PHONE", "DESK_PHONE"] = "SOFT_PHONE"
    desk_phone_number: str | None = None
    auto_accept: bool = False
    after_contact_work_seconds: int = Field(default=60, ge=0, le=2_000_000)

    @model_validator(mode="after")
    def validate_phone(self) -> "AgentSpec":
        if self.phone_type == "DESK_PHONE" and not self.desk_phone_number:
            raise ValueError("desk_phone_number is required for DESK_PHONE")
        if self.phone_type == "SOFT_PHONE" and self.desk_phone_number:
            raise ValueError("desk_phone_number is only valid for DESK_PHONE")
        return self


class ContactFlowSpec(BaseModel):
    name: str = Field(min_length=1, max_length=127)
    description: str = "Generated inbound contact flow"
    welcome_message: str = Field(min_length=1, max_length=1000)
    type: Literal[
        "CONTACT_FLOW", "CUSTOMER_QUEUE", "CUSTOMER_HOLD", "CUSTOMER_WHISPER",
        "AGENT_HOLD", "AGENT_WHISPER", "OUTBOUND_WHISPER", "AGENT_TRANSFER",
        "QUEUE_TRANSFER",
    ] = "CONTACT_FLOW"


class DnisSpec(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country_code: str = Field(min_length=2, max_length=2)
    number_type: Literal["DID", "TOLL_FREE"] = "DID"
    prefix: str | None = Field(default=None, description="Optional E.164 prefix such as +18005")
    contact_flow_name: str

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z]{2}", value):
            raise ValueError("country_code must be a two-letter ISO code")
        return value.upper()

    @field_validator("prefix")
    @classmethod
    def validate_prefix(cls, value: str | None) -> str | None:
        if value and not re.fullmatch(r"\+[1-9]\d{0,14}", value):
            raise ValueError("prefix must start with + and contain E.164 digits")
        return value


class ConnectInstanceSpec(BaseModel):
    """Small, auditable scope for creating one Amazon Connect instance."""

    instance_alias: str = Field(min_length=1, max_length=45)
    region: str = Field(description="AWS region, for example us-east-1")
    identity_management_type: IdentityType = "CONNECT_MANAGED"
    directory_id: str | None = None
    inbound_calls_enabled: bool = True
    outbound_calls_enabled: bool = True
    contact_flow_logs_enabled: bool = False
    contact_lens_enabled: bool = True
    auto_resolve_best_voices_enabled: bool = True
    early_media_enabled: bool = True
    multi_party_conference_enabled: bool = False
    tags: dict[str, str] = Field(default_factory=dict)
    time_zone: str = "UTC"
    skills: list[SkillSpec] = Field(default_factory=list)
    agents: list[AgentSpec] = Field(default_factory=list)
    contact_flows: list[ContactFlowSpec] = Field(default_factory=list)
    dnis: list[DnisSpec] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("instance_alias")
    @classmethod
    def validate_alias(cls, value: str) -> str:
        value = value.strip()
        if not re.fullmatch(r"[a-zA-Z0-9-]+", value):
            raise ValueError("use only letters, numbers, and hyphens")
        return value

    @field_validator("region")
    @classmethod
    def validate_region(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", value):
            raise ValueError("expected an AWS region such as us-east-1")
        return value

    @model_validator(mode="after")
    def validate_directory(self) -> "ConnectInstanceSpec":
        if self.identity_management_type == "EXISTING_DIRECTORY" and not self.directory_id:
            raise ValueError("directory_id is required for EXISTING_DIRECTORY")
        if self.identity_management_type != "EXISTING_DIRECTORY" and self.directory_id:
            raise ValueError("directory_id is only valid for EXISTING_DIRECTORY")
        skill_names = [item.name for item in self.skills]
        flow_names = [item.name for item in self.contact_flows]
        usernames = [item.username for item in self.agents]
        if len(set(skill_names)) != len(skill_names):
            raise ValueError("skill names must be unique")
        if len(set(flow_names)) != len(flow_names):
            raise ValueError("contact flow names must be unique")
        if len(set(usernames)) != len(usernames):
            raise ValueError("agent usernames must be unique")
        if self.identity_management_type != "SAML":
            long_usernames = [name for name in usernames if len(name) > 20]
            if long_usernames:
                raise ValueError(
                    "non-SAML agent usernames may not exceed 20 characters: "
                    f"{long_usernames}"
                )
        unknown_skills = {item.skill_name for item in self.agents} - set(skill_names)
        if unknown_skills:
            raise ValueError(f"agents reference unknown skills: {sorted(unknown_skills)}")
        unknown_flows = {item.contact_flow_name for item in self.dnis} - set(flow_names)
        if unknown_flows:
            raise ValueError(f"DNIS entries reference unknown contact flows: {sorted(unknown_flows)}")
        return self


class AgentResponse(BaseModel):
    spec: ConnectInstanceSpec | None = None
    summary: str = Field(description="Short confirmation of the interpreted request")
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    clarification_question: str | None = None

    @model_validator(mode="after")
    def validate_clarification_state(self) -> "AgentResponse":
        if self.spec is None and not self.clarification_question:
            raise ValueError("clarification_question is required when spec is null")
        if self.spec is not None and self.missing_fields:
            raise ValueError("missing_fields must be empty when spec is complete")
        return self
