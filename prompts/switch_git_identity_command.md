# switch_git_identity_command.md

This document defines the `/switch_git_identity` command to update global Git identity using an account name mapped in a separate `.properties` file.

Purpose

- Switch global Git username (`user.name`) and email (`user.email`) from a configured account mapping.
- Keep credentials outside command-line literals.

Properties file

Use `config/git_identity.properties`:

```properties
git.account.personal.username=Your Personal Name
git.account.personal.email=personal@example.com

git.account.work.username=Your Work Name
git.account.work.email=work@example.com
```

Slash command format

```text
/switch_git_identity --account-name personal --properties config/git_identity.properties
```

CLI equivalent

Run from the project root:

```bash
python -m src.switch_git_identity --account-name personal --properties config/git_identity.properties
```

Dry run (validation only)

```bash
python -m src.switch_git_identity --account-name personal --properties config/git_identity.properties --dry-run
```

Behavior

- Reads `git.account.<account_name>.username` and `git.account.<account_name>.email` from the `.properties` file.
- Sets `git config --global user.name`.
- Sets `git config --global user.email`.
- Prints configured global values for verification.

Notes

- This updates Git global config for the current OS user profile.
- For repository-local identity, use `git config user.name ...` and `git config user.email ...` without `--global`.
