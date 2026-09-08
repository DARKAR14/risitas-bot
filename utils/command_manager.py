import asyncio
import json
from pathlib import Path

from discord import AppCommandType


class CommandManager:
    """Administra qué comandos se publican en Discord."""

    def __init__(self, bot):
        self.bot = bot
        self.settings_path = Path(__file__).parent.parent / "bot_settings.json"
        self.catalog = {}
        self.disabled = set()
        self.lock = asyncio.Lock()
        self._load_settings()

    def _load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self.disabled = set(data.get("disabled_commands", []))
        except FileNotFoundError:
            self.disabled = set()
        except (OSError, ValueError) as error:
            print(f"[ERROR] No se pudo leer bot_settings.json: {error}", flush=True)
            self.disabled = set()

    def _save_settings(self):
        data = {"disabled_commands": sorted(self.disabled)}
        temporary = self.settings_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.settings_path)

    def capture(self):
        self.catalog = {
            command.name: command for command in self.bot.tree.get_commands()
        }

    def apply_saved_state(self):
        for name in self.disabled:
            command = self.catalog.get(name)
            if command:
                self.bot.tree.remove_command(
                    name,
                    type=getattr(command, "type", AppCommandType.chat_input),
                )

    def list_commands(self):
        published = {command.name for command in self.bot.tree.get_commands()}
        result = []

        for name, command in sorted(self.catalog.items()):
            binding = getattr(command, "binding", None)
            result.append(
                {
                    "name": name,
                    "description": command.description,
                    "enabled": name in published,
                    "type": str(
                        getattr(command, "type", AppCommandType.chat_input)
                    ).split(".")[-1],
                    "module": binding.__class__.__module__ if binding else None,
                }
            )

        return result

    async def set_enabled(self, name, enabled):
        async with self.lock:
            command = self.catalog.get(name)
            if not command:
                raise KeyError(name)

            currently_enabled = any(
                item.name == name for item in self.bot.tree.get_commands()
            )
            if currently_enabled == enabled:
                return self.get_command(name)

            if enabled:
                self.bot.tree.add_command(command, override=True)
            else:
                self.bot.tree.remove_command(
                    name,
                    type=getattr(command, "type", AppCommandType.chat_input),
                )

            try:
                await self.bot.tree.sync()
            except Exception:
                if enabled:
                    self.bot.tree.remove_command(
                        name,
                        type=getattr(command, "type", AppCommandType.chat_input),
                    )
                else:
                    self.bot.tree.add_command(command, override=True)
                raise

            if enabled:
                self.disabled.discard(name)
            else:
                self.disabled.add(name)
            self._save_settings()
            return self.get_command(name)

    def get_command(self, name):
        for command in self.list_commands():
            if command["name"] == name:
                return command
        return None
