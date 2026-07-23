from connect_agent.models import AgentSpec, ConnectInstanceSpec, ContactFlowSpec, DnisSpec, SkillSpec
from connect_agent.terraform import render_existing_dnis_contact_flow_files, render_files
import pytest


def test_renders_connect_resource_without_directory():
    files = render_files(
        ConnectInstanceSpec(
            instance_alias="acme-support",
            region="us-east-1",
            tags={"Environment": "dev"},
        )
    )
    main = files["main.tf"]
    assert 'resource "aws_connect_instance" "acme_support"' in main
    assert 'instance_alias                   = "acme-support"' in main
    assert "directory_id" not in main
    assert '"Environment" = "dev"' in main


def test_renders_directory_when_requested():
    files = render_files(
        ConnectInstanceSpec(
            instance_alias="corp-help",
            region="eu-west-1",
            identity_management_type="EXISTING_DIRECTORY",
            directory_id="d-1234567890",
        )
    )
    assert 'directory_id             = "d-1234567890"' in files["main.tf"]


def test_renders_skill_agent_flow_and_dnis_association():
    spec = ConnectInstanceSpec(
        instance_alias="contact-center",
        region="us-east-1",
        skills=[SkillSpec(name="English")],
        agents=[AgentSpec(username="alice", first_name="Alice", last_name="Agent", skill_name="English")],
        contact_flows=[ContactFlowSpec(name="Main", welcome_message="Welcome")],
        dnis=[DnisSpec(name="Main Line", country_code="US", contact_flow_name="Main")],
    )
    files = render_files(spec)
    main = files["main.tf"]
    assert 'resource "aws_connect_queue" "english"' in main
    assert 'resource "aws_connect_routing_profile" "english"' in main
    assert 'resource "aws_connect_user" "alice"' in main
    assert 'resource "aws_connect_contact_flow" "main"' in main
    assert 'resource "aws_connect_phone_number_contact_flow_association" "main_line"' in main
    assert 'password = var.agent_passwords["alice"]' in main
    assert "terraform.tfvars.example" in files


def test_rejects_normalized_resource_name_collision():
    spec = ConnectInstanceSpec(
        instance_alias="contact-center",
        region="us-east-1",
        skills=[SkillSpec(name="English-US"), SkillSpec(name="English_US")],
    )
    with pytest.raises(ValueError, match="collide"):
        render_files(spec)


def test_escapes_terraform_interpolation_in_flow_message():
    spec = ConnectInstanceSpec(
        instance_alias="contact-center",
        region="us-east-1",
        contact_flows=[ContactFlowSpec(name="Main", welcome_message="Hello ${danger}")],
    )
    assert "$${danger}" in render_files(spec)["main.tf"]


def test_renders_existing_dnis_contact_flow_association_without_claiming_number():
    files = render_existing_dnis_contact_flow_files(
        region="us-east-1",
        instance_id="instance-id",
        phone_number_id="phone-number-id",
        flow=ContactFlowSpec(name="Existing DNIS Flow", welcome_message="Welcome"),
    )
    main = files["main.tf"]
    assert 'resource "aws_connect_contact_flow" "existing_dnis_flow"' in main
    assert 'resource "aws_connect_phone_number_contact_flow_association" "existing_dnis_flow"' in main
    assert "resource \"aws_connect_phone_number\"" not in main
    assert "var.existing_dnis_phone_number_id" in main
