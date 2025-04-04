from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from models import PlayerInfo
from models import PlayerTable
import time
import os
import requests
from dotenv import load_dotenv

class SporzaScraperService:
    def __init__ (self):
        load_dotenv()
        self.url = os.getenv('SPORZA_LEAGUE_URL')
        # self.league_table: PlayerTable = None
        old_players = [
            PlayerInfo(1, "CARRY", 1111),               # Original points: 1377
            PlayerInfo(3, "De leanderleetje's ", 1203),  # Original points: 1377
            PlayerInfo(5, "Rialcé", 944),               # Original points: 1261
            PlayerInfo(4, "Team Snickx", 1000),          # Original points: 1231
            PlayerInfo(5, "Kelly Verbier", 1008),        # Original points: 1197
            PlayerInfo(6, "GoGo Pedalo", 1505),          # Original points: 1185
            PlayerInfo(7, "Bing Bang Bong", 944),        # Original points: 1029
            PlayerInfo(9, "Jeroen doe nou niet", 1076),  # Original points: 976
            PlayerInfo(8, "Rijsttaartje voor onderweg", 1010)  # Original points: 876
        ]

        lt = PlayerTable(old_players)
        self.league_table = lt
        

    def __getCompetitionInfo(self) -> list[PlayerInfo]: 
        response = requests.get(self.url)
        sporzaData = response.json()
        player_info_list: list[PlayerInfo] = []
        rank: int = 1

        for team in sporzaData['teams']:
            team_name = team['name']
            score = team['points']
            player_info = PlayerInfo(rank, team_name, int(score))
            player_info_list.append(player_info)
            rank += 1
        
        return player_info_list
    
    def getLeagueTable(self, with_compare: bool) -> str:
        player_info: list[PlayerInfo] = self.__getCompetitionInfo()
        table: PlayerTable = PlayerTable(player_info)
        table_string: str = table.create_table_string()
        
        if with_compare and self.league_table != None:
            compare_result: str = table.compare_tables(self.league_table)
            print(compare_result)
            if compare_result == None:
                return None
            table_string += compare_result

        self.league_table = table
        return table_string
    
