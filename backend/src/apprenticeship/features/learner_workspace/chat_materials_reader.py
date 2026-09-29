"""Load validated, bounded conversation material from a learner starter."""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from apprenticeship.features.learner_workspace.chat_context import coworker_context, mentor_context
from apprenticeship.features.learner_workspace.chat_models import ChatAgent
from apprenticeship.features.modules.module_spec import ModuleSpec
from apprenticeship.features.modules.peer_private import PeerPrivate
from apprenticeship.features.modules.peer_public import PeerPublic


@dataclass(frozen=True)
class ChatMaterials:
    agents: list[ChatAgent]
    contexts: dict[str, str]


class ChatMaterialsUnavailable(Exception):
    pass


class ChatMaterialsReader:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def read(
        self, module_id: str, spec: ModuleSpec, public_peers: list[PeerPublic],
    ) -> ChatMaterials:
        root = self._data_dir / "modules" / module_id
        starter = root / "starter"
        try:
            peers = TypeAdapter(list[PeerPrivate]).validate_python(
                json.loads((root / "private" / "peers.json").read_text(encoding="utf-8"))
            )
            if len(peers) != 2 or len(public_peers) != 2:
                raise ValueError("Expected two peers")
            if any(peer.name != public.name or peer.role != public.role
                   for peer, public in zip(peers, public_peers, strict=True)):
                raise ValueError("Peer profiles disagree with published record")
            contexts = {
                f"peer-{index}": coworker_context(starter, peer)
                for index, peer in enumerate(peers)
            }
            contexts["mentor"] = mentor_context(starter, spec)
        except (OSError, ValueError, ValidationError) as error:
            raise ChatMaterialsUnavailable(
                "This module's conversation materials are unavailable"
            ) from error

        agents = [
            ChatAgent(
                id=f"peer-{index}", name=peer.name, role=peer.role,
                description=", ".join(peer.responsibilities),
            )
            for index, peer in enumerate(peers)
        ]
        agents.append(ChatAgent(
            id="mentor", name="AI mentor", role="Mentor",
            description="Helps you reason through the task with focused hints.",
        ))
        return ChatMaterials(agents=agents, contexts=contexts)
