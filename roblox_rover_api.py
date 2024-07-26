import aiohttp
import asyncio
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import re

class RoverAPIError(Exception):
    """Base exception for RoverAPI errors"""
    def __init__(self, message: str, status_code: int = None, error_code: str = None, detail: Dict = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)

class RateLimitError(RoverAPIError):
    """Raised when rate limit is exceeded"""
    pass

class AuthenticationError(RoverAPIError):
    """Raised when there's an authentication problem"""
    pass

class NotFoundError(RoverAPIError):
    """Raised when a resource is not found"""
    pass

class ServerError(RoverAPIError):
    """Raised when the server encounters an error"""
    pass

class DiscordError(RoverAPIError):
    """Raised when there's an error related to Discord"""
    pass


def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

@dataclass
class RobloxInfo:
    roblox_id: int
    cached_username: str
    discord_id: str
    guild_id: str

    @classmethod
    def from_api(cls, data):
        return cls(**{camel_to_snake(k): v for k, v in data.items()})


@dataclass
class DiscordUser:
    id: str
    username: str
    avatar: Optional[str]
    discriminator: str
    public_flags: int
    flags: int
    banner: Optional[str] = None
    accent_color: Optional[int] = None
    global_name: Optional[str] = None
    avatar_decoration_data: Optional[Any] = None
    banner_color: Optional[str] = None
    clan: Optional[Any] = None


@dataclass
class DiscordGuildMember:
    avatar: Optional[str]
    communication_disabled_until: Optional[str]
    flags: int
    joined_at: str
    nick: Optional[str]
    pending: bool
    premium_since: Optional[str]
    roles: List[str]
    user: DiscordUser
    mute: bool
    deaf: bool
    banner: Optional[str] = None
    unusual_dm_activity_until: Optional[str] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api(cls, data: Dict[str, Any]):
        known_fields = cls.__annotations__.keys()
        extra_fields = {k: v for k, v in data.items() if k not in known_fields}

        if 'user' in data:
            data['user'] = DiscordUser(**data['user'])

        return cls(**{k: v for k, v in data.items() if k in known_fields}, extra_fields=extra_fields)


@dataclass
class DiscordInfo:
    discord_users: List[DiscordGuildMember]
    roblox_id: int
    guild_id: str

    @classmethod
    def from_api(cls, data: Dict[str, Any]):
        return cls(
            discord_users=[DiscordGuildMember.from_api(member) for member in data['discordUsers']],
            roblox_id=data['robloxId'],
            guild_id=data['guildId']
        )

@dataclass
class UpdateActions:
    can_manage_roles: bool
    can_manage_nicknames: bool

@dataclass
class UpdateResult:
    actions: UpdateActions
    roles: List[str]
    unmanageable_bound_roles: List[str]
    added_roles: List[str]
    removed_roles: List[str]
    failed_roles: List[str]

class RoverAPI:
    BASE_URL = "https://registry.rover.link/api"

    def __init__(self):
        self.api_key = None
        self.session = None

    def set_api_key(self, api_key: str):
        self.api_key = api_key

    async def __aenter__(self):
        if not self.api_key:
            raise ValueError("API key not set. Call set_api_key() before using the client.")
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Tuple[Dict[str, Any], Dict[str, str]]:
        if not self.session:
            raise RuntimeError("API client not initialized. Use 'async with' context manager.")

        url = f"{self.BASE_URL}{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                headers = dict(response.headers)
                data = await response.json()

                if response.status == 200:
                    return data, headers

                error_message = data.get('message', 'Unknown error occurred')
                error_code = data.get('errorCode')
                detail = data.get('detail')

                if error_code == 'discord_error':
                    raise DiscordError(error_message, response.status, error_code, detail)
                elif response.status == 429:
                    raise RateLimitError(error_message, response.status, error_code, detail)
                elif response.status == 401:
                    raise AuthenticationError(error_message, response.status, error_code, detail)
                elif response.status == 404:
                    raise NotFoundError(error_message, response.status, error_code, detail)
                elif 500 <= response.status < 600:
                    raise ServerError(error_message, response.status, error_code, detail)
                else:
                    raise RoverAPIError(error_message, response.status, error_code, detail)

        except aiohttp.ClientError as e:
            raise RoverAPIError(f"Network error occurred: {str(e)}") from e

    async def get_roblox_from_discord(self, guild_id: int, user_id: int) -> tuple[RobloxInfo, dict[str, str]]:
        endpoint = f"/guilds/{guild_id}/discord-to-roblox/{user_id}"
        data, headers = await self._request("GET", endpoint)
        return RobloxInfo.from_api(data), headers

    async def get_discord_from_roblox(self, guild_id: int, roblox_id: int) -> tuple[DiscordInfo, dict[str, str]]:
        endpoint = f"/guilds/{guild_id}/roblox-to-discord/{roblox_id}"
        data, headers = await self._request("GET", endpoint)
        return DiscordInfo.from_api(data), headers

    async def update_user(self, guild_id: int, user_id: int) -> tuple[UpdateResult, dict[str, str]]:
        endpoint = f"/guilds/{guild_id}/update/{user_id}"
        data, headers = await self._request("POST", endpoint)
        return UpdateResult(**data), headers

    async def delete_api_key(self) -> None:
        await self._request("DELETE", "/api-key")

class RateLimitHandler:
    def __init__(self):
        self.buckets = {}

    def update(self, headers: dict):
        if bucket := headers.get('X-RateLimit-Bucket'):
            self.buckets[bucket] = {
                'reset_after': float(headers.get('X-RateLimit-Reset-After', 0)),
                'remaining': int(headers.get('X-RateLimit-Remaining', 0)),
                'retry_after': float(headers.get('Retry-After', 0))
            }

    async def wait_if_needed(self, bucket: str):
        if bucket in self.buckets:
            bucket_info = self.buckets[bucket]
            if bucket_info['remaining'] == 0:
                await asyncio.sleep(bucket_info['reset_after'])

class RoverClient:
    def __init__(self, api_key: str):
        self.api = RoverAPI()
        self.rate_limit_handler = RateLimitHandler()
        self._set_api_key(api_key)

    def _set_api_key(self, api_key: str):
        self.api.set_api_key(api_key)

    async def __aenter__(self):
        await self.api.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.api.__aexit__(exc_type, exc_val, exc_tb)

    async def get_roblox_from_discord(self, guild_id: int, user_id: int) -> RobloxInfo:
        await self.rate_limit_handler.wait_if_needed('discord_to_roblox')
        result, headers = await self.api.get_roblox_from_discord(guild_id, user_id)
        self.rate_limit_handler.update(headers)
        return result

    async def get_discord_from_roblox(self, guild_id: int, roblox_id: int) -> DiscordInfo:
        await self.rate_limit_handler.wait_if_needed('roblox_to_discord')
        result, headers = await self.api.get_discord_from_roblox(guild_id, roblox_id)
        self.rate_limit_handler.update(headers)
        return result

    async def update_user(self, guild_id: int, user_id: int) -> UpdateResult:
        await self.rate_limit_handler.wait_if_needed('update_user')
        result, headers = await self.api.update_user(guild_id, user_id)
        self.rate_limit_handler.update(headers)
        return result

    async def delete_api_key(self) -> None:
        await self.api.delete_api_key()
