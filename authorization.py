# This class manages the information required for application authorization
# like e.g. API-tokens, login details, ...
#
# Example JSON-file:
# {
#     "Discord": {
#         "Token": "",
#         "ClientID": "",
#         "ClientSecret": ""
#     },
#     "MySQL": {
#         "IP": "",
#         "User": "",
#         "Password": "",
#         "Database": ""
#     }
# }

import json
import datetime

class AuthorizationInfo:

    # Constructor
    # Loads authorization data from given JSON-file, or uses default values if none is given
    # path: Path of the JSON-file containing the authorization information
    def __init__(self, path = None): 
        if path is None:
            self.__initDefaults()
        else:
            self.loadFromJSON(path)

    # Sets all authorization data to default values
    def __initDefaults(self):
        self.discordToken = ""
        self.discordClientID = ""
        self.discordClientSecret = ""

        self.mysqlIP = ""
        self.mysqlUser = ""
        self.mysqlPassword = ""
        self.mysqlDatabase = ""

        self.authPath = None

    # Loads authorization data from a given JSON-file. An example file is in the documentation at the top of this file's documentation
    # path: Path of the JSON-file to be loaded
    def loadFromJSON(self, path):
        with open(path, "r") as f:
            authJSON = json.loads(f.read())

            discordJSON = authJSON["Discord"]
            self.discordToken = discordJSON["Token"]
            self.discordClientID = discordJSON["ClientID"]
            self.discordClientSecret = discordJSON["ClientSecret"]

            mysqlJSON = authJSON["MySQL"]
            self.mysqlIP = mysqlJSON["IP"]
            self.mysqlUser = mysqlJSON["User"]
            self.mysqlPassword = mysqlJSON["Password"]
            self.mysqlDatabase = mysqlJSON["Database"]

            self.authPath = path

    # Saves authorization Datei to a given JSON-file.
    # path: Path of the JSON-file to which the data should be saved
    def saveToJSON(self, path):
        authJSON = {
                "Discord": {
                    "Token": self.discordToken,
                    "ClientID": self.discordClientID,
                    "ClientSecret": self.discordClientSecret
                },
                "MySQL": {
                    "IP": self.mysqlIP,
                    "User": self.mysqlUser,
                    "Password": self.mysqlPassword,
                    "Database": self.mysqlDatabase
                }
            }

        with open(path, "w") as f:
            json.dump(authJSON, f, ensure_ascii=True, indent=4)
