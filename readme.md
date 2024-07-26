
### Looking for a roblox discord bot? 
[Agent Blox has you covered.](https://discord.com/oauth2/authorize?client_id=1150791638369718392) 

# RoVer API Wrapper

An asynchronous Python wrapper for the RoVer API, designed to simplify interactions with RoVer's services, perfectly integrates with a discord bot. This wrapper provides an easy-to-use interface for Discord-Roblox account verification and user management.

## Features

- Asynchronous API calls using `aiohttp`
- Automatic rate limiting handling
- Comprehensive error handling with custom exceptions
- Easy-to-use interface with Pythonic naming conventions
- Structured data responses using dataclasses
- Flexible handling of API responses to accommodate future changes
- Context manager support for efficient resource management


## Quick Start
```py
import asyncio
from roblox_rover_api import RoverClient, RoverAPIError

async def main():
    client = RoverClient("your_api_key_here")

    async with client:
        try:
            # Get Roblox info from Discord user
            roblox_info = await client.get_roblox_from_discord("guild_id", "user_id")
            print(f"Roblox Username: {roblox_info.cached_username}")

            # Get Discord info from Roblox user
            discord_info = await client.get_discord_from_roblox("guild_id", "roblox_id")
            for user in discord_info.discord_users:
                print(f"Discord Username: {user.user.username}")

            # Update user (RoVer Plus only)
            update_result = await client.update_user("guild_id", "user_id")
            print(f"Added Roles: {update_result.added_roles}")

        except RoverAPIError as e:
            print(f"An API error occurred: {e.message}")
            if hasattr(e, 'detail') and e.detail:
                print(f"Error details: {e.detail}")

if __name__ == "__main__":
    asyncio.run(main())
```
# RoverClient

The main client for interacting with the RoVer API.

## Methods

- **`get_roblox_from_discord(guild_id: int, user_id: int) -> RobloxInfo`**: Get Roblox information for a Discord user.
- **`get_discord_from_roblox(guild_id: int, roblox_id: int) -> DiscordInfo`**: Get Discord information for a Roblox user.
- **`update_user(guild_id: int, user_id: int) -> UpdateResult`**: Update a user's roles and nickname (RoVer Plus only).
- **`delete_api_key() -> None`**: Delete the current API key.

## Data Classes

- **`RobloxInfo`**: Contains Roblox user information.
- **`DiscordUser`**: Represents a Discord user.
- **`DiscordGuildMember`**: Represents a Discord guild member.
- **`DiscordInfo`**: Contains Discord user information for a Roblox user.
- **`UpdateActions`**: Represents actions that can be performed during an update.
- **`UpdateResult`**: Contains the result of an update operation.

## Error Handling

- **`RoverAPIError`**: Base exception for all API errors.
- **`RateLimitError`**: Raised when rate limit is exceeded.
- **`AuthenticationError`**: Raised for authentication issues.
- **`NotFoundError`**: Raised when a resource is not found.
- **`ServerError`**: Raised for server-side errors.
- **`DiscordError`**: Raised for Discord-specific errors.

