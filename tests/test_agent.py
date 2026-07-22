from connect_agent.agent import _message_text, _prompt_for_json
from connect_agent.models import AgentResponse
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser


def test_message_text_handles_string_content():
    assert _message_text(AIMessage(content='{"ok": true}')) == '{"ok": true}'


def test_message_text_handles_content_blocks():
    message = AIMessage(content=[{"type": "text", "text": '{"ok": true}'}])
    assert _message_text(message) == '{"ok": true}'


def test_json_prompt_forbids_prose_and_includes_schema():
    parser = PydanticOutputParser(pydantic_object=AgentResponse)
    messages = _prompt_for_json("Create support", parser)
    system_text = messages[0].content
    assert "Return exactly one JSON object" in system_text
    assert '"spec"' in system_text
