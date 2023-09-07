from asyncpg import Connection
from mautrix.util.async_db import UpgradeTable

upgrade_table = UpgradeTable()


@upgrade_table.register(description="Initial revision")
async def upgrade_v1(conn: Connection) -> None:
    await conn.execute(
        """CREATE TABLE portal (
            phone_id           TEXT PRIMARY KEY,
            mxid            VARCHAR(255),
            app_business_id     TEXT,
            relay_user_id   VARCHAR(255),
            encrypted       BOOLEAN DEFAULT false
        )"""
    )
    await conn.execute(
        """CREATE TABLE puppet (
            phone_id         TEXT PRIMARY KEY,
            app_business_id   TEXT,
            display_name  TEXT,
            is_registered BOOLEAN NOT NULL DEFAULT false,
            custom_mxid   VARCHAR(255),
            access_token  TEXT,
            next_batch    TEXT,
            base_url      TEXT
        )"""
    )
    await conn.execute(
        """CREATE TABLE matrix_user (
            mxid            VARCHAR(255) PRIMARY KEY,
            app_business_id     TEXT,
            notice_room     TEXT
        )"""
    )
    await conn.execute(
        """CREATE TABLE message (
            event_mxid          VARCHAR(255) PRIMARY KEY,
            room_id             VARCHAR(255) NOT NULL,
            phone_id               TEXT NOT NULL,
            sender              VARCHAR(255) NOT NULL,
            whatsapp_message_id     TEXT NOT NULL,
            app_business_id         TEXT NOT NULL,
            created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
            UNIQUE (event_mxid, room_id),
            UNIQUE (whatsapp_message_id)
        )"""
    )
    await conn.execute(
        """CREATE TABLE ws_application (
            business_id             TEXT PRIMARY KEY,
            ws_phone_id             TEXT,
            name                VARCHAR(255),
            admin_user          VARCHAR(255),
            page_access_token   TEXT
        )"""
    )

    # The business_id of meta applications are unique to your platform.
    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_ws_application_app_business_id
        FOREIGN KEY (app_business_id) references ws_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE portal ADD CONSTRAINT FK_portal_ws_application_app_business_id
        FOREIGN KEY (app_business_id) references ws_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE matrix_user ADD CONSTRAINT FK_matrix_user_ws_application_app_business_id
        FOREIGN KEY (app_business_id) references ws_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE puppet ADD CONSTRAINT FK_puppet_ws_application_app_business_id
        FOREIGN KEY (app_business_id) references ws_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_portal_phone_id
        FOREIGN KEY (phone_id) references portal (phone_id)"""
    )
