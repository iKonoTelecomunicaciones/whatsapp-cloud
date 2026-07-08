from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes

if TYPE_CHECKING:
    from asyncpg import Connection

log = logging.getLogger("whatsapp_matrix.crypto")

ENCRYPTED_PREFIX = "enc:"
NONCE_SIZE = 16
TAG_SIZE = 16


def is_encrypted(value: str) -> bool:
    return value.startswith(ENCRYPTED_PREFIX)


def encrypt_value(value: str, key: bytes) -> str:
    nonce = get_random_bytes(NONCE_SIZE)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(value.encode("utf-8"))
    payload = base64.b64encode(nonce + tag + ciphertext).decode("ascii")
    return ENCRYPTED_PREFIX + payload


def decrypt_value(encrypted: str, key: bytes) -> str:
    if not is_encrypted(encrypted):
        return encrypted
    payload = base64.b64decode(encrypted[len(ENCRYPTED_PREFIX) :])
    nonce = payload[:NONCE_SIZE]
    tag = payload[NONCE_SIZE : NONCE_SIZE + TAG_SIZE]
    ciphertext = payload[NONCE_SIZE + TAG_SIZE :]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


async def migrate_encrypt_existing_data(conn: Connection, key: bytes) -> None:
    rows = await conn.fetch("SELECT business_id, page_access_token, pin FROM wb_application")
    for row in rows:
        updates: dict[str, str] = {}
        page_access_token = row["page_access_token"]
        pin = row["pin"]

        if page_access_token and not is_encrypted(page_access_token):
            updates["page_access_token"] = encrypt_value(page_access_token, key)
        if pin and not is_encrypted(pin):
            updates["pin"] = encrypt_value(pin, key)

        if not updates:
            continue

        set_parts = []
        values = [row["business_id"]]
        for index, (column, encrypted_value) in enumerate(updates.items(), start=2):
            set_parts.append(f"{column}=${index}")
            values.append(encrypted_value)

        await conn.execute(
            f"UPDATE wb_application SET {', '.join(set_parts)} WHERE business_id=$1",
            *values,
        )
        log.info("Encrypted sensitive fields for wb_application %s", row["business_id"])
