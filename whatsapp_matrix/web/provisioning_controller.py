import json
from logging import Logger, getLogger

from aiohttp import ClientSession

from whatsapp.types import WSPhoneID
from whatsapp_matrix.db import WhatsappApplication
from whatsapp_matrix.portal import Portal
from whatsapp_matrix.puppet import Puppet
from whatsapp_matrix.user import User

from ..config import Config


class ProvisioningController:
    http: ClientSession
    log: Logger = getLogger()

    def __init__(
        self,
        config: Config,
        client_session: ClientSession,
    ) -> None:
        self.base_url = config["whatsapp.base_url"]
        self.version = config["whatsapp.version"]
        self.http = client_session

    @property
    def _acao_headers(self) -> dict[str, str]:
        """
        Return the Access-Control-Allows headers

        """
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
        }

    @property
    def _headers(self) -> dict[str, str]:
        """
        Return the headers of the request

        """
        return {
            **self._acao_headers,
            "Content-Type": "application/json",
        }

    def _invalidate_business_id_caches(self, old_business_id: str) -> None:
        """
        Invalidate the business id caches.

        Parameters
        ----------
        old_business_id: str
            The old business id to invalidate.
        """
        User.by_business_id.pop(old_business_id, None)
        for key in list(Portal.by_app_and_identifier.keys()):
            if old_business_id in key:
                Portal.by_app_and_identifier.pop(key, None)

        for identifier, puppet in list(Puppet.by_identifier_id.items()):
            if puppet.app_business_id == old_business_id:
                Puppet.by_identifier_id.pop(identifier, None)

    async def update_app(
        self, whatsapp_app: WhatsappApplication, updates: dict[str, str], admin_user: str
    ) -> WhatsappApplication:
        """
        Update the WhatsApp application.

        Parameters
        ----------
        whatsapp_app: WhatsappApplication
            The WhatsApp application to update.
        updates: dict[str, str]
            The updates to apply to the WhatsApp application.
        admin_user: str
            The admin user of the WhatsApp application.

        Returns
        -------
        WhatsappApplication
            The updated WhatsApp application.

        Raises
        ------
        Exception
            If the WhatsApp application cannot be updated.
            The exception will be a dictionary with the following structure:
            {
                "detail": {
                    "data": {"business_id": updates["business_id"]},
                    "message": "business_id %(business_id)s is already registered",
                }
            }
        """
        if "business_id" in updates and updates["business_id"] != whatsapp_app.business_id:
            existing = await WhatsappApplication.get_by_business_id(updates["business_id"])
            if existing and existing.admin_user != admin_user:
                raise Exception(
                    json.dumps(
                        {
                            "detail": {
                                "data": {"business_id": updates["business_id"]},
                                "message": "business_id %(business_id)s is already registered",
                            }
                        }
                    )
                )

        if "wb_phone_id" in updates and updates["wb_phone_id"] != whatsapp_app.wb_phone_id:
            existing = await WhatsappApplication.get_by_wb_phone_id(updates["wb_phone_id"])
            if existing and existing.admin_user != admin_user:
                raise Exception(
                    json.dumps(
                        {
                            "detail": {
                                "data": {"wb_phone_id": updates["wb_phone_id"]},
                                "message": "wb_phone_id %(wb_phone_id)s is already registered",
                            }
                        }
                    )
                )

        old_business_id = whatsapp_app.business_id
        old_wb_phone_id = whatsapp_app.wb_phone_id
        current_business_id = old_business_id

        invalidate_business_id_caches = await whatsapp_app.update_identifiers(
            updates, old_business_id, old_wb_phone_id, current_business_id
        )

        if invalidate_business_id_caches:
            self._invalidate_business_id_caches(old_business_id)
            User.by_mxid.pop(admin_user, None)

        user = await User.get_by_mxid(mxid=admin_user, create=False)
        if user:
            user._add_to_cache()

        try:
            return await WhatsappApplication.get_by_admin_user(admin_user=admin_user)
        except Exception:
            self.log.error(
                "Failed to decrypt updated WhatsApp application data for %s", admin_user
            )
            raise Exception(json.dumps({"detail": {"message": "Internal server error"}}))

    async def set_pin(
        self, phone_id: WSPhoneID, pin: str, page_access_token: str
    ) -> tuple[int, str]:
        """
        Set the pin for a phone.

        Parameters
        ----------
        phone_id: WSPhoneID
            The phone ID to set the pin for.
        pin: str
            The pin to set for the phone.
        page_access_token: str
            The page access token to use to set the pin.

        Returns
        -------
        tuple[int, str]
            The status and message of the response.
        """
        url = f"{self.base_url}/{self.version}/{phone_id}"
        self.log.debug(f"Setting pin for phone {phone_id} with url {url}")
        data = {"pin": pin}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {page_access_token}",
        }

        async with self.http.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                self.log.debug(f"Pin set successfully for phone {phone_id}")
                return response.status, "Pin set successfully"

            self.log.error(f"Failed to set pin for phone {phone_id}: {await response.text()}")
            message = await response.json()

            return response.status, message.get("error", {}).get("message", "Failed to set pin")
