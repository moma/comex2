"""
Simple user class to provide login

cf. https://flask-login.readthedocs.io/en/latest/#how-it-works
    https://flask-login.readthedocs.io/en/latest/_modules/flask_login/mixins.html#UserMixin
"""
__author__    = "CNRS"
__copyright__ = "Copyright 2016 ISCPIF-CNRS"
__email__     = "romain.loth@iscpif.fr"

from json        import loads, dumps
from datetime    import date
from flask_login import LoginManager
from re          import match

if __package__ == 'services':
    from services.dbcrud import connect_db, get_full_scholar, \
                                            get_doors_temp_user
    from services.tools import mlog, REALCONFIG, prejsonize
else:
    from dbcrud         import connect_db, get_full_scholar, \
                                           get_doors_temp_user
    from tools          import mlog, REALCONFIG, prejsonize

# will be exported to main for initialization with app
login_manager = LoginManager()

@login_manager.user_loader
def load_user(mixedid):
    """
    Used by flask-login to bring back user object from a special id stored in session... this special id is defined in User.get_id()
    """
    u = None
    mlog("DEBUG", "load_user: %s" % mixedid)
    if mixedid is not None:

        testluid = match('normal/luid:(\d+)$', mixedid)
        testduid = match('empty/doors:([a-f\d-]+)$', mixedid)

        if testluid:
            luid = int(testluid.groups()[0])
            u = User(luid)

        elif testduid:
            doors_uid = testduid.groups()[0]
            u = User(None, doors_uid=doors_uid)
            mlog("DEBUG", "load_user: empty user recreated from doors_uid")

    return u


class User(object):

    def __init__(self, luid, doors_uid=None):
        """
        Normal user syntax:         User(luid)
        (user already in db)
         => has luid

        Empty user syntax:          User(None, doors_uid=foobar)
        (user exists only in
         doors but not in db)
         => no luid, but has doors_uid

         NB load_user() wants a *single id for both*,
             which is provided by self.get_id()
        """
        mlog('DEBUG',
             'new User(luid=%s, doors_uid="%s")' %(str(luid), str(doors_uid)))

        # normal user has a nice info dict
        if luid is not None:
            luid = int(luid)
            scholar = get_full_scholar(luid)
            if scholar == None:
                raise ValueError('this uid %i references a scholar that is not really in the DB... Did you change the database recently and have still some old cookies with IDs?' % luid)
            else:
                self.uid = luid
                self.info = scholar
                self.info['affiliation'] = self.get_compact_affiliation()
                self.json_info = dumps(prejsonize(self.info))
                self.doors_uid = self.info['doors_uid']
                self.empty = False

                if 'pic_fname' in self.info and self.info['pic_fname']:
                    self.pic_src = '/data/shared_user_img/'+self.info['pic_fname']
                elif 'pic_url' in self.info and self.info['pic_url']:
                    self.pic_src = self.info['pic_url']
                else:
                    self.pic_src = None

        # user exists in doors but has nothing in scholars DB yet
        elif doors_uid is not None:
            self.uid = None
            self.info = {}
            self.json_info = "{}"
            self.doors_uid = doors_uid
            self.doors_info = get_doors_temp_user(doors_uid)
            self.empty = True
        else:
            raise TypeError("User can either be initialized with comex_db luid or with doors_uid")

    def get_id(self):
        """
        Provides a special ID used only by login_manager

        NB double init cases forced us to introduce
           here a *single id to load both cases*,
           for use later in user_loader

        (it's needed because when reloading user, login_manager
         will do something like this: u = user_loader(old_u.get_id())
                                          ---------------------------
        """
        mixedid = None
        if self.uid:
            mixedid = "normal/luid:"+str(self.uid)
        elif self.doors_uid:
            mixedid = "empty/doors:"+self.doors_uid
        else:
            raise ValueError("No IDs for this user flask-login won't refind it")
        return mixedid

    def get_compact_affiliation(self):
        """
        Provides a single affiliation string (possibly empty for legacy users)

        Context: comex structure allows multiple affiliations of 2 different types (labs and institutions), but external apps like doors need only one string to resume it all.

        NB: this implementation only uses the first lab and first inst
            all users should have always one lab entry, except for new doors users
            however legacy users have their lab entry set to name:_NULL
        """
        compact_lab = ''
        compact_inst = ''

        if "labs" in self.info and len(self.info['labs']):
            lab = self.info['labs'][0]
            # we skip legacy _NULL values
            if lab['name'] != '_NULL':
                # label is name and acronym
                compact_lab += lab['label']

                # these optional slots have normal None values when empty
                if lab['lab_code']:
                    compact_lab += " [%s]" % lab['lab_code']
                if lab['locname']:
                    compact_lab += " - %s" % lab['locname']

        if "insts" in self.info and len(self.info['insts']):
            inst = self.info['insts'][0]

            # label is always there
            compact_inst = inst['label']

            if inst['locname']:
                compact_lab += " - %s" % inst['locname']

        aff_str = ''
        if len(compact_lab) and not len(compact_inst):
            aff_str = compact_lab
        elif not len(compact_lab) and len(compact_inst):
            aff_str = compact_inst
        elif len(compact_lab) and len(compact_inst):
            aff_str = "%s / %s" % (compact_lab, compact_inst)

        return aff_str


    @property
    def is_active(self):
        """
        :boolean flag:

        uses scholars.status
        and self.empty <=> is also active a user who exists
                           in doors db but not in comex_db

              STATUS STR           RESULT
               "active"          flag active
                "test"           flag active if DEBUG
               "legacy"          flag active if validity_date >= NOW()
        """
        if self.empty:
            # the user has a doors uid so he's entitled to a login
            # and will be directed to the profile page to create his infos
            return True
        else:
            # ... or has a record_status in comex_db
            sirstatus = self.info['record_status']
            sivdate = self.info['valid_date']

            # boolean result
            return (sirstatus == "active"
                        or (
                            sirstatus == "legacy"
                            and
                            sivdate <= date.today()
                        )
                        or (
                            sirstatus == "test"
                            and
                            REALCONFIG['LOG_LEVEL'] == "DEBUG"
                        )
                    )

    @property
    def is_anonymous(self):
        """
        POSS in the future we can use it for demo users
        """
        return False

    @property
    def is_authenticated(self):
        """
        We assume user object only exists if user was authenticated or has cookie
        POSS: re-test each time with doors
        """
        return True

    def __eq__(self, other):
        return self.uid == other.uid



# ----------- remote user -----------------------

from requests    import post


def doors_login(email, password, config=REALCONFIG):
    """
    Remote query to Doors API to login a user

    Doors responses look like this:
        {'status': 'login ok',
          'userInfo': {
            'hashAlgorithm': 'PBKDF2',
            'password': '8df55dde7b1a2cc013afe5ed2d20ae22',
            'id': {'id': '9e30ce89-72a1-46cf-96ca-cf2713b7fe9d'},
            'name': 'Corser, Peter',
            'hashParameters': {
              'iterations' : 1000,
              'keyLenght' : 128
            }
          }
        }
    NB: returned doors_uid will be None if user not found
    """
    uid = None
    sentdata = {'login':email.lower(), 'password':password}
    ssl_verify = True
    http_scheme = "https:"

    if config['DOORS_NOSSL']:
        # /!\ unsafe param: only useful for local tests /!\
        http_scheme = 'http:'
        ssl_verify = False
        mlog("WARNING", "user.doors_login: SSL and HTTPS turned off (after tests remove DOORS_NOSSL from config file)")

    if config['DOORS_PORT'] in ['80', '443']:
        # implicit port
        doors_base_url = http_scheme + '//'+config['DOORS_HOST']
    else:
        doors_base_url = http_scheme + '//'+config['DOORS_HOST']+':'+config['DOORS_PORT']

    doors_response = post(doors_base_url+'/api/user', data=sentdata, verify=ssl_verify)

    mlog("INFO", "/api/user doors_response",doors_response)
    if doors_response.ok:
        login_info = loads(doors_response.content.decode())

        if login_info['status'] == "LoginOK":
            uid = login_info['userID']
            # ID is a string of the form: "UserID(12849e74-b039-481f-b8eb-1e52562fbda6)"
            capture = match(r'UserID\(([0-9a-f-]+)\)', uid)
            if capture:
                uid = capture.groups()[0]

    elif match(r'User .* not found$', doors_response.json()):
        uid = None
        mlog('INFO', "doors_login says user '%s' was not found" % email)
    else:
        raise Exception('Doors request failed')

    return uid

def doors_register(email, password, last_name, first_name="", affiliation="", config=REALCONFIG):
    """
    Remote query to Doors API to register a user
    """
    if not len(email) or not len(password) or not len(last_name):
        mlog("ERROR", "can't proceed with doors registration (invalid args)")
        return None

    uid = None
    sentdata = {
        'login':email.lower(), 'password':password,
        'firstName': first_name, 'lastName':last_name,
        'affiliation': affiliation
        }

    http_scheme = "https:"

    if config['DOORS_NOSSL']:
        # /!\ unsafe param: only useful for local tests /!\
        http_scheme = 'http:'
        ssl_verify = False
        mlog("WARNING", "user.doors_register: SSL and HTTPS turned off (after tests remove DOORS_NOSSL from config file)")

    if config['DOORS_PORT'] in ['80', '443']:
        # implicit port
        doors_base_url = http_scheme + '//'+config['DOORS_HOST']
    else:
        doors_base_url = http_scheme + '//'+config['DOORS_HOST']+':'+config['DOORS_PORT']

    doors_response = post(doors_base_url+'/api/register', data=sentdata, verify=ssl_verify)

    mlog("INFO", "/api/register doors_response",doors_response)
    if doors_response.ok:
        # eg doors_response.content = b'{"status":"registration email sent",
        #                                "email":"john@locke.com"}''
        answer = loads(doors_response.content.decode())
        # mlog("INFO", "/api/register answer",answer)
        return answer['userID']
    else:
        return None
