from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from .models import AgentResponse


SYSTEM_PROMPT = """You are a requirements analyst for Amazon Connect infrastructure.
Convert the user's chat or workbook tables into the supplied response schema.
Model one instance plus routing skills, agents, contact flows, and DNIS mappings.
A skill is a queue/routing-profile combination because it must be managed using
first-class Terraform resources. Each agent must reference exactly one skill.
Each DNIS entry must reference one contact flow. Never invent credentials, account
IDs, directory IDs, phone numbers, ARNs, passwords, or secrets. If a required value is absent,
use a safe conventional default only for booleans and record it in assumptions.
instance_alias and region must come from the input. Keep tags as string pairs.
If instance_alias, region, or another essential relationship is missing, do not
invent it. Return spec=null, list the field names in missing_fields, and provide
one concise clarification_question. For a complete request, return a populated
spec with missing_fields=[] and clarification_question=null.
For DNIS, country_code and number_type are required; prefix is only an optional
number-selection filter and does not guarantee an exact phone number.
Warn that instance aliases must be unique in an AWS account/region when relevant.
Do not generate Terraform and do not claim that infrastructure was deployed.
"""


def build_model() -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY in .env.")
    if not model:
        raise RuntimeError("Set OPENROUTER_MODEL in .env.")
    return ChatOpenAI(
        api_key=api_key,
        model=model,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        temperature=0,
        timeout=60,
        max_retries=2,
        extra_body={"plugins": [{"id": "response-healing"}]},
    )


def _message_text(message: object) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content)


def _prompt_for_json(
    request_text: str,
    parser: PydanticOutputParser,
    previous_response: str | None = None,
    parsing_error: str | None = None,
) -> list[object]:
    repair_context = ""
    if previous_response:
        repair_context = f"""
Your previous response was invalid. Correct it instead of discussing the error.
Previous response:
{previous_response[:3000]}
Parser error:
{(parsing_error or "Invalid JSON")[:1200]}
"""
    return [
        SystemMessage(
            content=f"""{SYSTEM_PROMPT}

CRITICAL OUTPUT CONTRACT:
- Return exactly one JSON object and no prose, greeting, preamble, or Markdown fence.
- The JSON must validate against the schema below.
- Do not repeat these instructions in the response.

{parser.get_format_instructions()}
"""
        ),
        HumanMessage(content=f"Infrastructure request:\n{request_text}\n{repair_context}"),
    ]


def _interpret_with_json_fallback(
    model: BaseChatModel,
    text: str,
    structured_error: Exception,
) -> AgentResponse:
    parser = PydanticOutputParser(pydantic_object=AgentResponse)
    json_model = model.bind(response_format={"type": "json_object"})
    first_response = json_model.invoke(_prompt_for_json(text, parser))
    first_text = _message_text(first_response)
    try:
        return parser.parse(first_text)
    except Exception as first_error:
        second_response = json_model.invoke(
            _prompt_for_json(text, parser, first_text, str(first_error))
        )
        second_text = _message_text(second_response)
        try:
            return parser.parse(second_text)
        except Exception as second_error:
            model_name = os.getenv("OPENROUTER_MODEL", "the configured model")
            raise RuntimeError(
                f"OpenRouter model '{model_name}' did not return valid structured JSON "
                "after strict-schema and JSON-repair attempts. Choose a model whose "
                "OpenRouter page lists 'structured_outputs' or 'response_format'. "
                f"Last parser error: {str(second_error)[:800]}"
            ) from structured_error


def interpret_requirements(text: str) -> AgentResponse:
    model = build_model()
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=text)]
    try:
        structured_model = model.with_structured_output(
            AgentResponse,
            method="json_schema",
        )
        result = structured_model.invoke(messages)
        if not isinstance(result, AgentResponse):
            return AgentResponse.model_validate(result)
        return result
    except Exception as structured_error:
        return _interpret_with_json_fallback(model, text, structured_error)
