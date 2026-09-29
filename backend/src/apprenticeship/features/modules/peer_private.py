from pydantic import Field

from apprenticeship.features.modules.peer_public import PeerPublic


class PeerPrivate(PeerPublic):
    known_facts: list[str] = Field(min_length=1)
    unknown_topics: list[str] = Field(min_length=1)
    response_boundaries: list[str] = Field(min_length=1)
