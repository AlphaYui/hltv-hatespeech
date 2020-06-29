from mysqlwrapper import MySQLWrapper
from datetime import datetime, timedelta

def initializeTables(mysql: MySQLWrapper, overwrite: bool = False):
    # Creates database tables
    # They all follow the same guidelines:
    #   - The first ID is the SQL ID on which tables can be joined
    #   - The second ID (HLTVID) is the unique identifier used to reconstruct the URL on HLTV.org
    #   - These are both unique, so "ON DUPLICATE" statements trigger if the same HLTV item is tried to be added twice

    # Posts: Contains all posts (responses to threads, or the initial post in a thread)
    # HLTVID - For https://www.hltv.org/forums/threads/2329019/whos-dumber#r43857044 it'd be: '2329019/whos-dumber#r43857044'
    #           (This has an overlap with the Thread HLTVID, but without it the uniqueness of a post couldn't be checked easily with ON DUPLICATE)
    # ThreadID - SQL ID of the thread the post is a response to
    # AuthorID - SQL ID of the author of the post
    # ReplyNum - Number of the reply in the thread (e.g. 3 for the 3rd response to a thread). 0 for the initial post.
    # Content - The content of the post in utf8
    # Time - The time at which the post was made
    # HateRating - A confidence score between 0.0 and 1.0, indicating how likely this post is hatespeech
    # OffRating- A confidence score between 0.0 and 1.0, indicating how likely this post contains offensive language
    mysql.createTable("Posts", (
        "PostID INT AUTO_INCREMENT, "
        "HLTVID VARCHAR(127) NOT NULL, "
        "ThreadID INT NOT NULL, "
        "AuthorID INT NOT NULL, "
        "ReplyNum INT NOT NULL, "
        "Content TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, "
        "Time DATETIME DEFAULT NOW(), "
        "HateRating FLOAT DEFAULT 0, "
        "OffRating FLOAT DEFAULT 0, "
        "PRIMARY KEY(PostID), "
        "UNIQUE (HLTVID)"
    ), 
    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    overwrite)

    # Authors: Contains all forum authors (accounts that created threads or posts)
    # HLTV - For https://www.hltv.org/profile/766189/nabaski it'd be '766189/nabaski'
    # Name - Forum name of the author
    mysql.createTable("Authors", (
        "AuthorID INT AUTO_INCREMENT, "
        "HLTVID VARCHAR(63) NOT NULL, "
        "Name VARCHAR(63) NOT NULL, "
        "PRIMARY KEY(AuthorID), "
        "UNIQUE (HLTVID)"
    ), 
    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    overwrite)

    # Threads: Contains all forum threads
    # HLTVID - For https://www.hltv.org/forums/threads/2329019/whos-dumber it'd be '2329019/whos-dumber'
    # ForumID - SQL ID of the forum the post was made in
    # AuthorID - SQL ID of the author who created the thread
    # NumResponses - The number of posts in the thread
    # Time - The time at which the thread was created
    mysql.createTable("Threads", (
        "ThreadID INT AUTO_INCREMENT, "
        "HLTVID VARCHAR(63) NOT NULL, "
        "ForumID INT NOT NULL, "
        "AuthorID INT NOT NULL, "
        "Title VARCHAR(127) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL, "
        "NumResponses INT DEFAULT 0, "
        "Time DATETIME DEFAULT NOW(), "
        "PRIMARY KEY(ThreadID), "
        "UNIQUE (HLTVID)"
    ), 
    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    overwrite)

    # Forums: Contains all forums that are monitored
    # HLTV - For https://www.hltv.org/forums/17/off-topic it'd be '17/off-topic'
    # Name - Name of the forum
    mysql.createTable("Forums", (
        "ForumID INT AUTO_INCREMENT, "
        "HLTVID VARCHAR(63) NOT NULL, "
        "Name VARCHAR(63) NOT NULL, "
        "PRIMARY KEY(ForumID), "
        "UNIQUE (HLTVID)"
    ),
    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    overwrite)

    # Signals: Used to pause or exit the program cleanly
    # Currently required signals:
    # End: If set to 1, this program will terminate after the end of the current refresh
    # Refresh: Time in minutes between refreshs
    mysql.createTable("Signals", (
        "SignalName VARCHAR(63), "
        "Value INT DEFAULT 0, "
        "PRIMARY KEY(SignalName)"
    ),
    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    overwrite)


class Forum:

    def __init__(self, name, hltvID = None, sqlID = None):
        self.name = name
        self.hltvID = hltvID
        self.sqlID = sqlID

    # Example: https://www.hltv.org/forums/17/off-topic
    def getURL(self):
        return f"https://www.hltv.org/forums/{self.hltvID}"

    def insert(self, mysql: MySQLWrapper):
        mysql.query(
            "INSERT INTO Forums (HLTVID, Name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE Name=%s;",
            (self.hltvID, self.name, self.name,)
        )

        self.sqlID = self.getSQLID(mysql)

    def getSQLID(self, mysql: MySQLWrapper):
        mysql.query(
            "SELECT ForumID FROM Forums WHERE HLTVID=%s;",
            (self.hltvID,)
        )

        result = mysql.fetchResults()

        if result is None:
            return None
        else:
            return result[0][0]


class ForumAuthor:

    def __init__(self, name, hltvID = None, url = None):
        self.name = name
        self.hltvID = hltvID
        self.sqlID = None
        if url is not None:
            self.hltvID = url[29:]

    # Example: https://www.hltv.org/profile/766189/nabaski
    def getURL(self):
        return f"https://www.hltv.org/profile/{self.hltvID}"

    def insert(self, mysql: MySQLWrapper):
        mysql.query(
            "INSERT INTO Authors (HLTVID, Name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE Name=%s;",
            (self.hltvID, self.name, self.name,)
        )

        self.sqlID = self.getSQLID(mysql)

    def getSQLID(self, mysql: MySQLWrapper):
        mysql.query(
            "SELECT AuthorID FROM Authors WHERE HLTVID=%s;",
            (self.hltvID,)
        )

        result = mysql.fetchResults()

        if result is None:
            return None
        else:
            return result[0][0]


class ForumPost:

    def __init__(self, shortID, threadID, index, author, content, timestamp, hateRating, offRating):
        self.shortID = shortID
        self.sqlID = None
        self.threadID = threadID
        self.index = index
        self.author = author
        self.content = content
        self.timestamp = timestamp
        self.hateRating = hateRating
        self.offRating = offRating

        self.threadHLTVID = ''

    def getHLTVID(self):
        if self.shortID == '':
            return self.threadHLTVID
        else:
            return f"{self.threadHLTVID}#{self.shortID}"

    # Example: https://www.hltv.org/forums/threads/2329019/whos-dumber#r43857044
    def getURL(self):
        return f"https://www.hltv.org/forums/threads/{self.getHLTVID()}"

    def insert(self, mysql: MySQLWrapper):
        mysql.query(
            (
                "INSERT INTO Posts (HLTVID, ThreadID, ReplyNum, AuthorID, Content, Time, HateRating, OffRating) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE HLTVID=%s;"
            ),
            (self.getHLTVID(), self.threadID, self.index, self.author.sqlID, self.content, self.timestamp, self.hateRating, self.offRating, self.getHLTVID(),)
        )

        self.sqlID = self.getSQLID(mysql)

    def getSQLID(self, mysql: MySQLWrapper):
        mysql.query(
            "SELECT PostID FROM Posts WHERE HLTVID=%s;",
            (self.getHLTVID(),)
        )

        result = mysql.fetchResults()

        if result is None:
            return None
        else:
            return result[0][0]


class ForumThread:

    def __init__(self, title, author, forumID, hltvID = None, url = None):
        self.sqlID = None
        self.title = title
        self.author = author
        self.forumID = forumID

        self.content = None
        self.timestamp = None
        self.posts = []

        if hltvID is None:
            self.hltvID = url[36:]
        else:
            self.hltvID = hltvID   

    # Example: https://www.hltv.org/forums/threads/2329019/whos-dumber
    def getURL(self):
        return f"https://www.hltv.org/forums/threads/{self.hltvID}"

    def insert(self, mysql: MySQLWrapper):
        mysql.query(
            (
                "INSERT INTO Threads (HLTVID, ForumID, AuthorID, Title, NumResponses, Time) VALUES "
                "(%s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE HLTVID=%s;"
            ),
            (self.hltvID, self.forumID, self.author.sqlID, self.title, len(self.posts), self.timestamp, self.hltvID,)
        )

        self.sqlID = self.getSQLID(mysql)

    def getSQLID(self, mysql: MySQLWrapper):
        mysql.query(
            "SELECT ThreadID FROM Threads WHERE HLTVID=%s;",
            (self.hltvID,)
        )

        result = mysql.fetchResults()

        if result is None:
            return None
        else:
            return result[0][0]