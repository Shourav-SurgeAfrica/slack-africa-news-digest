from flask import Flask
import run_daily_digest  # make sure this file exists
import traceback

app = Flask(__name__)

@app.route("/")
def home():
    return "SurgeScope is live."

@app.route("/trigger", methods=["GET"])
def trigger():
    try:
        run_daily_digest.main()  # call the function directly
        return "News digest triggered successfully!"
    except Exception as e:
        return f"Error: {e}\n\n{traceback.format_exc()}"
