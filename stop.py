from mysqlwrapper import MySQLWrapper
from authorization import AuthorizationInfo

auth = AuthorizationInfo("auth.json")
mysql = MySQLWrapper(auth)

mysql.query("UPDATE Signals SET Active=1 WHERE SignalName=%s;", ('End'))
print('Sent end signal to scraper. It will terminate after the current cycle is complete.')