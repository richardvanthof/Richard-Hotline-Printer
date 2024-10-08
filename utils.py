import uuid
import datetime
import csv
import requests
import socket

log_collection = []

# Logging function
def log(message: str, type='info'):
    entry = {
      'log_id': uuid.uuid4(),
      'timestamp': datetime.datetime.today(),
      'type': type,
      'message': message,
    }

    try: 
      with open('logs/hotline.log.csv', mode="a") as hotline_log:
        hotline_log = csv.writer(hotline_log, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        hotline_log.writerow([entry['timestamp'], entry['log_id'], entry['type'], entry['message']])

      print(message)
      log_collection.append(entry)

    except Exception as e:
       print(e)
       raise e



# Check internet connection
def is_online():
    timeout = 1

    try:
        requests.head("http://www.google.com/", timeout=timeout)
        return True
    except requests.ConnectionError:
        return False

def get_local_ip():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return ip