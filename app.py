from flask import Flask, render_template, jsonify
from flask_cors import CORS
import requests
from datetime import datetime
import threading
import time
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
HISTORY_FILE = 'history.json'
HISTORY_LENGTH = 20
UPDATE_INTERVAL = 30

# DEFINED ORDER: The frontend will display exactly in this sequence.
SITES_CONFIG = [
    ('Self-Service', 'https://apps.uillinois.edu/selfservice'),
    ('Canvas', 'https://canvas.illinois.edu'),
    ('MyIllini', 'https://myillini.illinois.edu'),
    ('Course Explorer', 'https://courses.illinois.edu'),
    ('UIUC Status', 'https://status.illinois.edu'),
    ('Media Space', 'https://mediaspace.illinois.edu'),
    ('APPS Directory', 'https://apps.uillinois.edu'),
    ('Illinois.edu', 'https://illinois.edu'),
    'Student Affairs': 'https://studentaffairs.illinois.edu', # Can mix types if needed, but tuple is safer for order
    ('Admissions', 'https://admissions.illinois.edu'),
    ('University Housing', 'https://housing.illinois.edu'),
    ('Library', 'https://library.illinois.edu'),
    ('Technology Services', 'https://techservices.illinois.edu'),
    ('Box', 'https://uofi.box.com'),
    ('Webstore', 'https://webstore.illinois.edu')
]

# Normalize to a dict for easy lookup, but we keep SITES_CONFIG for order
SITES_DICT = {name: url for name, url in SITES_CONFIG if isinstance(name, str) is False}
# Fix for the mixed list above, let's just use a list of tuples for strict ordering
ORDERED_SITES = [
    ('Self-Service', 'https://apps.uillinois.edu/selfservice'),
    ('Canvas', 'https://canvas.illinois.edu'),
    ('MyIllini', 'https://myillini.illinois.edu'),
    ('Course Explorer', 'https://courses.illinois.edu'),
    ('UIUC Status', 'https://status.illinois.edu'),
    ('Media Space', 'https://mediaspace.illinois.edu'),
    ('APPS Directory', 'https://apps.uillinois.edu'),
    ('Illinois.edu', 'https://illinois.edu'),
    ('Student Affairs', 'https://studentaffairs.illinois.edu'),
    ('Admissions', 'https://admissions.illinois.edu'),
    ('University Housing', 'https://housing.illinois.edu'),
    ('Library', 'https://library.illinois.edu'),
    ('Technology Services', 'https://techservices.illinois.edu'),
    ('Box', 'https://uofi.box.com'),
    ('Webstore', 'https://webstore.illinois.edu')
]

status_history = {}
current_status = {}
last_check_time = None

def load_history():
    global status_history, current_status, last_check_time
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                status_history = data.get('history', {})
                # Trim history
                for name in status_history:
                    status_history[name] = status_history[name][-HISTORY_LENGTH:]
                current_status = data.get('current', {})
                if data.get('last_check'):
                    last_check_time = datetime.fromisoformat(data.get('last_check'))
        except Exception as e:
            logger.error(f"Load error: {e}")

def save_history():
    try:
        data = {
            'history': status_history,
            'current': current_status,
            'last_check': last_check_time.isoformat() if last_check_time else None
        }
        with open(HISTORY_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Save error: {e}")

load_history()

def check_website(url):
    try:
        start = time.time()
        headers = {'User-Agent': 'UIUC-Status-Monitor/1.0'}
        resp = requests.get(url, timeout=5, headers=headers)
        return {
            'status': 'up' if resp.status_code == 200 else 'down',
            'time': round((time.time() - start) * 1000),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'status': 'down', 'time': 0, 'error': str(e), 'timestamp': datetime.now().isoformat()}

def monitor_loop():
    global last_check_time
    logger.info("Monitor started...")
    while True:
        try:
            for name, url in ORDERED_SITES:
                res = check_website(url)
                current_status[name] = res
                
                if name not in status_history: status_history[name] = []
                status_history[name].append(res)
                if len(status_history[name]) > HISTORY_LENGTH:
                    status_history[name].pop(0)
            
            last_check_time = datetime.now()
            save_history()
            logger.info(f"Check done at {last_check_time}")
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        time.sleep(UPDATE_INTERVAL)

def get_payload():
    """Returns an ordered LIST of sites"""
    site_list = []
    
    # Iterate over ORDERED_SITES to preserve order
    for name, url in ORDERED_SITES:
        hist = status_history.get(name, [])
        
        # Calc Uptime
        if hist:
            up = sum(1 for h in hist if h['status'] == 'up')
            uptime = round((up / len(hist)) * 100, 1)
        else:
            uptime = 0.0
        
        site_list.append({
            'name': name,
            'url': url,
            'uptime': uptime,
            'current': current_status.get(name, {'status': 'unknown', 'time': 0}),
            'history': hist
        })

    return {
        'last_check': last_check_time.isoformat() if last_check_time else None,
        'sites': site_list # Sending as a List (Array)
    }

@app.route('/')
def index():
    return render_template('index.html', initial_data=get_payload())

@app.route('/api/status')
def get_status():
    return jsonify(get_payload())

if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') or not app.debug:
        threading.Thread(target=monitor_loop, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000)