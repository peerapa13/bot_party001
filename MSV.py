from flask import Flask
from threading import Thread 

app = Flask('')

@app.route('/')
def home():
    return "SR"

def run():
    app.run(host='0.0.0.0', port=8080)

def server_on(): # เอา (0) ออกถ้าไม่ได้ใช้ parameter
    t = Thread(target=run)
    t.start()