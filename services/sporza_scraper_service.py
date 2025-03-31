from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import asyncio
from dotenv import load_dotenv

class SporzaScraperService:
    def __init__ (self):
        load_dotenv()
        self.login_url = os.getenv('SPORZA_LOGIN_URL')
        self.league_url = os.getenv('SPORZA_LEAGUE_URL')
        self.username = os.getenv('SPORZA_LOGIN')
        self.password = os.getenv('SPORZA_PASSWORD')
        self.setup_selenium()
    
    def setup_selenium(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)

    def scrapeSporza(self) -> str:
        self.driver.get(self.login_url)
        wait = WebDriverWait(self.driver, 500)
        self.login(wait)
        time.sleep(10)
        self.driver.get(self.league_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tbody.ant-table-tbody tr")))
        table_data = self.scrapeTable()
        self.driver.quit()
        return table_data

    def login(self, wait):
        email_field = wait.until(EC.presence_of_element_located((By.ID, "email-id-email")))
        print('logging in with emaul' + self.username)
        email_field.send_keys(self.username)
        password_field = wait.until(EC.presence_of_element_located((By.ID, "password-id-password")))
        password_field.send_keys(self.password)
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[1]/div[3]/div/main/div[4]/form/button"))) 
        login_button.click()
    
    def scrapeTable(self) -> str:
        rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody.ant-table-tbody tr")
        # Extract data from each row
        table_data = []
        for row in rows:
            columns = row.find_elements(By.TAG_NAME, "td")
            rank = columns[0].text.strip()
            team_name = columns[1].find_element(By.TAG_NAME, "a").text.strip()
            player_name = columns[1].find_element(By.TAG_NAME, "span").text.strip() 
            points = columns[2].text.strip() 
            table_data.append([rank, team_name, player_name, points])
        return "\n\n".join([" | ".join(row) for row in table_data])
