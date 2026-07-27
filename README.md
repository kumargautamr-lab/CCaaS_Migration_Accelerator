# AWS Connect Migration Accelerator Tool

AWS Connect Migration Accelerator Tool is a local LangChain + OpenRouter + Streamlit application that turns a completed Excel requirements template into reviewed Terraform for Amazon Connect.

## What it does

- provides a downloadable `.xlsx` template with dedicated worksheets for the instance, skills, agents, contact flows, and DNIS
- accepts a completed Excel template or a deterministic quick form; there is no chat workflow
- parses the downloadable template deterministically into a typed `ConnectInstanceSpec`
- uses a LangChain model through OpenRouter only as a fallback for non-template workbooks
- validates identity-management rules and AWS-region syntax
- renders Terraform deterministically; the model never emits arbitrary HCL
- previews and downloads `main.tf`, `variables.tf`, and `outputs.tf` as a ZIP
- optionally commits the same generated files straight to a GitHub repository (PyGithub)
- creates routing skills as queues plus routing profiles and assigns agents to them
- creates users whose initial passwords are supplied only through a sensitive Terraform variable
- creates JSON contact flows using the Amazon Connect Flow language
- claims DID or toll-free DNIS numbers and associates each number with a contact flow
- never runs `terraform apply`

## Quick start

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`, then configure your OpenRouter API key and model slug:

   ```dotenv
   OPENROUTER_API_KEY=your-key-here
   OPENROUTER_MODEL=provider/model-slug
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   OPENROUTER_MAX_TOKENS=8192
   ```

   Do not commit `.env` or place API keys, passwords, AWS credentials, or customer data in the workbook.

   The completed downloadable template is parsed locally and does not call OpenRouter. For non-template workbooks, models advertising `structured_outputs` or `response_format` are preferred. The fallback requests strict JSON Schema output, then performs a JSON-mode generation and one repair attempt.

3. Start the UI:

   ```powershell
   streamlit run app.py
   ```

4. In the UI, either upload a completed requirements template or use the quick form for a smaller task.

## Quick form

The quick form creates Terraform without calling the AI model. It uses explicit fields for Amazon Connect instance settings, skills, and agents. An agent's assigned skill must exactly match a skill name. Use the Excel template for contact flows and DNIS-to-contact-flow associations.

The focused **Add contact flow to existing DNIS** form is available for a smaller association task. It accepts an existing Connect instance ID and Amazon Connect phone-number ID, creates the new contact flow, and generates only the Terraform association package. It does not claim a new number or create another Connect instance.

## Excel template

The template contains these worksheets:

- `Instructions`: guidance only; this worksheet is ignored during generation
- `Instance`: Amazon Connect alias, region, identity management, telephony options, and tags
- `Skills`: queues and routing profiles used to implement routing skills
- `Agents`: users and their skill associations
- `ContactFlows`: inbound contact flow definitions
- `DNIS`: phone-number requests and contact-flow associations

Keep the column names intact. Add one item per row to the repeating worksheets. Agent rows must reference a skill name, and DNIS rows must reference a contact-flow name.

## Skill mapping

The HashiCorp AWS provider does not currently expose Amazon Connect user proficiencies as a first-class Terraform resource. To preserve the Terraform-only requirement, the application models a skill as a queue plus routing profile. Each generated agent is assigned to one routing profile. It does not generate CLI provisioners.

## DNIS behavior

Terraform can claim an available number by country, type, and optional E.164 prefix, then associate it with a contact flow. A prefix filters available inventory; it does not guarantee that AWS will allocate one exact phone number. Existing numbers need to be imported into Terraform state first.

## Publish to GitHub

Every generated package has a **Publish Terraform to GitHub** panel next to its
download button. It commits the exact files from the download — `main.tf`,
`variables.tf`, `outputs.tf`, and `terraform.tfvars.example` when present — to a
repository you own, using [PyGithub](https://pygithub.readthedocs.io/) and the
GitHub Git Data API. All files land in a single atomic commit so the committed
tree always matches the ZIP.

In the panel, supply:

- **Repository** in `owner/name` form
- **Branch** to commit to (created from the repository's default branch if it does not exist)
- **Target directory** for the files (leave blank to commit to the repository root)
- **GitHub token** — a fine-grained personal access token with **Contents: write**
  permission on the target repository
- **Commit message**

The token is used only for that single request and is never written to disk by the
application. For local convenience you can prefill the form by setting `GITHUB_TOKEN`,
`GITHUB_REPOSITORY`, `GITHUB_BRANCH`, and `GITHUB_TARGET_DIRECTORY` in `.env`; set
`GITHUB_API_URL` to target GitHub Enterprise Server. Never commit real tokens.

Publishing writes source files only. As with the downloaded package, the tool never
runs `terraform plan` or `terraform apply` — review the committed files and run
Terraform separately with human approval.

Do not enable `terraform.tfvars` for commit: the `.gitignore` in this project ignores
it, and the generated `terraform.tfvars.example` only contains placeholder secrets.

## AWS authentication

This app only generates files and does not require AWS credentials. Run Terraform separately using temporary AWS credentials or an assumed role, review `terraform plan`, then require human approval before `terraform apply`.

## Tests

```powershell
pytest
```
