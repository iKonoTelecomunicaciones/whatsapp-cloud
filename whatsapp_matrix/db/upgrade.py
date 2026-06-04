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
        """CREATE TABLE wb_application (
            business_id             TEXT PRIMARY KEY,
            wb_phone_id             TEXT,
            name                VARCHAR(255),
            admin_user          VARCHAR(255),
            page_access_token   TEXT
        )"""
    )

    await conn.execute(
        """CREATE TABLE reaction (
            event_mxid          VARCHAR(255) PRIMARY KEY,
            room_id             VARCHAR(255) NOT NULL,
            sender              VARCHAR(255) NOT NULL,
            whatsapp_message_id     TEXT NOT NULL,
            reaction            VARCHAR(255),
            created_at          TIMESTAMP WITH TIME ZONE NOT NULL,
            UNIQUE (event_mxid, room_id)
        )"""
    )

    # The business_id of meta applications are unique to your platform.
    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_wb_application_app_business_id
        FOREIGN KEY (app_business_id) references wb_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE portal ADD CONSTRAINT FK_portal_wb_application_app_business_id
        FOREIGN KEY (app_business_id) references wb_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE matrix_user ADD CONSTRAINT FK_matrix_user_wb_application_app_business_id
        FOREIGN KEY (app_business_id) references wb_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE puppet ADD CONSTRAINT FK_puppet_wb_application_app_business_id
        FOREIGN KEY (app_business_id) references wb_application (business_id)"""
    )

    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_portal_phone_id
        FOREIGN KEY (phone_id) references portal (phone_id)"""
    )

    await conn.execute(
        """ALTER TABLE reaction ADD CONSTRAINT FK_message_whatsapp_message_id
        FOREIGN KEY (whatsapp_message_id) references message (whatsapp_message_id)
        ON DELETE CASCADE"""
    )


@upgrade_table.register(
    description="Change primary key of portal table and reference it to message table"
)
async def upgrade_v2(conn: Connection) -> None:
    await conn.execute("""ALTER TABLE message DROP CONSTRAINT FK_message_portal_phone_id""")

    await conn.execute(
        """ALTER TABLE portal
        DROP CONSTRAINT portal_pkey,
        ADD PRIMARY KEY (phone_id, app_business_id)"""
    )

    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_portal_phone_id_business_id
        FOREIGN KEY (phone_id, app_business_id) references portal (phone_id, app_business_id)"""
    )


@upgrade_table.register(
    description="Refactor puppet table: add id and username columns, remove unused columns"
)
async def upgrade_v3(conn: Connection) -> None:
    # Drop FK constraint linking puppet to wb_application via app_business_id
    await conn.execute(
        """ALTER TABLE puppet DROP CONSTRAINT FK_puppet_wb_application_app_business_id"""
    )

    # Drop unused columns
    await conn.execute(
        """ALTER TABLE puppet
        DROP COLUMN access_token,
        DROP COLUMN next_batch,
        DROP COLUMN base_url,
        DROP COLUMN is_registered,
        DROP COLUMN app_business_id"""
    )

    # Replace phone_id primary key with a SERIAL id column
    await conn.execute("""ALTER TABLE puppet DROP CONSTRAINT puppet_pkey""")
    await conn.execute("""ALTER TABLE puppet ADD COLUMN id SERIAL PRIMARY KEY""")

    # Add username column with unique constraint
    await conn.execute("""ALTER TABLE puppet ADD COLUMN username TEXT UNIQUE""")
    # phone_id is necessary to be unique to avoid having multiple puppets with the same phone_id
    # and also to be nullable
    await conn.execute("""ALTER TABLE puppet ALTER COLUMN phone_id DROP NOT NULL""")

    await conn.execute("""ALTER TABLE puppet ADD CONSTRAINT unique_phone_id UNIQUE (phone_id)""")


@upgrade_table.register(description="Refactor portal table: add id, bsuid and puppet_id columns")
async def upgrade_v4(conn: Connection) -> None:
    # Drop composite primary key (phone_id, app_business_id) and replace with SERIAL id
    await conn.execute(
        """ALTER TABLE message DROP CONSTRAINT FK_message_portal_phone_id_business_id"""
    )
    await conn.execute("""ALTER TABLE portal DROP CONSTRAINT portal_pkey""")
    await conn.execute("""ALTER TABLE portal ADD COLUMN id SERIAL PRIMARY KEY""")

    # Add bsuid column with unique constraint
    await conn.execute("""ALTER TABLE portal ADD COLUMN bsuid TEXT UNIQUE""")

    # Add puppet_id FK referencing puppet(id)
    await conn.execute("""ALTER TABLE portal ADD COLUMN puppet_id INTEGER""")
    await conn.execute(
        """ALTER TABLE portal ADD CONSTRAINT FK_portal_puppet_id
        FOREIGN KEY (puppet_id) REFERENCES puppet (id) ON DELETE RESTRICT"""
    )

    # Change the phone_id column to be nullable
    await conn.execute("""ALTER TABLE portal ALTER COLUMN phone_id DROP NOT NULL""")


@upgrade_table.register(
    description="Refactor message table: replace room_id/phone_id/app_business_id with portal_id FK"
)
async def upgrade_v5(conn: Connection) -> None:
    # Drop FK constraints that reference columns being removed
    await conn.execute(
        """ALTER TABLE message DROP CONSTRAINT FK_message_wb_application_app_business_id"""
    )

    # Add portal_id column and populate it from the existing phone_id + app_business_id pair
    await conn.execute("""ALTER TABLE message ADD COLUMN portal_id INTEGER""")
    await conn.execute(
        """UPDATE message SET portal_id = portal.id
        FROM portal
        WHERE message.phone_id = portal.phone_id
        AND message.app_business_id = portal.app_business_id"""
    )
    await conn.execute("""ALTER TABLE message ALTER COLUMN portal_id SET NOT NULL""")

    # Add FK constraint from message to portal
    await conn.execute(
        """ALTER TABLE message ADD CONSTRAINT FK_message_portal_id
        FOREIGN KEY (portal_id) REFERENCES portal (id) ON DELETE RESTRICT"""
    )

    # Drop the now-redundant columns
    await conn.execute(
        """ALTER TABLE message
        DROP COLUMN room_id,
        DROP COLUMN phone_id,
        DROP COLUMN app_business_id"""
    )

    # Update puppet_id in portal table to reference puppet.id instead of puppet.phone_id
    await conn.execute(
        """UPDATE portal SET puppet_id = puppet.id
        FROM puppet
        WHERE portal.phone_id = puppet.phone_id"""
    )
