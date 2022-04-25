"""API wrapper for Loqed integration."""

from __future__ import annotations
import base64
from hashlib import sha256
import json
import logging
from time import time
from aiohttp import ClientSession

DEFAULT_TIMEOUT = 3
TIMESTAMP_HEADER_NAME = "timestamp"
HASH_HEADER_NAME = "hash"
ALLOWED_DRIFT = 60


def _now_as_timestamp():
    return int(time())


_LOGGER = logging.getLogger(__name__)


class LoqedWebhookClient:
    """
    Client for communicating with the Loqed local bridge
    """

    def __init__(
        self,
        session: ClientSession,
        ip_address: str,
        api_key: str,
        timeout=DEFAULT_TIMEOUT,
    ) -> None:
        """
        :param ip_address: ip address of your loqed bridge
        :param api_key: base64 encoded key of your bridge
        """
        self.__session = session
        self.__ip_address = ip_address
        self.__api_key = api_key
        self.__timeout = timeout

    async def setup_webhook(self, lock_id, callback_url: str, flags: int):
        """
        Sets up a webhook for the given lock. Enables all events and calls the callbackUrl
        """
        now = _now_as_timestamp()
        signature = self._generate_signature(
            callback_url.encode() + flags.to_bytes(4, "big"), now
        )
        result = await self.__session.post(
            f"http://{self.__ip_address}/webhooks",
            timeout=self.__timeout,
            headers={"timestamp": str(now), "hash": signature},
            json={
                "url": callback_url,
                "trigger_state_changed_open": flags & 1,
                "trigger_state_changed_latch": flags >> 1 & 1,
                "trigger_state_changed_night_lock": flags >> 2 & 1,
                "trigger_state_changed_unknown": flags >> 3 & 1,
                "trigger_state_goto_open": flags >> 4 & 1,
                "trigger_state_goto_latch": flags >> 5 & 1,
                "trigger_state_goto_night_lock": flags >> 6 & 1,
                "trigger_battery": flags >> 7 & 1,
                "trigger_online_status": flags >> 8 & 1,
            },
        )

        _LOGGER.debug("Setup returned %d: %s", result.status, result.text)

        return result.status == 200

    async def remove_webhook(self, lock_id, webhook_id: int):
        """
        Removes a webhook for the given lock.
        """
        now = _now_as_timestamp()
        signature = self._generate_signature(webhook_id.to_bytes(8, "big"), now)
        result = await self.__session.delete(
            f"http://{self.__ip_address}/webhooks/{webhook_id}",
            timeout=self.__timeout,
            headers={"timestamp": str(now), "hash": signature},
        )

        _LOGGER.debug("Remove returned %d: %s", result.status, result.text)

        return result.status == 200

    async def get_all_webhooks(self, lock_id):
        """
        Returns all webhooks
        """
        now = _now_as_timestamp()
        signature = self._generate_signature(bytes(), now)
        result = await self.__session.get(
            f"http://{self.__ip_address}/webhooks",
            timeout=self.__timeout,
            headers={"timestamp": str(now), "hash": signature},
        )

        # Loqed bridge incorrectly returns mimetype text/html, so we manually load here
        body = await result.read()
        return json.loads(body)

    def validate_message(
        self,
        body: str,
        timestamp: int,
        message_hash: str,
        allow_all_times: bool = False,
    ):
        """
        Validates the given body to have come from the configured bridge
        """

        calculated_hash = self._generate_signature(body.encode(), timestamp)

        now = _now_as_timestamp()

        return message_hash == calculated_hash and (
            allow_all_times
            or timestamp in range(now - ALLOWED_DRIFT, now + ALLOWED_DRIFT)
        )

    def _generate_signature(self, body: bytes, timestamp: int):
        """
        Returns the signature for the requested message
        """
        return sha256(
            body + timestamp.to_bytes(8, "big") + base64.b64decode(self.__api_key)
        ).hexdigest()


class LoqedLockClient:
    """
    Client for sending actions to the Loqed lock
    """

    def __init__(
        self, session: ClientSession, ip_address: str, local_key_id: int, secret: str
    ) -> None:
        self.__session = session
        self.__ip_address = ip_address
        self.__local_key_id = local_key_id
        self.__secret = secret

    async def open_lock(self, lock_id):
        """
        Open the provided lock
        """
        result = await self.__session.get(
            f"http://{self.__ip_address}/state?command=OPEN&local_key_id={self.__local_key_id}&secret={self.__secret}"
        )
        return result.status == 200

    async def lock_lock(self, lock_id):
        """
        Locks the provided lock
        """
        result = await self.__session.get(
            f"http://{self.__ip_address}/state?command=NIGHT_LOCK&local_key_id={self.__local_key_id}&secret={self.__secret}"
        )
        return result.status == 200

    async def latch_lock(self, lock_id):
        """
        Locks the provided lock
        """
        result = await self.__session.get(
            f"http://{self.__ip_address}/state?command=DAY_LOCK&local_key_id=2&secret=Bs2Yhh6Tr%2BCPrC70DL9JI0LEm%2B0RRMUEAxXCK1l4JdA%3D"
        )
        return result.status == 200

    async def get_lock_status(self, lock_id):
        """
        Gets the status of the provided lock
        """
        result = await self.__session.get(f"http://{self.__ip_address}/status")
        body = await result.text()
        return json.loads(body)


class LoqedException(Exception):
    """
    Exception thorown to indicate handling error in Loqed integration
    """
