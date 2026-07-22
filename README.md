# AWS Connect Migration Accelerator Tool

AWS Connect Migration Accelerator Tool is a local LangChain + OpenRouter + Streamlit application that turns a completed Excel requirements template into reviewed Terraform for Amazon Connect.

## What it does

- provides a downloadable `.xlsx` template with dedicated worksheets for the instance, skills, agents, contact flows, and DNIS
- accepts only the completed Excel template through the UI; there is no chat or manual-entry workflow
- uses a LangChain model through OpenRouter to normalize the workbook into a typed `ConnectInstanceSpec`
- validates identity-management rules and AWS-region syntax
- renders Terraform deterministically; the model never emits arbitrary HCL
- previews and downloads `main.tf`, `variables.tf`, and `outputs.tf` as a ZIP
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
   ```

   Do not commit `.env` or place API keys, passwords, AWS credentials, or customer data in the workbook.

   Models advertising `structured_outputs` or `response_format` on their OpenRouter model page are preferred. The application first requests strict JSON Schema output, then performs a JSON-mode generation and one repair attempt for less-capable models.

3. Start the UI:

   ```powershell
   streamlit run app.py
   ```

4. In the UI, download the requirements template, complete it, upload the saved `.xlsx` file, and select **Generate Terraform package**.

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

## AWS authentication

This app only generates files and does not require AWS credentials. Run Terraform separately using temporary AWS credentials or an assumed role, review `terraform plan`, then require human approval before `terraform apply`.

## Tests

```powershell
pytest
```
