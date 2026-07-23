from __future__ import annotations

from pydantic import ValidationError
import streamlit as st

from .models import AgentResponse, AgentSpec, ConnectInstanceSpec, ContactFlowSpec, SkillSpec
from .terraform import render_existing_dnis_contact_flow_files


def _validation_message(exc: ValidationError) -> str:
    messages = []
    for error in exc.errors():
        location = " → ".join(str(part) for part in error["loc"])
        messages.append(f"{location}: {error['msg']}")
    return "\n\n".join(messages)


def manual_builder() -> tuple[AgentResponse | None, bool]:
    """Render the compact explicit-field form used for smaller tasks."""
    st.subheader("Quick setup form")
    st.caption(
        "Create an instance with routing skills and agents. "
        "Use the Excel template when contact flows or DNIS associations are required."
    )

    count_left, count_right = st.columns(2)
    skill_count = int(
        count_left.number_input(
            "Number of skills",
            min_value=0,
            max_value=10,
            value=1,
            step=1,
            key="manual_skill_count",
        )
    )
    agent_count = int(
        count_right.number_input(
            "Number of agents",
            min_value=0,
            max_value=25,
            value=1,
            step=1,
            key="manual_agent_count",
        )
    )

    with st.form("manual_terraform_form"):
        st.markdown("#### Amazon Connect instance")
        instance_left, instance_middle, instance_right = st.columns(3)
        instance_alias = instance_left.text_input(
            "Instance alias",
            placeholder="acme-support",
        )
        region = instance_middle.text_input("AWS region", value="us-east-1")
        identity_type = instance_right.selectbox(
            "Identity management",
            ["CONNECT_MANAGED", "SAML", "EXISTING_DIRECTORY"],
        )

        option_left, option_middle, option_right = st.columns(3)
        directory_id = option_left.text_input(
            "Directory ID",
            help="Required only for EXISTING_DIRECTORY.",
        )
        time_zone = option_middle.text_input("Time zone", value="UTC")
        environment = option_right.text_input("Environment tag", value="dev")

        feature_cols = st.columns(4)
        inbound = feature_cols[0].checkbox("Inbound calls", value=True)
        outbound = feature_cols[1].checkbox("Outbound calls", value=True)
        flow_logs = feature_cols[2].checkbox("Contact-flow logs", value=False)
        contact_lens = feature_cols[3].checkbox("Contact Lens", value=True)

        skill_values = []
        if skill_count:
            st.markdown("#### Skills")
        for index in range(skill_count):
            with st.container(border=True):
                st.markdown(f"**Skill {index + 1}**")
                name_col, channel_col, concurrency_col = st.columns(3)
                name = name_col.text_input(
                    "Skill name",
                    key=f"manual_skill_name_{index}",
                    placeholder="English Support",
                )
                channel = channel_col.selectbox(
                    "Channel",
                    ["VOICE", "CHAT", "TASK"],
                    key=f"manual_skill_channel_{index}",
                )
                concurrency = concurrency_col.number_input(
                    "Concurrency",
                    min_value=1,
                    max_value=10,
                    value=1,
                    step=1,
                    key=f"manual_skill_concurrency_{index}",
                )
                description = st.text_input(
                    "Description",
                    value="Generated routing skill",
                    key=f"manual_skill_description_{index}",
                )
                routing_left, routing_right = st.columns(2)
                priority = routing_left.number_input(
                    "Priority",
                    min_value=1,
                    max_value=999,
                    value=1,
                    step=1,
                    key=f"manual_skill_priority_{index}",
                )
                delay_seconds = routing_right.number_input(
                    "Delay (seconds)",
                    min_value=0,
                    max_value=9999,
                    value=0,
                    step=1,
                    key=f"manual_skill_delay_{index}",
                )
                skill_values.append(
                    {
                        "name": name,
                        "description": description,
                        "channel": channel,
                        "concurrency": concurrency,
                        "priority": priority,
                        "delay_seconds": delay_seconds,
                    }
                )

        agent_values = []
        if agent_count:
            st.markdown("#### Agents")
            st.caption("The assigned skill must exactly match one of the skill names above.")
        for index in range(agent_count):
            with st.container(border=True):
                st.markdown(f"**Agent {index + 1}**")
                username_col, first_col, last_col = st.columns(3)
                username = username_col.text_input(
                    "Username",
                    key=f"manual_agent_username_{index}",
                    placeholder="alice",
                )
                first_name = first_col.text_input(
                    "First name",
                    key=f"manual_agent_first_{index}",
                )
                last_name = last_col.text_input(
                    "Last name",
                    key=f"manual_agent_last_{index}",
                )
                email_col, skill_col = st.columns(2)
                email = email_col.text_input(
                    "Email (optional)",
                    key=f"manual_agent_email_{index}",
                )
                skill_name = skill_col.text_input(
                    "Assigned skill",
                    key=f"manual_agent_skill_{index}",
                    placeholder="English Support",
                )
                phone_col, number_col, auto_col, acw_col = st.columns(4)
                phone_type = phone_col.selectbox(
                    "Phone type",
                    ["SOFT_PHONE", "DESK_PHONE"],
                    key=f"manual_agent_phone_type_{index}",
                )
                desk_phone = number_col.text_input(
                    "Desk number",
                    key=f"manual_agent_desk_phone_{index}",
                    placeholder="+12065550100",
                )
                auto_accept = auto_col.checkbox(
                    "Auto accept",
                    value=False,
                    key=f"manual_agent_auto_accept_{index}",
                )
                acw_seconds = acw_col.number_input(
                    "After-call work",
                    min_value=0,
                    max_value=2_000_000,
                    value=60,
                    step=1,
                    key=f"manual_agent_acw_{index}",
                )
                agent_values.append(
                    {
                        "username": username,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "skill_name": skill_name,
                        "phone_type": phone_type,
                        "desk_phone_number": desk_phone,
                        "auto_accept": auto_accept,
                        "after_contact_work_seconds": acw_seconds,
                    }
                )

        submitted = st.form_submit_button(
            "Generate Terraform from quick form",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None, False

    try:
        skills = [
            SkillSpec(
                name=value["name"].strip(),
                description=value["description"].strip() or "Generated routing skill",
                channel=value["channel"],
                concurrency=int(value["concurrency"]),
                priority=int(value["priority"]),
                delay_seconds=int(value["delay_seconds"]),
            )
            for value in skill_values
            if value["name"].strip()
        ]
        agents = [
            AgentSpec(
                username=value["username"].strip(),
                first_name=value["first_name"].strip(),
                last_name=value["last_name"].strip(),
                email=value["email"].strip() or None,
                skill_name=value["skill_name"].strip(),
                phone_type=value["phone_type"],
                desk_phone_number=value["desk_phone_number"].strip() or None,
                auto_accept=value["auto_accept"],
                after_contact_work_seconds=int(value["after_contact_work_seconds"]),
            )
            for value in agent_values
            if value["username"].strip()
        ]
        tags = {"ManagedBy": "Terraform"}
        if environment.strip():
            tags["Environment"] = environment.strip()

        spec = ConnectInstanceSpec(
            instance_alias=instance_alias,
            region=region,
            identity_management_type=identity_type,
            directory_id=directory_id.strip() or None,
            inbound_calls_enabled=inbound,
            outbound_calls_enabled=outbound,
            contact_flow_logs_enabled=flow_logs,
            contact_lens_enabled=contact_lens,
            time_zone=time_zone,
            tags=tags,
            skills=skills,
            agents=agents,
        )
        return (
            AgentResponse(
                spec=spec,
                summary=f"Validated quick-form requirements for {spec.instance_alias}.",
            ),
            True,
        )
    except ValidationError as exc:
        st.error("Please correct the form:\n\n" + _validation_message(exc))
        return None, True


def _resource_id(value: str) -> str:
    """Accept a bare ID or an AWS ARN and return its final resource segment."""
    normalized = value.strip().rstrip("/")
    if normalized.startswith("arn:") and "/" in normalized:
        return normalized.rsplit("/", 1)[-1]
    return normalized


def existing_dnis_flow_builder() -> tuple[dict[str, str] | None, bool, str | None]:
    """Render a focused form for a new flow associated with an existing DNIS."""
    st.subheader("Add contact flow to existing DNIS")
    st.caption(
        "This creates a contact flow and associates it with a phone number already claimed "
        "in Amazon Connect. It does not create an instance or claim another number."
    )

    with st.form("existing_dnis_flow_form"):
        st.markdown("#### Existing Amazon Connect resources")
        resource_left, resource_middle, resource_right = st.columns(3)
        region = resource_left.text_input(
            "AWS region",
            value="us-east-1",
            key="existing_dnis_region",
        )
        instance_id = resource_middle.text_input(
            "Connect instance ID",
            key="existing_dnis_instance_id",
            placeholder="aaaaaaaa-bbbb-cccc-dddd-111111111111",
            help="A bare instance ID or instance ARN.",
        )
        phone_number_id = resource_right.text_input(
            "Existing DNIS phone-number ID",
            key="existing_dnis_phone_number_id",
            placeholder="12345678-abcd-1234-efgh-9876543210ab",
            help="Use the Amazon Connect phone-number ID, not only the displayed E.164 number.",
        )

        st.markdown("#### New contact flow")
        flow_left, flow_right = st.columns([2, 1])
        flow_name = flow_left.text_input(
            "Contact-flow name",
            key="existing_dnis_flow_name",
            placeholder="Main Inbound Flow",
        )
        flow_type = flow_right.selectbox(
            "Flow type",
            [
                "CONTACT_FLOW",
                "CUSTOMER_QUEUE",
                "CUSTOMER_HOLD",
                "CUSTOMER_WHISPER",
                "AGENT_HOLD",
                "AGENT_WHISPER",
                "OUTBOUND_WHISPER",
                "AGENT_TRANSFER",
                "QUEUE_TRANSFER",
            ],
            key="existing_dnis_flow_type",
        )
        description = st.text_input(
            "Description",
            value="Inbound flow for an existing DNIS",
            key="existing_dnis_flow_description",
        )
        welcome_message = st.text_area(
            "Welcome message",
            key="existing_dnis_welcome_message",
            placeholder="Thank you for calling. Please hold while we connect you.",
            height=100,
        )

        submitted = st.form_submit_button(
            "Generate contact-flow association package",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return None, False, None

    normalized_instance_id = _resource_id(instance_id)
    normalized_phone_number_id = _resource_id(phone_number_id)
    if not normalized_instance_id:
        st.error("Connect instance ID is required.")
        return None, True, None
    if not normalized_phone_number_id:
        st.error("Existing DNIS phone-number ID is required.")
        return None, True, None

    try:
        flow = ContactFlowSpec(
            name=flow_name.strip(),
            description=description.strip() or "Inbound flow for an existing DNIS",
            welcome_message=welcome_message.strip(),
            type=flow_type,
        )
        files = render_existing_dnis_contact_flow_files(
            region=region.strip(),
            instance_id=normalized_instance_id,
            phone_number_id=normalized_phone_number_id,
            flow=flow,
        )
        return files, True, flow.name
    except ValidationError as exc:
        st.error("Please correct the form:\n\n" + _validation_message(exc))
        return None, True, None
