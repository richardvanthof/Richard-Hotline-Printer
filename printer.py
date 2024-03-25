from utils import *
from escpos.printer import *

# Main functions
# Checks if printer is connected. If not this function will return an error 
# (BUG: build in a right error) that prevents printing.

def detectPrinter():
    # Checks if USB Printer is available. If not, the dummy printer is used.
    try:
        p = Usb(0x0416, 0x5011)
        log("👍   Printer Detected")
        return p
    except:
        log('No printer detected', 'error')
        raise p



# Function that prints the messages from the message contents (data: JS object) 
# to the specified device (device)
def printMessage(data, device):
    p = device
    created = str(data.get('created'))
    name = str(data.get('name'))
    contact = str(data.get('contact'))
    message = str(data.get('''message'''))
    print("🖨   Printing message from %s"%(name))
    # body = "PARSED DATA: name: %s, contact: %s, message: %s" % (name, contact, message)
    try:
        p.text("""
IMPORTANT MESSAGE:
%s

By: %s

%s


Contact:
%s

_______________________________
===============================
        """% (created, name, message, contact))
        return True
    except:
        return False
    


# Deletes message from the print que
def delete_from_printque(message):
    try:

        messageIndex = messages.index(message)
        messages.remove(messages[messageIndex])
        print("🗑   Deleted %s from print que"%(message[0]))
        return True
    except Exception as e:
        print(e)
        return False