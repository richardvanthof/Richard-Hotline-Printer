# Hotline print client
## Get started
1. Install dependencies using `pip install -r requirements.txt`
2. Make sure all hardware is connected, according to the following schematic:
TBD
The printer is a Welquiczj-890F (generic thermal printer) that is connected using USB to the raspberry pi.
3. Add an .env file with your server credentials
```
# API
HOST=http://api.hotline.therichard.space
USERNAME=YOURUSERNAMEHERE
PASSWORD=YOURPASSWORDHERE

```
4. Start the service by running `python app.py`