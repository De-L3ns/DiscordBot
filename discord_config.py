import discord
from discord.ext import commands
import praw
import os
from dotenv import load_dotenv

# Load environment variables from .env file



class DiscordConfig:
    def __init__(self):
        load_dotenv()
        self.intents = discord.Intents.default()
        self.intents.members = True
        self.intents.message_content = True
        self.help_command = commands.DefaultHelpCommand(no_category='Commands')
        self.client = commands.Bot(command_prefix='!', intents=self.intents, help_command=self.help_command)
        self.token = os.getenv('DISCORD_TOKEN')
        self.initialiseRedditConfig()
        self.setImgurConfig()

    def initialiseRedditConfig(self):
        self.reddit = praw.Reddit(client_id= os.getenv('REDDIT_CLIENT_ID'),
                                  client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                                  username=os.getenv('REDDIT_USERNAME'),
                                  password=os.getenv('REDDIT_PASSWORD'),
                                  user_agent=os.getenv('REDDIT_USER_AGENT'))
    def setImgurConfig(self):
        self.imgur_client_id = os.getenv('IMGUR_CLIENT_ID')
        self.imgur_album_key = os.getenv('IMGUR_ALBUM_KEY')
    
    def run(self):
        self.client.run(self.token)