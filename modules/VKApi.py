import vk


class VKParser:
    def __init__(self, token):
        try:
            session = vk.Session(token)
            self.vk_api = vk.API(session)
        except Exception as e:
            print(e)
            exit(-1)

    def get_group(self, group_id):
        fields = 'id, name, screen_name, is_closed, deactivated, city, country'
        try:
            response = self.vk_api.groups.getById(group_id=group_id, fields=fields, v='5.103')[0]
        except Exception as e:
            print(e)
        else:
            converted_response = dict()
            for field in fields.split(', '):
                if field not in response.keys():
                    converted_response[field.title()] = None
                else:
                    if field == 'city' or field == 'country':
                        converted_response[field.title()] = response[field]['title']
                    elif field == 'is_closed':
                        converted_response[field.title()] = True if response[field] else False  
                    else:
                        converted_response[field.title()] = response[field]
            return converted_response
        return None