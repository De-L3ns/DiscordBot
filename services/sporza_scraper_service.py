from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from models import PlayerInfo
from models import PlayerTable
import os
import requests
from dotenv import load_dotenv

class SporzaScraperService:
    def __init__ (self):
        load_dotenv()
        self.url = os.getenv('SPORZA_LEAGUE_URL')
        self.league_table: PlayerTable = PlayerTable(self.__getCompetitionInfo())
        

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
            if compare_result == None:
                return None
            table_string += compare_result

        self.league_table = table
        return table_string
    
