from models import PlayerInfo
from models import PlayerTable
import os
import requests
from dotenv import load_dotenv
from typing import Any

class SporzaScraperService:
    def __init__ (self):
        load_dotenv()
        self.url = os.getenv(
            'https://wielermanager.sporza.be/vrjr-m-26/competitions/5B2gvM7VF6.data?_routes=routes%2F%24edition.competitions.%24minicompetition.%28%24match%29',
        )
        self.league_table: PlayerTable = PlayerTable(self.__getCompetitionInfo())
        

    def __getCompetitionInfo(self) -> list[PlayerInfo]: 
        response = requests.get(self.url)
        response.raise_for_status()
        sporzaData = response.json()
        player_info_list: list[PlayerInfo] = []

        def decode_indexed_payload(raw: list[Any]) -> Any:
            memo: dict[int, Any] = {}
            in_progress: set[int] = set()

            def resolve_ref(ref: Any) -> Any:
                if isinstance(ref, int):
                    return resolve_index(ref)
                return resolve_node(ref)

            def resolve_index(idx: int) -> Any:
                if idx in memo:
                    return memo[idx]
                if idx in in_progress:
                    return None
                if idx < 0 or idx >= len(raw):
                    return None

                in_progress.add(idx)
                result = resolve_node(raw[idx])
                memo[idx] = result
                in_progress.remove(idx)
                return result

            def resolve_node(node: Any) -> Any:
                if isinstance(node, dict):
                    if node and all(isinstance(k, str) and k.startswith("_") and k[1:].isdigit() for k in node):
                        out: dict[str, Any] = {}
                        for key_ref_token, value_ref in node.items():
                            key_ref = int(key_ref_token[1:])
                            key = resolve_index(key_ref)
                            value = resolve_ref(value_ref)
                            out[str(key)] = value
                        return out
                    return {k: resolve_ref(v) for k, v in node.items()}

                if isinstance(node, list):
                    return [resolve_ref(item) for item in node]

                return node

            return resolve_index(0)

        if isinstance(sporzaData, list):
            decoded_root = decode_indexed_payload(sporzaData)
            route_payload = next(iter(decoded_root.values()))
            members = route_payload["data"]["miniCompetition"]["members"]
        else:
            members = sporzaData['teams']

        for team in members:
            team_name = team.get('teamName') or team.get('name')
            score = team.get('points', 0)
            rank = int(team.get('rank', 0))
            if not team_name:
                continue
            player_info = PlayerInfo(rank, team_name, int(score))
            player_info_list.append(player_info)

        player_info_list.sort(key=lambda p: p.rank)
        
        return player_info_list
    
    def getLeagueTable(self, with_compare: bool) -> str:
        player_info: list[PlayerInfo] = self.__getCompetitionInfo()
        table: PlayerTable = PlayerTable(player_info)
        table_string: str = table.create_table_string()
        
        if with_compare and self.league_table != None:
            compare_result: str = table.compare_tables(self.league_table)
            if compare_result == None:
                return None
            table_string += compare_result

        self.league_table = table
        return table_string
    
