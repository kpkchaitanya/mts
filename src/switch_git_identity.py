"""
switch_git_identity.py

Set global Git identity using account mappings in a .properties file.

Usage:
    python -m src.switch_git_identity --account-name personal --properties config/git_identity.properties
"""

import argparse
import subprocess
from pathlib import Path


def parse_properties(properties_path: Path) -> dict[str, str]:
    """Parse a simple .properties file with key=value pairs."""
    if not properties_path.exists():
        raise FileNotFoundError(f"Properties file not found: {properties_path}")

    data: dict[str, str] = {}
    with properties_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            content = line.strip()
            if not content or content.startswith("#") or content.startswith("!"):
                continue
            if "=" not in content:
                continue
            key, value = content.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def list_configured_accounts(properties: dict[str, str]) -> list[str]:
    """Return configured account names from property keys."""
    accounts: set[str] = set()
    prefix = "git.account."
    suffixes = (".username", ".email")

    for key in properties:
        if not key.startswith(prefix):
            continue
        for suffix in suffixes:
            if key.endswith(suffix):
                account_name = key[len(prefix):-len(suffix)]
                if account_name:
                    accounts.add(account_name)
    return sorted(accounts)


def resolve_identity(properties: dict[str, str], account_name: str) -> tuple[str, str]:
    """Resolve username/email for a given account name."""
    normalized_account = account_name.strip()
    if not normalized_account:
        raise ValueError("Account name cannot be empty.")

    username_key = f"git.account.{normalized_account}.username"
    email_key = f"git.account.{normalized_account}.email"

    username = properties.get(username_key, "").strip()
    email = properties.get(email_key, "").strip()

    if username and email:
        return username, email

    available_accounts = list_configured_accounts(properties)
    available_text = ", ".join(available_accounts) if available_accounts else "none"
    raise ValueError(
        "Invalid or incomplete account mapping for "
        f"'{normalized_account}'. Required keys: '{username_key}' and '{email_key}'. "
        f"Configured accounts: {available_text}."
    )


def run_switch_git_identity(account_name: str, properties_path: Path, dry_run: bool = False) -> None:
    """Set global git user.name and user.email from account mapping values."""
    props = parse_properties(properties_path)
    username, email = resolve_identity(props, account_name)

    print(f"[MTS] Properties file: {properties_path}")
    print(f"[MTS] account.name => {account_name}")
    print(f"[MTS] user.name => {username}")
    print(f"[MTS] user.email => {email}")

    if dry_run:
        print("[MTS] Dry run enabled. No git config changes were applied.")
        return

    subprocess.run(["git", "config", "--global", "user.name", username], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)

    configured_name = subprocess.check_output(
        ["git", "config", "--global", "user.name"],
        text=True,
    ).strip()
    configured_email = subprocess.check_output(
        ["git", "config", "--global", "user.email"],
        text=True,
    ).strip()
    verification_lines = subprocess.check_output(
        ["git", "config", "--global", "--list"],
        text=True,
    ).splitlines()
    identity_lines = [
        line
        for line in verification_lines
        if line.startswith("user.name=") or line.startswith("user.email=")
    ]

    print("[MTS] Global Git identity updated successfully.")
    print(f"[MTS] user.name:  {configured_name}")
    print(f"[MTS] user.email: {configured_email}")
    print("[MTS] Verification (from `git config --global --list`):")
    for line in identity_lines:
        print(f"[MTS]   {line}")


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI parser for git identity switching."""
    parser = argparse.ArgumentParser(
        description="Switch global Git username/email from account mappings in a .properties file",
    )
    parser.add_argument(
        "--account-name",
        type=str,
        required=True,
        help="Account key to use (mapped via git.account.<name>.username/email)",
    )
    parser.add_argument(
        "--properties",
        type=Path,
        default=Path("config/git_identity.properties"),
        help="Path to .properties file containing account mappings",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print values without applying git global config changes",
    )
    return parser


def main() -> None:
    """Entry point for the standalone git identity switch utility."""
    parser = build_argument_parser()
    args = parser.parse_args()
    run_switch_git_identity(
        account_name=args.account_name,
        properties_path=args.properties,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
