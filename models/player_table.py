from models.player_info import PlayerInfo
from datetime import datetime

class PlayerTable:
    def __init__(self, players: list[PlayerInfo]):
        self.players = players
        self.collumn_width = [
            1, #Rank
            20, #Team
            6 #Points
        ]
        self.headers = ["#", "Team", "Points"]

    def create_table_string(self) -> str:
        table: list[str] = []
        table.append(f"```")  # Discord formatting
        table.append(self.__format_row(self.headers))  # Header row
        table.append("-" * (sum(self.collumn_width) + 6))  # Mimic table (+6 for the whitespace and |)
        
        for player_data in self.players:
            table.append(self.__format_row([str(player_data.rank), player_data.team[:18], player_data.points]))  # Data rows
        
        last_update = f"Last update: {datetime.today().strftime('%d-%m-%y')} - {datetime.now().strftime('%H:%M:%S')}"
        table.append(last_update)
        table.append(f"```")  # Discord formatting
    
    
    def compare_tables(self, old_table: "PlayerTable"):
        changes: list[str] = []
        other_players = {p.team: p for p in old_table.players} 
        for player_data in self.players:
            rank_change = ''
            points_change = ''
            old_player_data = other_players.get(player_data.team)
            if player_data.points != old_player_data.points:
               points_change = f"kreeg {player_data.points - old_player_data.points} punten bij"
               rank_change = f"en stijgt naar plaats {player_data.rank}" if player_data.rank < old_player_data.rank else \
                             f"en zakt naar plaats {player_data.rank}" if player_data.rank > old_player_data.rank else "en blijft op dezelfde plaats"
               changes.append(f"🚴 {player_data.team} {points_change} {rank_change}")
        return "\n".join(changes) if changes else None
    
    def __format_row(self, row_data):
        return f"{row_data[0]:<{self.collumn_width[0]}} | {row_data[1]:<{self.collumn_width[1]}} | {row_data[2]:<{self.collumn_width[2]}}"
    
    