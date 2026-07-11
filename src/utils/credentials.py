from __future__ import annotations

import keyring

SERVICE_NAME = "MythicaPipelineApp"

OPENAI_KEY = "openai_api_key"
NOTION_TOKEN = "notion_integration_token"


def save_credential(key: str, value: str) -> None:
    keyring.set_password(SERVICE_NAME, key, value)


def get_credential(key: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, key)


def delete_credential(key: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, key)
    except keyring.errors.PasswordDeleteError:
        pass
