from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

from connect_agent.agent import interpret_requirements
from connect_agent.input_parser import workbook_to_prompt
from connect_agent.models import AgentResponse
from connect_agent.terraform import files_to_zip, render_files


load_dotenv()
st.set_page_config(
    page_title="AWS Connect Migration Accelerator Tool",
    page_icon="☁️",
    layout="wide",
)

st.markdown(
    """
<style>
:root {
  --navy: #020617;
  --navy-panel: #071a3d;
  --navy-soft: #0b2554;
  --gold: #f6c453;
  --gold-bright: #ffe59a;
  --gold-muted: #d9bd79;
  --grey: #9ca3af;
  --border: rgba(246, 196, 83, .34);
}

.stApp {
  color: var(--gold-bright);
  background:
    radial-gradient(circle at 12% 4%, rgba(36, 139, 255, .18), transparent 28rem),
    linear-gradient(145deg, var(--navy), #03112d 52%, #020617);
}

.block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}

h1, h2, h3, p, label, .stMarkdown, [data-testid="stWidgetLabel"] {
  color: var(--gold-bright) !important;
}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #061633, #020b1f) !important;
  border-right: 1px solid var(--border);
}

[data-testid="stFileUploaderDropzone"], [data-testid="stMetric"],
[data-testid="stExpander"], div[data-testid="stCodeBlock"] {
  background: rgba(7, 26, 61, .9) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzoneInstructions"] div,
.stCaption {color: var(--gold-muted) !important;}

.stButton > button, .stDownloadButton > button {
  color: #031a45 !important;
  font-weight: 800 !important;
  background: linear-gradient(135deg, var(--gold), var(--gold-bright)) !important;
  border: 1px solid #fff1bd !important;
  border-radius: 10px !important;
  box-shadow: 0 0 18px rgba(246, 196, 83, .24);
}

.stDownloadButton > button p,
.stDownloadButton > button span,
.stDownloadButton > button div {
  color: #031a45 !important;
  font-weight: 900 !important;
}

.stButton > button:disabled {
  color: #031a45 !important;
  background: linear-gradient(135deg, var(--gold), var(--gold-bright)) !important;
  border-color: #fff1bd !important;
  box-shadow: 0 0 18px rgba(246, 196, 83, .18);
  opacity: .68;
}

.stButton > button:disabled p,
.stButton > button:disabled span,
.stButton > button:disabled div {
  color: #031a45 !important;
  font-weight: 900 !important;
}

.app-header {
  margin: 0 auto 1.4rem;
  padding: .35rem 0 1rem;
  text-align: center;
  border-bottom: 1px solid var(--border);
}

.app-header h1 {
  margin: 0 !important;
  line-height: 1.1;
  font-size: 2.2rem;
}

.app-header p {
  margin: .35rem 0 0 !important;
  color: var(--gold-muted) !important;
  font-size: .98rem;
}

.muted {color: var(--gold-muted) !important;}
hr {border-color: var(--border);}

footer, [data-testid="stFooter"] {
  color: var(--gold-muted) !important;
  border-top: 1px solid var(--border);
  background: linear-gradient(90deg, #020b1f, #071a3d, #020b1f) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<header class="app-header"><h1>AWS Connect Migration Accelerator Tool</h1>'
    '<p>Legacy &rarr; Terraform &rarr; AWS Connect</p></header>',
    unsafe_allow_html=True,
)


def show_package(response: AgentResponse, key_prefix: str) -> None:
    if response.spec is None:
        raise ValueError("Cannot render Terraform until required fields are provided.")

    files = render_files(response.spec)
    st.success(response.summary)
    metrics = st.columns(4)
    metrics[0].metric("Skills", len(response.spec.skills))
    metrics[1].metric("Agents", len(response.spec.agents))
    metrics[2].metric("Flows", len(response.spec.contact_flows))
    metrics[3].metric("DNIS", len(response.spec.dnis))

    left, right = st.columns([1, 1.4])
    with left:
        st.subheader("Validated specification")
        st.json(response.spec.model_dump(exclude={"assumptions"}))
        if response.spec.assumptions:
            st.info("Assumptions: " + "; ".join(response.spec.assumptions))
        for warning in response.warnings:
            st.warning(warning)
    with right:
        st.subheader("Terraform preview")
        selected = st.selectbox(
            "File", list(files), key=f"{key_prefix}_file", label_visibility="collapsed"
        )
        st.code(files[selected], language="hcl")

    st.download_button(
        "Download Terraform package",
        data=files_to_zip(files),
        file_name=f"{response.spec.instance_alias}-terraform.zip",
        mime="application/zip",
        type="primary",
        key=f"{key_prefix}_download",
    )


with st.sidebar:
    st.caption("AI provider: OpenRouter")
    st.subheader("Workbook workflow")
    st.markdown(
        "1. Download the template\n\n"
        "2. Complete its six worksheets\n\n"
        "3. Upload the completed `.xlsx` file"
    )
    st.divider()
    st.subheader("Guardrails")
    st.markdown(
        "✓ Typed requirements\n\n"
        "✓ Deterministic HCL\n\n"
        "✓ No Terraform apply\n\n"
        "✓ Human plan review"
    )

template_path = (
    Path(__file__).resolve().parent
    / "outputs"
    / "connectcraft"
    / "amazon_connect_requirements_template.xlsx"
)

st.subheader("1. Download the requirements template")
st.markdown(
    "Use the dedicated **Instance**, **Skills**, **Agents**, **ContactFlows**, and **DNIS** "
    "worksheets. The workbook includes instructions, examples, and validation lists."
)
if template_path.exists():
    st.download_button(
        "Download Excel template",
        data=template_path.read_bytes(),
        file_name=template_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
else:
    st.error("The requirements template is missing from the application package.")

st.divider()
st.subheader("2. Upload the completed template")
upload = st.file_uploader(
    "Completed Amazon Connect requirements workbook",
    type=["xlsx"],
    help="Do not include passwords, API keys, AWS credentials, or customer data.",
)
generate_clicked = st.button(
    "Generate Terraform package",
    type="primary",
    use_container_width=True,
    disabled=upload is None,
)

if generate_clicked and upload is not None:
    try:
        request_text = workbook_to_prompt(upload.getvalue(), upload.name)
        with st.spinner("Interpreting and validating workbook requirements…"):
            response = interpret_requirements(request_text)
        if response.spec is None:
            clarification = response.clarification_question or response.summary
            missing = ", ".join(response.missing_fields)
            detail = f" Required fields: {missing}." if missing else ""
            raise ValueError(f"{clarification}{detail}")
        st.session_state.upload_response = response
        st.session_state.upload_source = upload.name
    except Exception as exc:
        st.session_state.pop("upload_response", None)
        st.session_state.pop("upload_source", None)
        st.error(f"I couldn’t generate the package: {exc}")

if (
    upload is not None
    and st.session_state.get("upload_source") == upload.name
    and "upload_response" in st.session_state
):
    st.divider()
    show_package(st.session_state.upload_response, "upload")
