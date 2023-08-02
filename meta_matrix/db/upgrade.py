from asyncpg import Connection
from mautrix.util.async_db import UpgradeTable

upgrade_table = UpgradeTable()


@upgrade_table.register(description="Initial revision")
async def upgrade_v1(conn: Connection) -> None:
    await conn.execute(
        """CREATE TABLE portal (
            ps_id           TEXT PRIMARY KEY,
            mxid            VARCHAR(255),
            app_page_id     TEXT,
            relay_user_id   VARCHAR(255),
            encrypted       BOOLEAN DEFAULT false
        )"""
    )
    await conn.execute(
        """CREATE TABLE puppet (
            ps_id         TEXT PRIMARY KEY,
            app_page_id   TEXT,
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
            app_page_id     TEXT,
            notice_room     TEXT
        )"""
    )
    await conn.execute(
        """CREATE TABLE message (
            event_mxid          VARCHAR(255) PRIMARY KEY,
            room_id             VARCHAR(255) NOT NULL,
            ps_id               TEXT NOT NULL,
            sender              VARCHAR(255) NOT NULL,
            meta_message_id     TEXT NOT NULL,
            app_page_id         TEXT NOT NULL,
            created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
            UNIQUE (event_mxid, room_id)
        )"""
    )
    await conn.execute(
        """CREATE TABLE meta_application (
            page_id             TEXT PRIMARY KEY,
            outgoing_page_id    TEXT,
            name                VARCHAR(255),
            admin_user          VARCHAR(255),
            page_access_token   TEXT
        )"""
    )

    # The page_id of meta applications are unique to your platform.
    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_meta_application_app_page_id
        FOREIGN KEY (app_page_id) references meta_application (page_id)"""
    )

    await conn.execute(
        """ALTER TABLE portal ADD CONSTRAINT FK_portal_meta_application_app_page_id
        FOREIGN KEY (app_page_id) references meta_application (page_id)"""
    )

    await conn.execute(
        """ALTER TABLE matrix_user ADD CONSTRAINT FK_matrix_user_meta_application_app_page_id
        FOREIGN KEY (app_page_id) references meta_application (page_id)"""
    )

    await conn.execute(
        """ALTER TABLE puppet ADD CONSTRAINT FK_puppet_meta_application_app_page_id
        FOREIGN KEY (app_page_id) references meta_application (page_id)"""
    )

    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_portal_ps_id
        FOREIGN KEY (ps_id) references portal (ps_id)"""
    )
