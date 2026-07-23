from io import BytesIO

import pandas as pd

from connect_agent.input_parser import workbook_to_spec


def _template_bytes() -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "instance_alias": "acme-support",
                    "region": "us-east-1",
                    "identity_management_type": "CONNECT_MANAGED",
                    "inbound_calls_enabled": "true",
                    "outbound_calls_enabled": "true",
                    "tag_environment": "dev",
                }
            ]
        ).to_excel(writer, sheet_name="Instance", index=False)
        pd.DataFrame(
            [{"name": "Support", "channel": "VOICE", "concurrency": "1"}]
        ).to_excel(writer, sheet_name="Skills", index=False)
        pd.DataFrame(
            [
                {
                    "username": "agent1",
                    "first_name": "Sample",
                    "last_name": "Agent",
                    "skill_name": "Support",
                    "phone_type": "SOFT_PHONE",
                }
            ]
        ).to_excel(writer, sheet_name="Agents", index=False)
    return buffer.getvalue()


def test_template_workbook_is_parsed_without_a_model():
    spec = workbook_to_spec(_template_bytes())
    assert spec.instance_alias == "acme-support"
    assert spec.tags == {"Environment": "dev"}
    assert spec.skills[0].name == "Support"
    assert spec.agents[0].skill_name == "Support"
