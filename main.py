import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from flask import Flask, request, jsonify

app = Flask(__name__)

class Machine:
    def __init__(self):
        self.session_list = []
        self.delay = 0
        self.url = None
        self.reactions_dict = {
            '1': 'like',
            '2': 'love',
            '3': 'care',
            '4': 'haha',
            '5': 'wow',
            '6': 'sad',
            '7': 'angry'
        }
        self.selected_reactions = []
        self.logged_in_accounts = []
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': 'Mozilla/5.0 (Linux; Android 12; SM-A037F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        }

    def boost_reaction(self, session):
        try:
            get_token = session.get('https://machineliker.net/auto-reactions').text
            token = re.search(r'name="_token" value="(.*?)"', get_token).group(1)
            hash_ = re.search(r'name="hash" value="(.*?)"', get_token).group(1)

            data = {
                'url': self.url,
                'limit': '20',
                'reactions[]': self.selected_reactions,
                '_token': token,
                'hash': hash_
            }

            response = session.post('https://machineliker.net/auto-reactions', headers=self.headers, data=data).text

            if "Error!" in response and "please try again after" in response:
                minutes = int(re.search(r'please try again after (\d+) minutes', response).group(1))
                self.delay = minutes * 60
                return f"Cooldown: Please wait {self.delay} seconds more"
            elif 'Order Submitted' in response:
                return f"Successfully increased reactions from {session}"
            else:
                return "Unexpected error occurred"
        except Exception as e:
            return f"Error boosting reaction: {e}"

    def login(self, fb_cookie):
        try:
            session = requests.Session()
            session.get('https://machineliker.net/login')
            headers = {
                'accept': 'application/json, text/plain, */*',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (Linux; Android 12; SM-A037F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
                'x-xsrf-token': session.cookies.get('XSRF-TOKEN').replace('%3D', '=')
            }
            data = {'session': fb_cookie}
            response = session.post('https://machineliker.net/login', headers=headers, data=data).json()

            if response['success']:
                name = response['user']['name']
                user_id = response['user']['id']
                self.logged_in_accounts.append(f"{user_id} | {name}")
                return session
            else:
                return None
        except Exception as e:
            return None

    def set_parameters(self, fb_cookies, link, reaction_types):
        self.url = link
        self.selected_reactions = [self.reactions_dict[x] for x in reaction_types]

    def process_boosting(self):
        results = []
        with ThreadPoolExecutor() as executor:
            for session in self.session_list:
                result = executor.submit(self.boost_reaction, session)
                results.append(result.result())
        return results

machine = Machine()

@app.route('/api', methods=['GET'])
def api():
    fb_cookie = request.args.get('cookie')
    link = request.args.get('link')
    reaction_types = request.args.get('type')

    if not fb_cookie or not link or not reaction_types:
        return jsonify({"error": "Missing parameters"}), 400

    # Set parameters and login
    machine.set_parameters([fb_cookie], link, reaction_types)
    session = machine.login(fb_cookie)

    if session:
        machine.session_list.append(session)
        results = machine.process_boosting()
        return jsonify({"results": results}), 200
    else:
        return jsonify({"error": "Invalid Facebook Cookie"}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Adjust the port if necessary
