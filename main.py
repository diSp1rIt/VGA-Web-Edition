from flask import Flask, request, render_template, redirect, session
from data import db_session
from data.users import *
from data.groups import *
import hashlib
from threading import Thread
from colorama import Fore
from modules import VKApi
from config import *
from flask_mail import Mail, Message
from os import path
from random import randint as ri

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
app.config.update(
    MAIL_SERVER='smtp.googlemail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='groupanalyzer@gmail.com',
    MAIL_PASSWORD=MAIL_PASSWD,
    MAIL_DEFAULT_SENDER='groupanalyzer@gmail.com'
)
mail = Mail(app)
parser = VKApi.VKParser(TOKEN)  # Парсер групп вк
tasks_for_add_to_db = []  # Списко задач на обновление базы данных
mails_to_send = {}  # ключ - id группы, значение - список почт
__domain__ = 'localhost'
__port__ = 8080


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

        err = task[0](task[1], task[2], task[3])  # 0 - без ошибок
        if err:
            print(f'Отмена в выполнении добавления/обновления базы данных. Группа: {task[1]}')
        else:
            if len(mails_to_send[int(task[1])]):
                with app.app_context():
                    msg = Message('Завершено', recipients=mails_to_send[int(task[1])])
                    group_name = session_db.query(Group).filter(Group.id == int(task[1])).first().name
                    msg.body = f'Данные по группе с названием: "{group_name}" обновлены.'
                    mail.send(msg)
            del tasks_for_add_to_db[tasks_for_add_to_db.index(task)]


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

    # Создание сессии
    if 'authorized' not in session:
        session['authorized'] = 0

    # Проврека на авторизованность и наличие почты
    if session.get('authorized') and session.get('email') is not None:
        return redirect(f'/work_ui')
    else:
        if request.method == 'GET':
            return render_template('login.html')
        else:
            hashed_pass = sha3(request.form['password'])
            if not list(session_db.query(User).filter(User.login == request.form['login'])):
                return render_template('login.html', error='err')
            if not list(session_db.query(User).filter(User.hashed_password == hashed_pass)):
                return render_template('login.html', error='err')
            user = session_db.query(User).filter(User.login == request.form['login']).first()
            session['authorized'] = 1
            session['email'] = user.email
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
        if 'http://vk.com/' not in addr and 'https://vk.com/' not in addr:
            params = {
                'title': 'VGA User Interface',
                'group': '',
                'error': 'err_didnt_find'
            }
            print('Bad url')
            return render_template('work_ui.html', **params)
        else:
            screen_name = addr.split('vk.com/')[1]
            if not list(session_db.query(Group).filter((Group.screen_name == screen_name))):
                response = parser.get_group(screen_name)
                if response is None:
                    if 'public' in screen_name:
                        screen_name = 'club' + screen_name.strip('public')
                    elif 'event' in screen_name:
                        screen_name = 'club' + screen_name.strip('event')
            if not list(session_db.query(Group).filter((Group.screen_name == screen_name))):
                print('Group didn\'t find in db')
                print('Try find in VK')
                response = parser.get_group(screen_name)
                if response is None:
                    print('Group not exists')
                    params = {
                        'title': 'VGA User Interface',
                        'group': '',
                        'error': 'err_didnt_find'
                    }
                    return render_template('work_ui.html', **params)
                else:
                    print('Group found')
                    print('Adding to db')

                    new_group = Group()
                    new_group.id = response['id']
                    new_group.screen_name = response['screen_name']
                    new_group.is_closed = response['is_closed']
                    new_group.deactivated = response['deactivated']
                    new_group.description = response['description']
                    new_group.city = response['city']
                    new_group.country = response['country']
                    new_group.name = response['name']
                    new_group.icon = response['photo_200']
                    session_db.add(new_group)
                    session_db.commit()

                    print('Group added to db')
        group_info = session_db.query(Group).filter((Group.screen_name == screen_name)).first()
        url_group_photo = group_info.icon
        keys = ['id', 'name', 'description', 'city', 'country', 'screen_name', 'is_closed', 'deactivated']
        params = {
            'title': 'VGA User Interface',
            'group': group_info.__dict__,
            'keys_group': keys,
            'error': '',
            'img': url_group_photo,
            'main_url': f'/work_ui',
            'scr_name': group_info.screen_name
        }
        if tasks_for_add_to_db and str(group_info.id) in [task_id[1] for task_id in tasks_for_add_to_db]:
            params['has_group'] = 'updating'
        elif path.exists(f'static/info/{group_info.id}/'):
            params['has_group'] = 1
        else:
            params['has_group'] = 0
        return render_template('work_ui.html', **params)


@app.route('/work_ui/request')
def request_to_update_data():
    global procedure
    if 'authorized' not in session or not session.get('authorized'):
        return redirect('/login')
    if 'group_id' not in list(request.args) or 'group_id' not in list(request.args):
        return 'Invalid request. Please, use the site\'s buttons for working, not urls'
    group_id = request.args.get('group_id')
    group = session_db.query(Group).filter(Group.id == int(group_id)).first()
    if group.update_time is not None:
        print('Has update time')
        update_time = round(datetime.datetime.timestamp(group.update_time))
        now_time = round(datetime.datetime.timestamp(datetime.datetime.now()))
        print(datetime.timedelta(seconds=(now_time - update_time)).days)
        if datetime.timedelta(seconds=(now_time - update_time)).days < 31:
            scr_name = session_db.query(Group).filter(Group.id == int(group_id)).first().screen_name
            return redirect(f'/work_ui?address=https%3A%2F%2Fvk.com%2F{scr_name}')
    short_tasks_list = [elem[1] for elem in
                        tasks_for_add_to_db]  # Список заданий состоящий из id групп
    if group_id not in short_tasks_list:
        time = parser.get_time(group_id)
        if time == 'err_access_denied':
            return render_template('request.html', err=time)
        task = (parser.get_all_users, group_id, session_db, time)
        tasks_for_add_to_db.append(task)
        mails_to_send[int(group_id)] = []
        if not procedure.is_alive():
            procedure = Thread(target=add_from_tasks)  # Поток функции обновления
            procedure.start()
    else:
        task = tasks_for_add_to_db[short_tasks_list.index(group_id)]
    short_tasks_list = [elem[1] for elem in tasks_for_add_to_db]  # Обновление
    if 'send_email' in list(request.args):
        if request.args.get('send_email') == 'true':
            if int(group_id) in mails_to_send.keys():
                mails_to_send[int(group_id)].append(session.get('email'))
            else:
                return 'Invalid request. Please, use the site\'s buttons for working, not urls'
        else:
            if int(group_id) in mails_to_send.keys() and session.get('email') in mails_to_send[int(group_id)]:
                mails_to_send[int(group_id)].pop(mails_to_send[int(group_id)].index(session.get('email')))
            else:
                return 'Invalid request. Please, use the site\'s buttons for working, not urls'
    hour = task[-1][0]
    minute = task[-1][1]
    time_ = datetime.time(hour=hour, minute=minute)
    hour = sum([tasks_for_add_to_db[i][-1][0] for i in range(short_tasks_list.index(task[1]) + 1)])
    minute = sum([tasks_for_add_to_db[i][-1][1] for i in range(short_tasks_list.index(task[1]) + 1)])
    if minute // 60 != 0:
        hour += minute // 60
        minute %= 60
    all_time = datetime.time(hour=hour, minute=minute)

    params = {
        'time': time_,
        'tasks': len(tasks_for_add_to_db),
        'current': short_tasks_list.index(task[1]) + 1,
        'all_time': all_time,
        'group_id': group_id,
        'scr_name': request.args.get('scr_name')
    }

    if session.get('email') in mails_to_send[int(group_id)]:
        params['required_msg'] = False
    else:
        params['required_msg'] = True

    return render_template('request.html', **params)


@app.route('/tasks_list')
def tasks_listing():
    tasks = []
    for group_id in [elem[1] for elem in tasks_for_add_to_db]:
        group = session_db.query(Group).filter(Group.id == int(group_id)).first()
        tasks.append({'img': group.icon, 'name': group.name, 'scr_name': group.screen_name, 'id': group.id})
    return render_template('tasks_list.html', task_list=tasks)


@app.route('/support')
def support():
    return render_template('support.html')


if __name__ == '__main__':
    db_session.global_init("db/user.sqlite")
    session_db = db_session.create_session()
    app.run(__domain__, __port__)
