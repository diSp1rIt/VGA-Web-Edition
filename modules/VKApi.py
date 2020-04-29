import vk
import json
from threading import Thread
from time import sleep
from data.users import *
from os import remove, path


class VKParser:
    def __init__(self, token):
        try:
            session = vk.Session(token)
            self.vk_api = vk.API(session)
        except Exception as e:
            print(e)
            exit(-1)

    def get_group(self, group_id):
        fields = 'id, name, screen_name, description, is_closed, deactivated, city, country'
        try:
            response = self.vk_api.groups.getById(group_id=group_id, fields=fields, v='5.103')[0]
        except Exception as e:
            print(e)
        else:
            converted_response = dict()
            for field in fields.split(', '):
                if field not in response.keys():
                    converted_response[field] = None
                else:
                    if field == 'city' or field == 'country':
                        converted_response[field] = response[field]['title']
                    elif field == 'is_closed':
                        converted_response[field] = True if response[field] else False
                    else:
                        converted_response[field] = response[field]
            return converted_response
        return None

    def get_group_picture(self, group_id):
        try:
            response = self.vk_api.groups.getById(group_id=group_id, fields='photo_max', v='5.103')[0]
        except Exception as e:
            print(e)
        else:
            return response['photo_200']

    def get_user(self, user_id):
        fields = ['id', 'first_name', 'last_name', 'verified', 'sex', 'bdate', 'city', 'country', 'home_town', 'domain',
                  'contacts', 'site', 'education', 'universities', 'schools', 'status', 'followers_count',
                  'common_count', 'occupation', 'nickname', 'relatives', 'relation', 'personal', 'connections',
                  'exports', 'activities', 'interests', 'music', 'movies', 'tv', 'books', 'games', 'about', 'quotes']
        try:
            response = self.vk_api.users.get(users_ids=user_id, fields=', '.join(fields), v='5.103')[0]
        except Exception as e:
            print(e)
        else:
            converted_response = dict()
            for field in fields:
                if field not in response.keys() or response[field] == '':
                    converted_response[field] = None
                else:
                    if field == 'city' or field == 'country':
                        converted_response[field] = response[field]['title']
                    elif field == 'is_closed':
                        converted_response[field] = True if response[field] else False
                    else:
                        converted_response[field] = response[field]
            return converted_response
        return None

    def get_all_users(self, group_id, session=None):
        try:
            i = 0
            count = self.vk_api.groups.getMembers(count=0, offset=0, v='5.103', group_id=group_id)['count']
            fields = ['id', 'first_name', 'last_name', 'sex', 'bdate', 'city', 'country', 'domain']

            def getting(os):
                nonlocal group_id
                data = self.vk_api.groups.getMembers(offset=os, v='5.103', group_id=group_id, fields=', '.join(fields))[
                    'items']
                if data is not None:
                    with open(f'temp_files/temp{os}.json', 'w') as f:
                        json.dump(data, f)
                    data = None
                else:
                    print('Data is None.')

            for offset in range(0, count + 1, 1000):
                thr = Thread(target=getting, args=(offset,))
                thr.start()
                sleep(1)

            for offset in range(0, count + 1, 1000):
                if path.exists(f'temp_files/temp{offset}.json'):
                    with open(f'temp_files/temp{offset}.json', 'r') as f:
                        data = json.load(f)
                    remove(f'temp_files/temp{offset}.json')
                else:
                    data = self.vk_api.groups.getMembers(offset=offset, v='5.103', group_id=group_id, fields=', '.join(fields))[
                        'items']
                    sleep(1)
                for user in data:
                    if not list(session.query(UserVK).filter(UserVK.id == user['id'])):
                        new_user = UserVK()
                        new_user.id = user['id']
                        new_user.firstname = user['first_name']
                        new_user.lastname = user['last_name']
                        if 'bdate' in user.keys():
                            new_user.bdate = user['bdate']
                        else:
                            new_user.bdate = None
                        if 'city' in user.keys():
                            new_user.city = user['city']['title']
                        else:
                            new_user.city = None
                        if 'country' in user.keys():
                            new_user.country = user['country']['title']
                        else:
                            new_user.country = None
                        new_user.domain = user['domain']
                        new_user.groups = group_id
                        new_user.sex = user['sex']
                        session.add(new_user)
                    else:
                        old_user = session.query(UserVK).filter(UserVK.id == user['id']).first()
                        old_user.groups = old_user.groups + ', ' + group_id
                print(i * 1000)
                i += 1
            session.commit()
            print('Commited')
        except Exception as e:
            print(e)
            return 'terminate'
        return 0
