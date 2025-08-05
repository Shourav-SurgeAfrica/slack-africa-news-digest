from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "SurgeScope is live."

@app.route("/trigger", methods=["GET"])
def trigger():
    try:
        subprocess.run(["python", "run_daily_digest.py"])
        return "News digest triggered successfully."
    except Exception as e:
        return f"Error: {e}"
