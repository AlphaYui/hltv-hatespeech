from authorization import AuthorizationInfo
from mysqlwrapper import MySQLWrapper
from forums import *

import discord
from discord.ext import commands

from hatesonar import Sonar

import sys


class MainCog(commands.Cog):

    def __init__(self, bot, mysql: MySQLWrapper):
        self.bot = bot
        self.mysql = mysql
        self.sonar = Sonar()

        self.discordForum = Forum("ECC-Discord", "ECC-Discord")
        self.discordForum.insert(self.mysql)

        self.discordAuthor = ForumAuthor("Discord", "-1")
        self.discordAuthor.insert(self.mysql)

        # self.generalThread = ForumThread("#general-chat", self.discordAuthor, self.discordForum.sqlID, hltvID = "709753463323754539")
        self.generalThread = ForumThread("#general-chat", self.discordAuthor, self.discordForum.sqlID, hltvID = "456834448558653451")
        self.generalThread.insert(self.mysql)

        # self.shitpostingThread = ForumThread("#shitposting-and-media", self.discordAuthor, self.discordForum.sqlID, hltvID = "727107131416903750")
        self.shitpostingThread = ForumThread("#shitposting-and-media", self.discordAuthor, self.discordForum.sqlID, hltvID = "468121733929369610")
        self.shitpostingThread.insert(self.mysql)

        self.mysql.db.commit()
    
    @commands.Cog.listener()
    async def on_message(self, message):

        # Checks if the message is in an observed channel and saves thread ID
        channelID = str(message.channel.id)
        threadID = 0

        if channelID == self.generalThread.hltvID:
            threadID = self.generalThread.sqlID
        elif channelID == self.shitpostingThread.hltvID:
            threadID = self.shitpostingThread.sqlID
        else:
            return

        # Compiles message info
        messageID = message.id
        content = message.clean_content
        authorID = message.author.id
        authorName = message.author.name
        timestamp = message.created_at

        # Calculates hate speech and offensive language rating
        rating = self.sonar.ping(f"{authorName}: {content}")
        hateRating = 0
        offRating = 0

        # Extracts confidence values for hate speech and offensive language from result
        for ratingClass in rating['classes']:
            if ratingClass['class_name'] == 'hate_speech':
                hateRating = ratingClass['confidence']
            elif ratingClass['class_name'] == 'offensive_language':
                offRating = ratingClass['confidence']

        author = ForumAuthor(authorName, authorID)
        author.insert(self.mysql)

        post = ForumPost(messageID, threadID, -1, author, content, timestamp, hateRating, offRating)
        post.insert(self.mysql)

        self.mysql.db.commit()
      



auth = AuthorizationInfo("auth.json")

print("Connecting to database...")
mysql = MySQLWrapper(auth)
initializeTables(mysql, False)

print("Initializing bot...")
bot = commands.Bot(command_prefix = '.ecc')
bot.add_cog(MainCog(bot, mysql))

print("Starting bot...")
bot.run(auth.discordToken)