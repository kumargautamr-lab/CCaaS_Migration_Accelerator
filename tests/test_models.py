import pytest
from pydantic import ValidationError

from connect_agent.models import AgentResponse, AgentSpec, ConnectInstanceSpec, ContactFlowSpec, DnisSpec, SkillSpec


def test_existing_directory_requires_directory_id():
    with pytest.raises(ValidationError):
        ConnectInstanceSpec(
            instance_alias="helpdesk",
            region="us-east-1",
            identity_management_type="EXISTING_DIRECTORY",
        )


def test_connect_managed_rejects_directory_id():
    with pytest.raises(ValidationError):
        ConnectInstanceSpec(
            instance_alias="helpdesk",
            region="us-east-1",
            identity_management_type="CONNECT_MANAGED",
            directory_id="d-1234567890",
        )


def test_rejects_unknown_agent_skill():
    with pytest.raises(ValidationError):
        ConnectInstanceSpec(
            instance_alias="helpdesk",
            region="us-east-1",
            agents=[
                AgentSpec(
                    username="alice",
                    first_name="Alice",
                    last_name="Agent",
                    skill_name="Missing",
                )
            ],
        )


def test_rejects_unknown_dnis_flow():
    with pytest.raises(ValidationError):
        ConnectInstanceSpec(
            instance_alias="helpdesk",
            region="us-east-1",
            skills=[SkillSpec(name="English")],
            contact_flows=[ContactFlowSpec(name="Main", welcome_message="Welcome")],
            dnis=[DnisSpec(name="Sales", country_code="US", contact_flow_name="Missing")],
        )


def test_allows_typed_clarification_without_spec():
    response = AgentResponse(
        summary="More information is required.",
        missing_fields=["instance_alias", "region"],
        clarification_question="What instance alias and AWS region should I use?",
    )
    assert response.spec is None


def test_rejects_missing_spec_without_question():
    with pytest.raises(ValidationError):
        AgentResponse(summary="Incomplete")
