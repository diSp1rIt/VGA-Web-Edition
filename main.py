from flask import Flask, request, render_template, redirect
from data import db_session
from data.users import *
import hashlib
from threading import Timer
from colorama import Fore
from modules import VKApi
from config import *

W = Fore.WHITE
G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW
B = Fore.BLUE


def sha3(string):
    return hashlib.sha3_512(string.encode()).hexdigest()


app = Flask(__name__)
app.config['SECRET_KEY'] = sha3('httpsgithubcomlev2454')
parser = VKApi.VKParser(TOKEN)
authed = []


@app.route('/')
@app.route('/index.html')
def index():
    params = {
        'title': 'VGA',
        'page': 'main'
    }
    return render_template('index.html', **params)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def logging():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        global authed
        if not list(session.query(User).filter(User.login == request.form['login'])):
            return render_template('login.html', error='err')
        if not list(session.query(User).filter(User.hashed_password == sha3(request.form['password']))):
            return render_template('login.html', error='err')

        hash = sha3(request.form["password"])
        authed.append(hash)

        def close_session():
            del authed[authed.index(hash)]
            print(R + '[ ] ' + Y + f'{request.form["login"]} logged out.' + W)

        timer = Timer(43200, close_session)
        timer.start()
        print(G + '[ ] ' + B + f'{request.form["login"]}' + Y + ' logged in.' + W)
        return redirect(f'/work_ui/{hash}')


@app.route('/work_ui')
@app.route('/work_ui/<string:token>', methods=['POST', 'GET'])
def working_zone(token=None):
    if request.method == 'GET':
        global authed
        if token not in authed or token is None:
            return redirect('/login')
        params = {
            'error': '',
            'title': 'VGA User Interface',
            'group': ''
        }
        return render_template('work_ui.html', **params)
    else:
        addr = request.form['address']
        if 'http://vk.com/' not in addr and 'https://vk.com/' not in addr:
            params = {
                'title': 'VGA User Interface',
                'group': '',
                'error': 'err_didnt_find'
            }
            return render_template('work_ui.html', **params)
        elif parser.get_group(addr.split('vk.com/')[1]) is None:
            params = {
                'title': 'VGA User Interface',
                'group': '',
                'error': 'err_didnt_find'
            }
            return render_template('work_ui.html', **params)
        else:
            group_info = parser.get_group(addr.split('vk.com/')[1])
            params = {
                'title': 'VGA User Interface',
                'group': group_info,
                'keys': group_info.keys(),
                'error': ''
            }
            return render_template('work_ui.html', **params)


@app.route('/register', methods=['GET', 'POST'])
def registration():
    if request.method == 'GET':
        return render_template('register.html', error='')
    else:
        if list(session.query(User).filter(User.login == request.form['login'])):
            return render_template('register.html', error='err_login_exists')
        elif len(request.form['password1']) < 8:
            return render_template('register.html', error='err_len_passwd')
        elif request.form['password1'] != request.form['password2']:
            return render_template('register.html', error='err_dont_match')
        elif list(session.query(User).filter(User.email == request.form['email'])):
            return render_template('register.html', error='err_email_exists')
        new_user = User()
        new_user.login = request.form['login']
        new_user.email = request.form['email']
        new_user.hashed_password = sha3(request.form['password1'])
        session.add(new_user)
        session.commit()
        print(G + '[+] Added new user: ' + B + request.form['login'] + W)
        return redirect('/login')


if __name__ == '__main__':
    db_session.global_init("db/user.sqlite")
    session = db_session.create_session()
    app.run('192.168.0.105', 80)
