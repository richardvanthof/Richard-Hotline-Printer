import asyncio
from utils import *
import threading


# Updates the 'printed' status in the database to true
def update_firebase_message(db, user: str, messageID: str):
    print("☑️  Updating print status %s on server"%(messageID))
    try:
        doc_ref = db.collection(u'Users').document(user).collection(u'Messages').document(messageID)
        doc_ref.update({
            'printed': True
        })
        return True
    except:
        return "Google Cloud could not be reached"

# Create an Event for notifying main thread.
callback_done = threading.Event()

# Create a callback on_snapshot function to capture changes
def on_snapshot(col_snapshot, changes, read_time):
    print("Callback received query snapshot.")
    print("Current cities in California:")
    for doc in col_snapshot:
        print(f"{doc.id}")
    callback_done.set()


# Checks if new messages are prescent with a false 'printed' status; 
# if so: they get downloaded and added to the 'messages' list
async def getData(db, user: str):
  messages = []
  try:
    docs = (
       db.collection(u'Users')
       .document(user)
       .collection(u'messages')
       .where('printed', '==', False)
       .stream()
    )
    async for doc in docs:
       messages.append({doc.id: doc.to_dict()})
    return messages
  except Exception as e:
     raise e
   
    
        

