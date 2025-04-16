from flask import Flask, send_from_directory, jsonify
import os
import json

DATA_PATH = "/app/data"

app = Flask(__name__, static_folder='/app/static', static_url_path='')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/validators')
def api_validators():
    path = os.path.join(DATA_PATH, "validators.json")
    if not os.path.exists(path):
        return jsonify([])
    with open(path) as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/api/sync_duties')
def api_sync_duties():
    path = os.path.join(DATA_PATH, "sync_duties.json")
    if not os.path.exists(path):
        return jsonify([])
    with open(path) as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/api/proposer_duties')
def api_proposer_duties():
    path = os.path.join(DATA_PATH, "proposer_duties.json")
    if not os.path.exists(path):
        return jsonify([])
    with open(path) as f:
        data = json.load(f)
    return jsonify(data)
