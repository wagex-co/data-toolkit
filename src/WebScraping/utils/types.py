from typing import TypedDict, List, Dict, Optional, Tuple

class GameOverUnderData(TypedDict):
    """Type representing the data structure for a single game's over/under odds."""
    date: str
    time: Optional[str]
    teams: Tuple[str, str]
    over_under: Optional[str]
    location: Optional[str]
    tv_network: Optional[str]

GamesDataList = List[GameOverUnderData]

ProcessedDataResult = Dict[str, List[GameOverUnderData]]
