from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
import re
from typing import Iterable

from mid.blocks.base import BaseBlock


@dataclass
class RegistryEntry:
    block_id: str
    instance: BaseBlock


class BlockRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._ordered_ids: list[str] = []

    def load(self) -> None:
        self._entries.clear()
        self._ordered_ids.clear()

        packages_to_scan = [
            "mid.blocks.examples",
            "mid.blocks.general",
            "mid.blocks.info",
        ]
        for pkg_name in packages_to_scan:
            package = importlib.import_module(pkg_name)
            for _, module_name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
                importlib.import_module(module_name)

        subclasses = list(_iter_subclasses(BaseBlock))
        instances: list[BaseBlock] = []
        for cls in subclasses:
            if cls is BaseBlock:
                continue
            instance = cls()
            if not instance.id:
                continue
            instances.append(instance)

        instances.sort(key=lambda block: block.order)
        for instance in instances:
            if instance.id in self._entries:
                raise ValueError(f"Duplicate block id: {instance.id}")
            self._entries[instance.id] = RegistryEntry(block_id=instance.id, instance=instance)
            self._ordered_ids.append(instance.id)

    def list_blocks(self) -> list[BaseBlock]:
        return [self._entries[block_id].instance for block_id in self._ordered_ids]

    def get(self, block_id: str) -> BaseBlock | None:
        entry = self._entries.get(block_id)
        if entry is None:
            return None
        return entry.instance

    def resolve(self, block_id: str) -> BaseBlock | None:
        direct = self.get(block_id)
        if direct is not None:
            return direct
        base_id = _resolve_instance_base(block_id)
        if base_id is None:
            return None
        return self.get(base_id)


def _iter_subclasses(cls: type[BaseBlock]) -> Iterable[type[BaseBlock]]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _iter_subclasses(subclass)


_INSTANCE_RE = re.compile(r"^(?P<base>.+)-(?P<idx>\d+)$")


def _resolve_instance_base(block_id: str) -> str | None:
    match = _INSTANCE_RE.match(block_id)
    if not match:
        return None
    return match.group("base")
