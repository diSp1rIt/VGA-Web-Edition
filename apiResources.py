from flask_restful import Resource, abort, reqparse
from data import db_session
from data.users import *
from data.groups import *
from flask import jsonify
import hashlib


def sha3(string):
    return hashlib.sha3_512(string.encode()).hexdigest()


user_parser = reqparse.RequestParser()
user_parser.add_argument('login', required=True)
user_parser.add_argument('email', required=True)
user_parser.add_argument('passwd', required=True)


class UserResource(Resource):
    def get_user(self, user_id):
        session = db_session.create_session()
        user = session.query(User).get(user_id)
        if not user:
            abort(404, message=f"User {user_id} not found")
        else:
            return user

    def get(self, user_id):
        user = self.get_user(user_id)
        return jsonify({'users': [user.to_dict()]})


class UserListResource(Resource):
    def get(self):
        session = db_session.create_session()
        users = session.query(User).all()
        return jsonify({'users': [user.to_dict() for user in users]})

    def post(self):
        session = db_session.create_session()
        args = user_parser.parse_args()
        passwd = args['passwd']
        login = args['login']
        email = args['email']
        session = db_session.create_session()
        if session.query(User).filter(User.login == login).first():
            abort(409, message=f"User \'{args['login']}\' already exists")
        elif len(passwd) < 8:
            abort(412, message=f'Password too short')
        elif passwd.isdigit() or passwd.lower() == passwd or passwd.upper() == passwd:
            abort(412, message=f'Password needs contain lower case, upper case and numbers')
        else:
            new_user = User()
            new_user.hashed_password = sha3(passwd)
            new_user.login = login
            new_user.email = email
            session.add(new_user)
            session.commit()
            return jsonify({'users': [new_user.to_dict()]})


class GroupResource(Resource):
    def get_group(self, group_id: str):
        session = db_session.create_session()
        if group_id.isdigit():
            group = session.query(Group).get(group_id)
            if not group:
                abort(404, message=f"Group {group_id} not found")
            return group
        else:
            group = list(session.query(Group).filter(Group.screen_name == group_id))
            if not group:
                abort(404, message=f"Group {group_id} not found")
            return group[0]

    def get(self, group_id):
        group = self.get_group(group_id)
        return jsonify({'users': group.to_dict()})