"""Streamlit panel for committing generated Terraform to a GitHub repository."""

from __future__ import annotations

import streamlit as st

from .github_publisher import (
    GitHubConfig,
    GitHubPublishError,
    PublishResult,
    github_defaults_from_env,
    publish_files,
)


def _render_result(result: PublishResult) -> None:
    verb = "Created branch and committed" if result.branch_created else "Committed"
    st.success(
        f"{verb} {len(result.file_paths)} file(s) to "
        f"`{result.repo_full_name}` on branch `{result.branch}`."
    )
    st.markdown(f"[View commit {result.commit_sha[:7]}]({result.commit_url})")
    st.caption("Committed paths:\n\n" + "\n\n".join(f"- `{path}`" for path in result.file_paths))


def github_publish_panel(
    files: dict[str, str],
    *,
    key_prefix: str,
    default_directory: str = "terraform",
    default_commit_message: str = "Add generated Amazon Connect Terraform",
) -> None:
    """Render a form that commits ``files`` to a GitHub repository on submit.

    The panel is deliberately opt-in (collapsed) and per-request: the token is
    never persisted by the app, and the last successful result is kept in
    session state only so it survives Streamlit reruns.
    """
    defaults = github_defaults_from_env()
    result_key = f"{key_prefix}_github_result"

    with st.expander("Publish Terraform to GitHub", expanded=False):
        st.caption(
            "Commit the generated files directly to a GitHub repository as a single "
            "commit. Use a fine-grained personal access token with **Contents: write** "
            "permission on the target repository. This never runs Terraform."
        )
        with st.form(f"{key_prefix}_github_form"):
            repo_full_name = st.text_input(
                "Repository (owner/name)",
                value=defaults["repo_full_name"] or "",
                key=f"{key_prefix}_github_repo",
                placeholder="my-org/connect-infra",
            )
            col_branch, col_dir = st.columns(2)
            branch = col_branch.text_input(
                "Branch",
                value=defaults["branch"],
                key=f"{key_prefix}_github_branch",
                help="Created from the default branch if it does not exist yet.",
            )
            target_directory = col_dir.text_input(
                "Target directory",
                value=default_directory or defaults["target_directory"],
                key=f"{key_prefix}_github_dir",
                help="Repository-relative folder for the files. Leave blank for the root.",
            )
            token = st.text_input(
                "GitHub token",
                value=defaults["token"] or "",
                type="password",
                key=f"{key_prefix}_github_token",
                help="Used only for this request. Prefill with GITHUB_TOKEN in .env for local use.",
            )
            commit_message = st.text_input(
                "Commit message",
                value=default_commit_message,
                key=f"{key_prefix}_github_message",
            )
            submitted = st.form_submit_button(
                "Commit files to GitHub",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not repo_full_name.strip():
                st.error("Repository is required, in owner/name form.")
            elif not token.strip():
                st.error("A GitHub token is required.")
            else:
                config = GitHubConfig(
                    token=token.strip(),
                    repo_full_name=repo_full_name.strip(),
                    branch=branch.strip() or "main",
                    target_directory=target_directory.strip(),
                    base_url=defaults["base_url"],
                )
                try:
                    with st.spinner("Committing files to GitHub…"):
                        result = publish_files(
                            config,
                            files,
                            commit_message.strip() or default_commit_message,
                        )
                except GitHubPublishError as exc:
                    st.session_state.pop(result_key, None)
                    st.error(f"GitHub publish failed: {exc}")
                else:
                    st.session_state[result_key] = result
                    _render_result(result)
        elif result_key in st.session_state:
            _render_result(st.session_state[result_key])
