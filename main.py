from flask import Flask, request, render_template, redirect, session
from data import db_session
from data.users import *
import hashlib
from threading import Thread
from colorama import Fore
from modules import VKApi
from config import *

# Цвета для вывода всяких отладочных данных в консоль
W = Fore.WHITE
G = Fore.GREEN
R = Fore.RED
Y = Fore.YELLOW
B = Fore.BLUE


# Объединил все действия хеширование в одну функцию
def sha3(string):
    return hashlib.sha3_512(string.encode()).hexdigest()


# Запуск и настройка программы
app = Flask(__name__)
app.config['SECRET_KEY'] = sha3('httpsgithubcomlev2454')
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=2)
parser = VKApi.VKParser(TOKEN)  # Парсер групп вк
tasks_for_add_to_db = []  # Списко задач на обновление базы данных


# Функция обновления/добавление пользователей
def add_from_tasks():
    global tasks_for_add_to_db

    #############################################################
    # Пока спикок задачь не будет пуст, будет идти обновление   #
    #############################################################

    while len(tasks_for_add_to_db) != 0:
        task = tasks_for_add_to_db[0]

        #############################################################################
        #   Список хранит хранит в себе кортеж, состоящий из объекта функции        #
        # парсера, id группы вк, текушей сессии базы данных и кортежа с часами,     #
        # минутами работы, а также кол-вом пользователей в группе.                  #
        #                                                                           #
        #   Почему часы и минуты работы и кол-во пользователей в одном кортеже?     #
        #   Это было сделанно для возможности указания времени работы не только в   #
        # отладчике, но на самом сайте.                                             #
        #############################################################################

        err = task[0](task[1], task[2], task[3])  # По окончанию обновления парсер вернет 0, если всё успешно
        if err:
            print(f'Отмена в выполнении добавления/обновления базы данных. Группа: {task[1]}')
        else:
            del tasks_for_add_to_db[tasks_for_add_to_db.index(task)]  # Удаление задачи после удачного завершения


procedure = Thread(target=add_from_tasks)  # Поток функции обновления


# Обработка домашней страницы
@app.route('/')
@app.route('/index.html')
def index():
    params = {
        'title': 'VGA',
        'page': 'main'
    }
    return render_template('index.html', **params)


# Обработка страницы "О проекте"
@app.route('/about')
def about():
    return render_template('about.html')


# Обработка страници входа
@app.route('/login', methods=['GET', 'POST'])
def logging():
    if 'authorized' not in session:
        session['authorized'] = 0
    if session.get('authorized'):
        return redirect(f'/work_ui')
    else:
        if request.method == 'GET':
            return render_template('login.html')
        else:
            if not list(session_db.query(User).filter(User.login == request.form['login'])):
                return render_template('login.html', error='err')
            if not list(session_db.query(User).filter(User.hashed_password == sha3(request.form['password']))):
                return render_template('login.html', error='err')
            session['authorized'] = 1
            session.permanent = True
            print(G + '[ ] ' + B + f'{request.form["login"]}' + Y + ' logged in.' + W)
            return redirect(f'/work_ui')


@app.route('/register', methods=['GET', 'POST'])
def registration():
    if request.method == 'GET':
        return render_template('register.html', error='')
    else:
        if list(session_db.query(User).filter(User.login == request.form['login'])):
            return render_template('register.html', error='err_login_exists')
        elif len(request.form['password1']) < 8:
            return render_template('register.html', error='err_len_passwd')
        elif request.form['password1'] != request.form['password2']:
            return render_template('register.html', error='err_dont_match')
        elif list(session_db.query(User).filter(User.email == request.form['email'])):
            return render_template('register.html', error='err_email_exists')
        new_user = User()
        new_user.login = request.form['login']
        new_user.email = request.form['email']
        new_user.hashed_password = sha3(request.form['password1'])
        session_db.add(new_user)
        session_db.commit()
        print(G + '[+] Added new user: ' + B + request.form['login'] + W)
        return redirect('/login')


@app.route('/work_ui')
def working_zone():
    if 'authorized' not in session or not session.get('authorized'):
        return redirect('/login')
    if not list(request.args):
        params = {
            'error': '',
            'title': 'VGA User Interface',
            'group': ''
        }
        return render_template('work_ui.html', **params)
    else:
        addr = request.args.get('address')
        if 'http://vk.com/' not in addr and 'https://vk.com/' not in addr or parser.get_group(
                addr.split('vk.com/')[1]) is None:
            params = {
                'title': 'VGA User Interface',
                'group': '',
                'error': 'err_didnt_find'
            }
            return render_template('work_ui.html', **params)
        else:
            group_id = addr.split('vk.com/')[1]
            group_info = parser.get_group(group_id)
            url_group_photo = parser.get_group_picture(group_id)
            params = {
                'title': 'VGA User Interface',
                'group': group_info,
                'keys_group': group_info.keys(),
                'error': '',
                'has_group': 1,
                'img': url_group_photo,
                'main_url': f'/work_ui'
            }
            if tasks_for_add_to_db and str(group_info['id']) in [task_id[1] for task_id in tasks_for_add_to_db]:
                params['has_group'] = 'updating'
            elif not session_db.query(UserVK).filter(UserVK.groups.like(f'%{group_info["id"]}%')).first():
                params['has_group'] = 0

            return render_template('work_ui.html', **params)


@app.route('/work_ui/request')
def request_to_update_data():
    if 'authorized' not in session or not session.get('authorized'):
        return redirect('/login')
    group_id = request.args.get('group_id')
    time = parser.get_time(group_id)
    task = (parser.get_all_users, group_id, session_db, time)
    if task not in tasks_for_add_to_db:
        tasks_for_add_to_db.append(task)
        if not procedure.is_alive():
            procedure.start()
        print(len(tasks_for_add_to_db))
    params = {
        'hour': time[0],
        'minutes': time[1],
        'tasks': len(tasks_for_add_to_db),
        'current': tasks_for_add_to_db.index(task) + 1,
        'group_id': group_id
    }
    return render_template('request.html', **params)


if __name__ == '__main__':
    db_session.global_init("db/user.sqlite")
    session_db = db_session.create_session()
    app.run('localhost', 8080)
