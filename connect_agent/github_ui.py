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


# Scoped styling so the GitHub buttons match the "Download Terraform package"
# button: black font on a light button (the default white text was invisible
# against a light background). Streamlit tags each keyed widget's container with
# a ``st-key-<key>`` class, so this targets only the GitHub deploy/confirm/cancel
# buttons and leaves the app's other buttons alone.
_BUTTON_STYLE = """
<style>
.st-key-_github_deploy button p,
[class*="st-key-"][class*="_github_confirm_btn"] button p,
[class*="st-key-"][class*="_github_cancel_btn"] button p {
    color: #000000 !important;
}

.st-key-_github_deploy button:hover,
[class*="st-key-"][class*="_github_confirm_btn"] button:hover,
[class*="st-key-"][class*="_github_cancel_btn"] button:hover {
    color: #000000 !important;
    border: 1px solid rgba(0, 0, 0, 0.45) !important;
}
</style>
"""


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
    default_commit_message: str = "Add generated Amazon Connect Terraform",
) -> None:
    """Render a button that commits ``files`` to a GitHub repository.

    The GitHub token is read from the server environment (``GITHUB_TOKEN``) and
    is never shown or entered in the UI, so credentials stay server-side. Repo,
    branch, and target directory remain editable so operators can retarget a
    commit. Committing is a two-step, confirm-first action to avoid accidental
    writes to the shared repository. This never runs Terraform.
    """
    defaults = github_defaults_from_env()
    token = (defaults["token"] or "").strip()

    result_key = f"{key_prefix}_github_result"
    confirm_key = f"{key_prefix}_github_confirm"

    with st.expander("Deploy Terraform to GitHub", expanded=False):
        if not token:
            st.info(
                "GitHub deployment is not configured. Set `GITHUB_TOKEN` in the "
                "server environment (a fine-grained token with **Contents: write** "
                "on the target repository) to enable the deploy button."
            )
            if result_key in st.session_state:
                _render_result(st.session_state[result_key])
            return

        st.markdown(_BUTTON_STYLE, unsafe_allow_html=True)
        st.caption(
            "Commit the generated files directly to the configured GitHub repository "
            "as a single commit. The GitHub token is read from the server environment "
            "and is never entered here. This never runs Terraform."
        )

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
            value=defaults["target_directory"],
            key=f"{key_prefix}_github_dir",
            help="Repository-relative folder for the files. Leave blank for the root.",
        )
        commit_message = st.text_input(
            "Commit message",
            value=default_commit_message,
            key=f"{key_prefix}_github_message",
        )

        repo_clean = repo_full_name.strip()
        branch_clean = branch.strip() or "main"

        if not st.session_state.get(confirm_key):
            if st.button(
                "Deploy to GitHub",
                type="primary",
                use_container_width=True,
                key="_github_deploy",
            ):
                if not repo_clean:
                    st.error("Repository is required, in owner/name form.")
                else:
                    st.session_state[confirm_key] = True
                    st.rerun()
        else:
            st.warning(
                f"Commit {len(files)} file(s) to `{repo_clean}` on branch "
                f"`{branch_clean}`?"
            )
            col_confirm, col_cancel = st.columns(2)
            confirmed = col_confirm.button(
                "Confirm commit",
                type="primary",
                use_container_width=True,
                key=f"{key_prefix}_github_confirm_btn",
            )
            cancelled = col_cancel.button(
                "Cancel",
                use_container_width=True,
                key=f"{key_prefix}_github_cancel_btn",
            )
            if cancelled:
                st.session_state.pop(confirm_key, None)
                st.rerun()
            elif confirmed:
                st.session_state.pop(confirm_key, None)
                config = GitHubConfig(
                    token=token,
                    repo_full_name=repo_clean,
                    branch=branch_clean,
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

        if result_key in st.session_state and not st.session_state.get(confirm_key):
            _render_result(st.session_state[result_key])
