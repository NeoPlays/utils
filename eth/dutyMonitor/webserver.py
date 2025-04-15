from flask import Flask, send_from_directory

app = Flask(__name__, static_folder='/data', static_url_path='')

@app.route('/')
def index():
    return send_from_directory('/data', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('/data', filename)
