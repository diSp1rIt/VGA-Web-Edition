#############################
# code 0 - all right        #
# code 1 - need a sign in   #
# code 2 - need a sign up   #
#############################


class Logging:
    def __init__(self):
        pass

    def check_web_session(self, web_session):
        if 'authorized' not in web_session:
            web_session['authorized'] = 0
            return 1
        else:
            if web_session.get('authorized') == 1:
                if web_session.get('email') is None:
                    return 2
                return 0
            else:
                return 1

