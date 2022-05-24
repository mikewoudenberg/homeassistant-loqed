"""API wrapper for Loqed integration."""

from __future__ import annotations

import base64
from enum import Enum
import hashlib
from hashlib import sha256
import hmac
import json
import logging
import struct
from time import time
import urllib

from aiohttp import ClientSession

DEFAULT_TIMEOUT = 5 * 60
TIMESTAMP_HEADER_NAME = "timestamp"
HASH_HEADER_NAME = "hash"
ALLOWED_DRIFT = 60
WEBHOOK_ALL_EVENTS_FLAG = 511


def _now_as_timestamp():
    return int(time())


_LOGGER = logging.getLogger(__name__)


class ActionType(Enum):
    """
    Represents an action that can be taken by the lock
    """

    OPEN = 1
    UNLOCK = 2
    LOCK = 3


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
        self._session = session
        self._ip_address = ip_address
        self._api_key = api_key
        self._timeout = timeout

    async def setup_webhook(
        self, callback_url: str, flags: int = WEBHOOK_ALL_EVENTS_FLAG
    ) -> bool:
        """
        Sets up a webhook for the given lock. Enables all events and calls the callbackUrl
        """
        now = _now_as_timestamp()
        signature = self.generate_signature(
            callback_url.encode() + flags.to_bytes(4, "big"), now
        )
        result = await self._session.post(
            f"http://{self._ip_address}/webhooks",
            timeout=self._timeout,
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

    async def remove_webhook(self, webhook_id: int) -> bool:
        """
        Removes a webhook for the given lock.
        """
        now = _now_as_timestamp()
        signature = self.generate_signature(webhook_id.to_bytes(8, "big"), now)
        result = await self._session.delete(
            f"http://{self._ip_address}/webhooks/{webhook_id}",
            timeout=self._timeout,
            headers={"timestamp": str(now), "hash": signature},
        )

        _LOGGER.debug("Remove returned %d: %s", result.status, result.text)

        return result.status == 200

    async def get_all_webhooks(self):
        """
        Returns all webhooks
        """
        now = _now_as_timestamp()
        signature = self.generate_signature(bytes(), now)
        result = await self._session.get(
            f"http://{self._ip_address}/webhooks",
            timeout=self._timeout,
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
    ) -> bool:
        """
        Validates the given body to have come from the configured bridge
        """

        calculated_hash = self.generate_signature(body.encode(), timestamp)

        now = _now_as_timestamp()

        return message_hash == calculated_hash and (
            allow_all_times
            or timestamp in range(now - ALLOWED_DRIFT, now + ALLOWED_DRIFT)
        )

    def generate_signature(self, body: bytes, timestamp: int) -> str:
        """
        Returns the signature for the requested message
        """
        return sha256(
            body + timestamp.to_bytes(8, "big") + base64.b64decode(self._api_key)
        ).hexdigest()


class LoqedLockClient:
    """
    Client for sending actions to the Loqed lock
    """

    def __init__(
        self, session: ClientSession, ip_address: str, local_key_id: int, secret: str
    ) -> None:
        self._session = session
        self._ip_address = ip_address
        self._local_key_id = local_key_id
        self._secret = secret

    async def open_lock(self) -> None:
        """
        Open the provided lock
        """
        result = await self._session.get(
            f"http://{self._ip_address}/to_lock?command_signed_base64={self._get_command(ActionType.OPEN)}"
        )
        result.raise_for_status()

    async def lock_lock(self) -> None:
        """
        Locks the provided lock
        """
        result = await self._session.get(
            f"http://{self._ip_address}/to_lock?command_signed_base64={self._get_command(ActionType.LOCK)}"
        )
        result.raise_for_status()

    async def latch_lock(self) -> None:
        """
        Locks the provided lock
        """
        result = await self._session.get(
            f"http://{self._ip_address}/to_lock?command_signed_base64={self._get_command(ActionType.UNLOCK)}"
        )
        result.raise_for_status()

    def _get_command(self, action: ActionType) -> str:
        """
        Generates a signed comamnd string that can be sent to the lock securely
        """
        message_id = 0
        protocol = 2
        command_type = 7
        device_id = 1
        message_id_bin = struct.pack("Q", message_id)
        protocol_bin = struct.pack("B", protocol)
        command_type_bin = struct.pack("B", command_type)
        local_key_id_bin = struct.pack("B", self._local_key_id)
        device_id_bin = struct.pack("B", device_id)
        action_bin = struct.pack("B", action.value)
        now = int(time())
        timenow_bin = now.to_bytes(8, "big", signed=False)
        local_generated_binary_hash = (
            protocol_bin
            + command_type_bin
            + timenow_bin
            + local_key_id_bin
            + device_id_bin
            + action_bin
        )
        command_hmac = hmac.new(
            base64.b64decode(self._secret), local_generated_binary_hash, hashlib.sha256
        ).digest()
        command = (
            message_id_bin
            + protocol_bin
            + command_type_bin
            + timenow_bin
            + command_hmac
            + local_key_id_bin
            + device_id_bin
            + action_bin
        )
        return urllib.parse.quote(base64.b64encode(command).decode("ascii"))


class LoqedStatusClient:
    """
    Client for retrieving status the Loqed bridge
    """

    def __init__(self, session: ClientSession, ip_address: str) -> None:
        self._session = session
        self._ip_address = ip_address

    async def get_lock_status(self) -> dict[str, str]:
        """
        Gets the status of the provided lock
        """
        result = await self._session.get(f"http://{self._ip_address}/status")
        return await result.json(
            content_type="text/html",
        )


class LoqedException(Exception):
    """
    Exception thorown to indicate handling error in Loqed integration
    """
