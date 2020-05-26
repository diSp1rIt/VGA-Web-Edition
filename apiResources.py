from flask_restful import Resource, abort
from data import db_session
from data.users import *
from data.groups import *
from flask import jsonify


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
        return jsonify({'users': user.to_dict()})


class GroupResource(Resource):
    def get_group(self, group_id: str):
        session = db_session.create_session()
        if group_id.isdigit():
            group = session.query(Group).get(group_id)
            if not group:
                abort(404, message=f"User {group_id} not found")
            return group
        else:
            group = list(session.query(Group).filter(Group.screen_name == group_id))
            if not group:
                abort(404, message=f"User {group_id} not found")
            return group[0]

    def get(self, group_id):
        group = self.get_group(group_id)
        return jsonify({'users': group.to_dict()})