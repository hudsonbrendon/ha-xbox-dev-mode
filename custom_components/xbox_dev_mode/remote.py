"""Remote platform: envia botoes de gamepad ao console via /ext/remoteinput.

Um unico `remote.xbox` que aceita `remote.send_command` com os nomes dos botoes
(a, b, x, y, dpad_up, menu, view, left_thumbstick_up, ...). Sem estado de ligado/
desligado a controlar — o console decide isso — entao is_on espelha o Dev Mode:
so faz sentido enviar input quando o portal esta ativo.
"""
from __future__ import annotations

import asyncio
from typing import Any, Iterable

from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from xbox_devportal import GAMEPAD_BUTTONS

from .const import STATE_DEV
from .coordinator import XboxDevModeCoordinator
from .entity import XboxEntity


class XboxRemote(XboxEntity, RemoteEntity):
    """Controle remoto de gamepad do Xbox."""

    _attr_translation_key = "remote"
    _dev_only = True

    def __init__(self, coordinator: XboxDevModeCoordinator, entry_id: str,
                 entry_unique_id: str) -> None:
        super().__init__(coordinator, entry_id, entry_unique_id)
        self._attr_unique_id = f"{entry_id}_remote"

    @property
    def is_on(self) -> bool:
        """Ligado = console em Dev Mode (unico estado em que input funciona)."""
        return bool(self.coordinator.data and self.coordinator.data.state == STATE_DEV)

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Envia um ou mais botoes de gamepad, em sequencia.

        `num_repeats` e `delay_secs` do HA sao respeitados.
        """
        repeats = kwargs.get("num_repeats", 1)
        delay = kwargs.get("delay_secs", 0.4)
        cmds = list(command)
        for _ in range(repeats):
            for i, cmd in enumerate(cmds):
                if cmd.lower() not in GAMEPAD_BUTTONS:
                    raise ValueError(
                        f"botao invalido: {cmd!r}; validos: {sorted(GAMEPAD_BUTTONS)}")
                await self.coordinator.client.press_gamepad_button(cmd.lower())
                if i < len(cmds) - 1:
                    await asyncio.sleep(delay)


async def async_setup_entry(hass: HomeAssistant, entry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Set up the remote entity."""
    coordinator = entry.runtime_data
    async_add_entities([XboxRemote(coordinator, entry.entry_id, entry.unique_id)])
