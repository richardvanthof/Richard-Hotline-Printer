import threading
from flask import Flask, render_template, request, jsonify
from app import setup, print_loop, unlock_and_print_mssg
import global_vars
from utils import *
from threading import Thread
import json
import asyncio
from escpos.printer import *
import firebase_admin
from firebase_admin import credentials, firestore_async


db = None;

def main():
  app = Flask(__name__)
  user = "Jabe"

  def init():
    try:
      global_vars.initialize()

      # Run initial checks
      setup()

      # Create firestore client
      global db
      cred = credentials.Certificate('credentials/serviceAccountKey.json')
      firebase_admin.initialize_app(cred)
      db = firestore_async.client()

      # Start background processes
      def async_main_wrapper():
        try:
          asyncio.run(print_loop(user, db))
        except Exception as e:
           raise e

      th = Thread(target=async_main_wrapper)
      th.start()

      
    except Exception as e:
      log(e, 'error')
  
  # Website pages
  @app.route("/")
  def index():
      print(global_vars.messages)
      return render_template('index.html', queue=global_vars.messages)

  @app.route("/logs")
  def logs():
      return render_template('logs.html', logs=log_collection)

  @app.route("/settings")
  def settings():
      return render_template('settings.html')


  @app.route("/api/confirm", methods=['POST'])
  async def confirm_receipt_and_print():
      try:
          processed = []
          req = json.loads(request.data)
          for id in req['messageIDs']:
              resp = await unlock_and_print_mssg(id, user, db)
              if(not resp):
              #    print(resp)
                raise resp
              else:
                  # print(resp)
                  processed.append(id)
                  log(f"Confirmed receipt and printed message {id} via the web interface.")
          return jsonify({
              'success': True,
              'updated_messages': processed
          })
      except Exception as e:
          log(e, 'error')
          return jsonify({
              'success': False,
              'message': e
          })
  # Run initiliazation function
  init()
  return app

app = main()

if __name__ == '__main__':
    # Debug server get started when executing this file directly via the command line.
    app = main()
    # Start web sever
    app.run(host='0.0.0.0', port='8000', debug='True')
