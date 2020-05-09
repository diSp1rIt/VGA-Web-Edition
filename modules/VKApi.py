import vk
from data.groups import *
from os import remove, path, mkdir
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import time as timelib


class VKParser:
    def __init__(self, token):
        try:
            session = vk.Session(token)
            self.vk_api = vk.API(session)
        except Exception as e:
            print(e)
            exit(-1)

    def get_group(self, group_id):
        fields = 'id, name, screen_name, description, is_closed, deactivated, city, country, photo_200'
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

    def get_user(self, user_id):
        fields = ['id', 'first_name', 'last_name', 'verified', 'sex', 'bdate', 'city', 'country',
                  'home_town', 'domain',
                  'contacts', 'site', 'education', 'universities', 'schools', 'status',
                  'followers_count',
                  'common_count', 'occupation', 'nickname', 'relatives', 'relation', 'personal',
                  'connections',
                  'exports', 'activities', 'interests', 'music', 'movies', 'tv', 'books', 'games',
                  'about', 'quotes']
        try:
            response = \
                self.vk_api.users.get(users_ids=user_id, fields=', '.join(fields), v='5.103')[0]
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

    def get_all_users(self, group_id, session=None, time=None):
        try:
            hour, mins, count = time
            print(
                f'Примерное время ожидания обновлени данных по {group_id}: {hour} ч. {mins:.2f} мин.')
            fields = ['id', 'first_name', 'last_name', 'sex', 'bdate', 'city', 'country', 'domain']

            mans_count = 0
            womans_count = 0
            man_ages_count = [0 for _ in range(100)]
            woman_ages_count = [0 for _ in range(100)]
            non_deactivated = 0
            banned_deactivated = 0
            deleted_deactivated = 0
            ages_count = [0 for _ in range(100)]

            for offset in range(0, count + 1, 1000):
                start_time = timelib.time()
                data = self.vk_api.groups.getMembers(offset=offset, v='5.103', group_id=group_id,
                                                     fields=', '.join(fields))['items']
                for user in data:
                    if user['sex'] == 1:
                        womans_count += 1
                    else:
                        mans_count += 1

                    if 'deactivated' in user.keys():
                        if user['deactivated'] == 'banned':
                            banned_deactivated += 1
                        elif user['deactivated'] == 'deleted':
                            deleted_deactivated += 1
                    else:
                        non_deactivated += 1

                    if 'bdate' in user.keys():
                        if user['bdate'].count('.') == 2:
                            age = datetime.datetime.now().year - int(user['bdate'].split('.')[-1])
                            if age < 100:
                                if user['sex'] == 1:
                                    woman_ages_count[age - 1] += 1
                                else:
                                    man_ages_count[age - 1] += 1
                                ages_count[age - 1] += 1
                            else:
                                ages_count[99] += 1
                end_time = round((timelib.time() - start_time) * 10) / 10
                print(end_time)
                if end_time < 0.06:
                    timelib.sleep(0.06 - end_time)

            if not path.exists(f'static/info/{group_id}'):
                mkdir(f'static/info/{group_id}')

            values = [mans_count, womans_count]
            labels = ['Мужчины', 'Женщины']
            fig1, ax1 = plt.subplots()
            ax1.pie(values, autopct='%1.2f%%')
            ax1.legend(labels=labels, bbox_to_anchor=(0.9, 1.1))
            fig1.savefig(f'static/info/{group_id}/sex_info.png')
            plt.close()

            values = [non_deactivated, banned_deactivated, deleted_deactivated]
            labels = ['Обычные', 'Забаненные', 'Удаленные']
            fig1, ax1 = plt.subplots()
            ax1.pie(values, autopct='%1.2f%%')
            ax1.legend(labels=labels, bbox_to_anchor=(0.9, 1.1))
            fig1.savefig(f'static/info/{group_id}/deactivated_info.png')
            plt.close()

            plt.rcParams['figure.figsize'] = [15, 5]
            fig1, ax1 = plt.subplots()
            ax1.set_xlabel('Возраст')
            ax1.set_ylabel('Количество')
            x = [i + 1 for i in range(100)]

            y = ages_count
            ax1.plot(x, y, 'go--')

            y = woman_ages_count
            ax1.plot(x, y, 'ro--')

            y = man_ages_count
            ax1.plot(x, y, 'bo--')

            ax1.grid()
            ax1.xaxis.set_major_locator(ticker.MultipleLocator(5))
            last_font_size = plt.rcParams['font.size']
            plt.rcParams['font.size'] = 22
            ax1.legend(labels=['Общий возрастной график', 'Женщины', 'Мужчины'], bbox_to_anchor=(1.1, 1.1))
            plt.savefig(f'static/info/{group_id}/ages_info.png')
            plt.rcParams['figure.figsize'] = [6.4, 4.8]
            plt.rcParams['font.size'] = last_font_size
            plt.close()

            group = session.query(Group).filter(Group.id == int(group_id)).first()
            group.update_time = datetime.datetime.now()
            session.commit()

            print('ЗАВЕРШЕНО')
        except Exception as e:
            print('НЕУДАЧА')
            print(e)
            return 1
        return 0

    def get_time(self, group_id):
        try:
            count = self.vk_api.groups.getMembers(count=0, offset=0, v='5.103', group_id=group_id)[
                'count']
        except Exception as e:
            return 'err_access_denied'
        hour = int(count / 441 // 3600)
        mins = round((count / 441 - hour * 3600) / 60)
        return hour, mins, count
