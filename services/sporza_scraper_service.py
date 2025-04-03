from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from models import PlayerInfo
import time
import os
import requests
from dotenv import load_dotenv

class SporzaScraperService:
    def __init__ (self):
        load_dotenv()
        self.url = os.getenv('SPORZA_LEAGUE_URL')

    def getCompetitionInfo(self) -> list[PlayerInfo]: 
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
    