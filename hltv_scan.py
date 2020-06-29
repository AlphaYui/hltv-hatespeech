from requests_html import HTMLSession
from mysqlwrapper import MySQLWrapper
from authorization import AuthorizationInfo
from forums import *

from hatesonar import Sonar
sonar = Sonar()

totalByteCount = 0
byteCount = 0

import time
from datetime import datetime, timedelta
import random


# Returns all threads on HLTV offtopic main page
def getForumThreads(session: HTMLSession, forum: Forum):
    # Requests the offtopic page HTML
    response = session.get(forum.getURL())

    global byteCount
    byteCount += len(response.content)

    # Selects the div containing the forum thread list
    forumDiv = response.html.find('.forumthreads')[0]

    # Fetches all rows from the thread list
    tableRows = forumDiv.find('tr.tablerow')
    threads = []

    # Converts every row into a thread object
    for row in tableRows:
        # Gets thread title and URL
        tdName = row.find('td.name')[0]
        threadURL = tdName.absolute_links.pop()
        threadName = tdName.text

        # Gets reply count
        tdReplies = row.find('td.replies')[0]
        replyCount = int(tdReplies.text)

        # Gets thread author
        tdAuthor = row.find('td.author')[0]
        authorURL = tdAuthor.absolute_links.pop()
        authorName = tdAuthor.text
        author = ForumAuthor(authorName, url = authorURL)

        # Creates thread object and adds it to list
        newThread = ForumThread(threadName, author, forum.sqlID, url = threadURL)
        threads += [newThread]
    
    return threads



# Loads info for a given forum thread
def loadThreadContent(session: HTMLSession, thread: ForumThread):
    # Requests the thread HTML
    response = session.get(thread.getURL())

    global byteCount
    byteCount += len(response.content)

    # Extracts all posts from it
    replies = response.html.find('.post, .forumthread')

    for reply in replies:
        replyNumAnchors = reply.find('.replyNum')
        replyNum = 0

        # Retrieves the post content
        content = reply.find('.forum-middle')[0].text 
        timestampStr = reply.find('.forum-bottombar')[0].text
        timestamp = datetime.strptime(timestampStr, "%Y-%m-%d %H:%M")
        postID = ''

        # These fields only exist for replies, not the top post, so their existence is checked
        if len(replyNumAnchors) > 0:
            replyNumStr = reply.find('.replyNum')[0].text
            replyNum = int(replyNumStr[1:])
        
            postID = reply.attrs['id']
        else:
            thread.timestamp = timestamp

        # Retrieves author information
        authorAnchor = reply.find('.authorAnchor')[0]
        authorName = authorAnchor.text
        authorURL = authorAnchor.absolute_links.pop()
        author = ForumAuthor(authorName, url = authorURL)

        # Replaces underscores with spaces so that the net can analyze the name properly
        authorNameWithSpaces = authorName.replace('_', ' ')

        # Calculates hate speech and offensive language rating
        rating = sonar.ping(f"{authorNameWithSpaces}: {content}")
        hateRating = 0
        offRating = 0

        # Extracts confidence values for hate speech and offensive language from result
        for ratingClass in rating['classes']:
            if ratingClass['class_name'] == 'hate_speech':
                hateRating = ratingClass['confidence']
            elif ratingClass['class_name'] == 'offensive_language':
                offRating = ratingClass['confidence']

        newPost = ForumPost(postID, thread.sqlID, replyNum, author, content, timestamp, hateRating, offRating)
        thread.posts += [newPost]


# Returns the list of forums that should be observed
def getForums(mysql: MySQLWrapper):

    mysql.query("SELECT ForumID, HLTVID, Name FROM Forums;")
    results = mysql.fetchResults()

    if results is None:
        return []
    else:
        forums = []

        for row in results:
            forumInfo = Forum(
                sqlID = row[0], hltvID = row[1], name = row[2]
            )

            if '/' in forumInfo.hltvID:
                forums += [forumInfo]
        
        return forums


def getRefreshTime(mysql: MySQLWrapper):
    mysql.query("SELECT Value FROM Signals WHERE SignalName='Refresh';")
    results = mysql.fetchResults()

    if results is None:
        return 30
    else:
        return results[0][0]

# Sets the End-Signal of the database
def setEndSignal(mysql: MySQLWrapper, enable: bool):
    enableInt = 0
    if enable:
        enableInt = 1
    mysql.query("INSERT INTO Signals (SignalName, Value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE Value=%s;", ('End', enableInt, enableInt,))
    mysql.db.commit()

# Retrieves the End-Signal of the database
def getEndSignal(mysql: MySQLWrapper):
    mysql.query("SELECT Value FROM Signals WHERE SignalName='End';")
    results = mysql.fetchResults()

    if results is None or results[0][0] == 1:
        return True
    else:
        return False


# Connect to MySQL database
auth = AuthorizationInfo("auth.json")
mysql = MySQLWrapper(auth)
overwrite = False

# Creates required tables
initializeTables(mysql, overwrite)

# Defines forums to be observed
forums = []
forums += [Forum("Offtopic", "17/off-topic")]
forums += [Forum("CSGO", "28/counter-strike-global-offensive")]
forums += [Forum("Hardware", "16/hardware-tweaks")]

for forum in forums:
    forum.insert(mysql)

# By default, the forums are scraped every 15min
mysql.query("INSERT INTO Signals (SignalName, Value) VALUES ('Refresh', 15) ON DUPLICATE KEY UPDATE SignalName='Refresh';")
mysql.db.commit()

# Starts a new HTML-session
session = HTMLSession()

setEndSignal(mysql, False)
while not getEndSignal(mysql):
    # Resets the refresh timer and debug output
    lastUpdateTime = datetime.now()
    timeStr = lastUpdateTime.strftime("%d.%m.%Y, %H:%M:%S")
    print(f"Starting new update at {timeStr}!")

    # Resets data counter each cycle
    byteCount = 0

    # Loads all forums that should be observed
    forums = getForums(mysql)

    forumCount = 1
    for forum in forums:
        print(f"Updating forum {forumCount}/{len(forums)}: {forum.name}")

        # Loads all threads for the forum
        threads = getForumThreads(session, forum)

        threadCount = 1
        for thread in threads:
            loadThreadContent(session, thread)

            # Adds the thread author to the database, or updates them if they already exist
            thread.author.insert(mysql)

            # Inserts the thread into the database, or updates it if it already exists
            thread.insert(mysql)
            mysql.db.commit()

            # Iterates over the posts a second time and adds the posts with the linked thread SQL ID
            for post in thread.posts:
                # Adds post and author to the database, or ignores it if it already exists
                post.threadID = thread.sqlID
                post.threadHLTVID = thread.hltvID
                post.author.insert(mysql)
                post.insert(mysql)
                mysql.db.commit()

            print(f"\tThread {threadCount}/{len(threads)}: {thread.title} ({len(thread.posts)-1} replies)")
            
            # Very conservative, slightly randomized rate limit as no high refresh rates are required
            time.sleep(2.0 + random.random())
            threadCount += 1

        # Commits changes to the database

        forumCount += 1
        totalByteCount += byteCount

    print(f"Update complete! Data downloaded: {byteCount/1e+6} MB. {totalByteCount/1e+9} GB downloaded so far.")

    # Checks how long the one refresh cycle should be
    cycleDurationMin = getRefreshTime(mysql)
    nextUpdateTime = lastUpdateTime + timedelta(minutes = cycleDurationMin)

    # Outputs time of next refresh
    if datetime.now() < nextUpdateTime:
        timeStr = nextUpdateTime.strftime("%d.%m.%Y, %H:%M:%S")
        timeUntilNextUpdate = nextUpdateTime - datetime.now()
        print(f"Next update at {timeStr}. (In {timeUntilNextUpdate.total_seconds()/60} minutes)")

    # Waits until the next refresh cycle should start or an end signal is received
    while datetime.now() < nextUpdateTime and not getEndSignal(mysql):
        time.sleep(5.0)
