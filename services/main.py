"""
Flask server used for the registration page for **COMEX** app
Context:
    - templates-based input form validated fields and checked if all were present
      (base_form.html + static/js/comex_reg_form_controllers.js)

    - Doors already validated and recorded the (email, password) combination

    - labels of SOURCE_FIELDS are identical to the name of their target COLS
        - fields will land into the 3 main db tables:
            - *scholars*
            - *affiliations*
            - *keywords* (and *sch_kw* mapping table)
        - a few fields give no columns, for ex: "other_org_type"

    - webapp is exposed as "server_comex_registration.app" for the outside
        - can be served in dev by python3 server_comex_registration.py
        - better to serve it via gunicorn (cf run.sh)
"""
__author__    = "CNRS"
__copyright__ = "Copyright 2016 ISCPIF-CNRS"
__version__   = "1.5"
__email__     = "romain.loth@iscpif.fr"
__status__    = "Dev"


# ============== imports ==============
from re           import sub, match
from os           import path, remove
from json         import dumps
from datetime     import timedelta
from urllib.parse import unquote
from flask        import Flask, render_template, request, \
                         redirect, url_for, session, Response
from flask_login  import fresh_login_required, login_required, \
                         current_user, login_user, logout_user

if __package__ == 'services':
    # when we're run via import
    print("*** comex services ***")
    from services.tools    import mlog
    from services          import tools, dbcrud, dbdatapi
    from services.user     import User, login_manager, \
                                  doors_login, doors_register
    from services.text.utils import sanitize
else:
    # when this script is run directly
    print("*** comex services (dev server mode) ***")
    from tools          import mlog
    import tools, dbcrud, dbdatapi
    from user           import User, login_manager, \
                               doors_login, doors_register
    from text.utils      import sanitize

# ============= app creation ============
config = tools.REALCONFIG

app = Flask("services",
             static_folder=path.join(config['HOME'],"static"),
             template_folder=path.join(config['HOME'],"templates"))

app.config['DEBUG'] = (config['LOG_LEVEL'] in ["DEBUG","DEBUGSQL"])
app.config['SECRET_KEY'] = 'TODO fill secret key for sessions for login'

# for SSL
app.config['PREFERRED_URL_SCHEME'] = 'https'

# for flask_login
cookie_timer = timedelta(hours=2)
app.config['PERMANENT_SESSION_LIFETIME'] = cookie_timer
app.config['REMEMBER_COOKIE_DURATION'] = cookie_timer
app.config['REMEMBER_COOKIE_NAME'] = 'communityexplorer.org cookie'

# -------------------------- 8<----------------------
from flask_cors import CORS, cross_origin
cors = CORS(app, resources={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'
# -------------------------- 8<----------------------

login_manager.login_view = "login"
login_manager.session_protection = "strong"
login_manager.init_app(app)

########### PARAMS ###########

# all inputs as they are declared in form, as a couple
SOURCE_FIELDS = [
#             NAME,              SANITIZE?    sanitizing specificity
         ("luid",                  False,        None),
         ("doors_uid",             False,        None),
         ("email",                  True,        None),
         ("country",                True,        None),
         ("first_name",             True,        None),
         ("middle_name",            True,        None),
         ("last_name",              True,        None),
         ("initials",               True,        None),
         # => for *scholars* table

         ("position",               True,        None),
         ("hon_title",              True,        None),
         ("interests_text",         True,        None),
         ("gender",                False,        None),   # M|F
         ("job_looking",            True,       "sbool"),
         ("job_looking_date",       True,       "sdate"),
         ("home_url",               True,       "surl"),  # scholar's homepage
         ("pic_url",                True,       "surl"),
         ("pic_file",              False,        None),   # saved separately
         # => for *scholars* table (optional)

         ("lab_label",              True,       "sorg"),  # ~ /name (acro)?/
         ("lab_locname",            True,        None),   #  'Paris, France'
         ("inst_label",             True,       "sorg"),  # ~ /name (acro)?/
         ("inst_type",             False,        None),   # predefined values
         (  "other_inst_type",      True,        None),   # +=> org_type
         # => for *orgs* table via parse_affiliation_records

         ("keywords",               True,        None),
         # => for *keywords* table (after split str)

         ("hashtags",               True,        None)
         # => for *hashtags* table (after split str)
      ]

# NB password values have already been sent by ajax to Doors

# mandatory minimum of keywords
MIN_KW = 5

# ============= context =============
@app.context_processor
def inject_doors_params():
    """
    Keys will be available in *all* templates

       -> 'doors_connect'
          (base_layout-rendered templates need it for login popup)
    """
    if 'DOORS_PORT' not in config or config['DOORS_PORT'] in ['80', '443']:
        context_dict = dict(
            doors_connect= config['DOORS_HOST']
        )
    else:
        context_dict = dict(
            doors_connect= config['DOORS_HOST']+':'+config['DOORS_PORT']
        )

    return context_dict

@login_manager.unauthorized_handler
def unauthorized():
    """
    Generic handler for all unauthorized
    (pages requires login)

    NB: Redirecting here is done by @login_required decorators
    """
    return render_template(
        "message.html",
        message = """
            Please <strong><a href="%(login)s">login here</a></strong>.
            <br/><br/>
            The page <span class='code'>%(tgt)s</span> is only available after login.
            """ % {'tgt': request.path,
                   'login': url_for('login', next=request.path, _external=True)}
    )


def reroute(function_name_str):
    return redirect(url_for(function_name_str, _external=True))


# ============= views =============

# -----------------------------------------------------------------------
# /!\ Routes are not prefixed by nginx in prod so we do it ourselves /!\
# -----------------------------------------------------------------------
@app.route("/")
def rootindex():
    """
    Root of the comex2 app (new index)
    Demo CSS with alternative index (top like old index, then underneath some layout à la notebook)

    also useful to be able to url_for('rootindex') when redirecting to php
    """
    return render_template(
                            "rootindex.html"
                          )

# /services/
@app.route(config['PREFIX']+'/')
def services():
    return reroute('login')

# /services/api/aggs
@app.route(config['PREFIX'] + config['API_ROUTE'] + '/aggs')
def aggs_api():
    """
    API to read DB aggregation data (ex: for autocompletes)

    REST params
        like:str    an optional filter for select
        hapax:int   an optional min count threshold
    """
    if 'field' in request.args:
        search_filter = None
        hap_thresh = None
        if 'like' in request.args:
            try:
                search_filter = str(request.args['like'])
            except:
                pass
        if 'hapax' in request.args:
            try:
                hap_thresh = int(request.args['hapax'])
            except:
                pass
        if hap_thresh is None:
            hap_thresh = int(config['HAPAX_THRESHOLD'])

        # field name itself is tested by db module
        result = dbdatapi.get_field_aggs(
            request.args['field'],
            search_filter_str=search_filter,
            hapax_threshold=hap_thresh
            )

        return Response(
            response=dumps(result),
            status=200,
            mimetype="application/json")
    else:
        raise TypeError("aggs API query is missing 'field' argument")

# /services/api/graph
@app.route(config['PREFIX'] + config['API_ROUTE'] + '/graph')
def graph_api():
    """
    API to provide json extracts of the DB to tinaweb
    (originally @ moma/legacy_php_comex/tree/master/comex_install)
    (original author S. Castillo)
    """
    if 'qtype' in request.args:
        graphdb = dbdatapi.BipartiteExtractor(config['SQL_HOST'])

        # request.query_string
        #                => b'qtype=filters&tags[]=%23iscpif'
        # tools.restparse(request.query_string.decode())
        #                => {'qtype': 'filters', 'tags': ['#iscpif']}

        scholars = graphdb.getScholarsList(
                    request.args['qtype'],
                    tools.restparse(
                      request.query_string.decode()
                    )
                  )
        if scholars and len(scholars):
            # Data Extraction
            # (getting details for selected scholars into graph object)
            # when filtering, TODO do it along with previous step getScholarsList
            # (less modular but a lot faster)
            graphdb.extract(scholars)

        return(
            Response(
                response=dumps(graphdb.buildJSON(graphdb.Graph)),
                status=200,
                mimetype="application/json")
        )

    else:
        raise TypeError("graph API query is missing qtype (should be 'filters' or 'uid')")



# /services/api/user
@app.route(config['PREFIX'] + config['API_ROUTE'] + '/user')
def user_api():
    """
    API to provide json infos about user DB

    implemented "op" <=> verbs:
        exists  => bool
    """
    if 'op' in request.args:
        if request.args['op'] == "exists":
            if 'email' in request.args:
                email = sanitize(request.args['email'])
                return(
                    Response(
                        response=dumps({'exists':dbcrud.email_exists(email)}),
                        status=200,
                        mimetype="application/json")
                )

    else:
        raise TypeError("user API query is missing the operation to perform (eg op=exists)")


# /services/user/
@app.route(config['PREFIX'] + config['USR_ROUTE']+'/', methods=['GET'])
def user():
    return reroute('login')


# /services/user/login/
@app.route(config['PREFIX'] + config['USR_ROUTE'] + '/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template(
            "login.html"
        )
    elif request.method == 'POST':
        mlog("DEBUG", "LOGIN: form received from "+request.path+", with keys:", [k for k in request.values])

        # we used this custom header to mark ajax calls => called_as_api True
        x_req_with = request.headers.get('X-Requested-With', type=str)
        called_as_api = (x_req_with in ['XMLHttpRequest', 'MyFetchRequest'])

        # testing the captcha answer
        captcha_userinput = request.form['my-captcha']
        captcha_userhash = tools.re_hash(captcha_userinput)
        captcha_verifhash = int(request.form['my-captchaHash'])

        # dbg
        # mlog("DEBUG", "login captcha verif", str(captcha_verifhash))
        # mlog("DEBUG", "login captcha user", str(captcha_userhash))

        if captcha_userhash != captcha_verifhash:
            mlog("WARNING", "pb captcha rejected")
            return render_template(
                "message.html",
                message = """
                    We're sorry the "captcha" information you entered was wrong!
                    <br/>
                    <strong><a href="%s">Retry login here</a></strong>.
                    """ % url_for('login', _external=True)
                )
        else:
            # OK captcha accepted
            email = request.form['email']
            pwd = request.form['password']

            # we do our doors request here server-side to avoid MiM attack on result
            try:
                doors_uid = doors_login(email, pwd, config)
            except Exception as err:
                mlog("ERROR", "LOGIN: error in doors_login request")
                raise (err)

            mlog("DEBUG", "user.doors_login() returned doors_uid '%s'" % doors_uid)

            if doors_uid is None:
                # break: can't doors_login
                nologin_message = """<b>The login exists but it was invalid!</b><br/>Perhaps the password was wrong ?<br/>Or perhaps you never checked your mailbox and clicked on the validation link ?"""
                if called_as_api:
                    # menubar login will prevent redirect
                    return(nologin_message, 404)
                else:
                    return render_template(
                        "message.html",
                        message = nologin_message
                    )

            luid = dbcrud.doors_uid_to_luid(doors_uid)

            if luid:
                # normal user
                user = User(luid)
            else:
                mlog("DEBUG", "LOGIN: encountered new doors id (%s), switching to empty user profile" % doors_uid)
                # user exists in doors but has no comex profile nor luid yet
                dbcrud.save_doors_temp_user(doors_uid, email)  # preserve the email
                user = User(None, doors_uid=doors_uid)     # get a user.empty

            # =========================
            login_ok = login_user(user)
            # =========================

            mlog('INFO',
                 'login of %s (%s) was %s' % (str(luid),
                                              doors_uid,
                                              str(login_ok))
            )

            # TODO check cookie
            # login_ok = login_user(User(luid), remember=True)
            #                                   -------------
            #                            creates REMEMBER_COOKIE_NAME
            #                        which is itself bound to session cookie

            if not login_ok:
                # break: failed to login_user()
                notok_message = "LOGIN There was an unknown problem with the login."
                if called_as_api:
                    # menubar login will prevent redirect
                    return(nologin_message, 404)
                else:
                    return render_template(
                        "message.html",
                        message = notok_message
                    )

            # ========
            # OK cases
            # ========
            if called_as_api:
                # menubar login will do the redirect
                return('', 204)

            elif user.empty:
                mlog('DEBUG',"empty user redirected to profile")
                # we go straight to empty profile for the person to create infos
                return reroute('profile')

            # normal call, normal user
            else:
                mlog('DEBUG', "normal user login redirect")
                next_url = request.args.get('next', None)

                if not next_url:
                    return reroute('profile')
                else:
                    next_url = unquote(next_url)
                    mlog("DEBUG", "login with next_url:", next_url)
                    safe_flag = tools.is_safe_url(next_url, request.host_url)
                    # normal next_url
                    if safe_flag:
                        # if relative
                        if next_url[0] == '/':
                            next_url = url_for('rootindex', _external=True) + next_url[1:]
                            mlog("DEBUG", "LOGIN: reabsoluted next_url:", next_url)

                        return(redirect(next_url))
                    else:
                        # server name is different than ours
                        # in next_url so we won't go there
                        return reroute('rootindex')


# /services/user/logout/
@app.route(config['PREFIX'] + config['USR_ROUTE'] + '/logout/')
def logout():
    logout_user()
    mlog('INFO', 'logged out previous user')
    return reroute('rootindex')

# /services/user/profile/
@app.route(config['PREFIX'] + config['USR_ROUTE'] + '/profile/', methods=['GET', 'POST'])
@fresh_login_required
def profile():
    """
    Entrypoint for users to load/re-save personal data

    @login_required uses flask_login to relay User object current_user
    """
    if request.method == 'GET':
        # login provides us current_user
        if current_user.empty:
            mlog("INFO",  "PROFILE: empty current_user %s" % current_user.uid)
        else:
            mlog("INFO",  "PROFILE: current_user %s" % current_user.uid)
            mlog("DEBUG",  "PROFILE: current_user details: \n  - %s" % (
                                '\n  - '.join([current_user.info['email'],
                                            current_user.info['initials'],
                                           current_user.info['doors_uid'] if current_user.info['doors_uid'] else "(no doors_uid)" ,
                                        str(current_user.info['keywords']),
                                            current_user.info['country']]
                                          )
                              )
                )

        # debug session cookies
        # print("[k for k in session.keys()]",[k for k in session.keys()])
        mlog("DEBUG", "PROFILE view with flag session.new = ", session.new)

        return render_template(
            "profile.html"
            # NB we also got user info in {{current_user.info}}
            #                         and {{current_user.json_info}}
        )
    elif request.method == 'POST':
        mlog("DEBUG", "saving profile with request.form=", request.form)


        # ajax calls get a little html, normal calls get a full page
        x_req_with = request.headers.get('X-Requested-With', type=str)
        called_as_api = (x_req_with in ['XMLHttpRequest', 'MyFetchRequest'])
        answer_template = "bare_thank_you.html" if called_as_api else "thank_you.html"

        mlog("DEBUG", "profile update flag called_as_api=", called_as_api)

        # special action DELETE!!
        if 'delete_user' in request.form and request.form['delete_user'] == 'on':
            the_id_to_delete = current_user.uid
            mlog("INFO",
                 "executing DELETE scholar's data at the request of user %s" % str(the_id_to_delete))

            # remove saved image if any
            if current_user.info['pic_fname']:
                remove(path.join(*tools.IMAGE_SAVING_POINT, current_user.info['pic_fname']))
            logout_user()
            dbcrud.rm_scholar(the_id_to_delete)

            return reroute('rootindex')


        else:
            # input fields data ~> normalized {cols:values}
            our_records = read_record_from_request(request)

            # small gotcha: absence of the file input is the default in GUI
            #               (even when we keep the image)
            if 'pic_fname' not in our_records and 'pic_fname' in current_user.info and current_user.info['pic_fname']:
                our_records['pic_fname'] = current_user.info['pic_fname']
            # POSS:
            #      a dedicated button to indicate that the pic should be rm


            # special action CREATE for a new user already known to doors
            if current_user.empty:
                mlog("DEBUG",
                     "create profile from new doors user %s" % current_user.doors_uid)
                # remove the empty luid
                our_records.pop('luid')

                # add the doors_uid and doors_email to the form (same keynames!)
                our_records = { **our_records, **current_user.doors_info }

                try:
                    # *create* this user in our DB
                    luid = save_form(our_records, update_flag = False)

                except Exception as perr:
                    return render_template("thank_you.html",
                                form_accepted = False,
                                backend_error = True,
                                debug_message = tools.format_err(perr)
                            )

                # if all went well we can remove the temporary doors user data
                dbcrud.rm_doors_temp_user(current_user.doors_uid)
                logout_user()
                # .. and login the user in his new mode
                login_user(User(luid))

                return render_template(
                    answer_template,
                    debug_records = (our_records if app.config['DEBUG'] else {}),
                    form_accepted = True,
                    backend_error = False
                )

            # normal action UPDATE
            else:
                try:
                    luid = save_form(our_records,
                                     update_flag = True,
                                     previous_user_info = current_user.info)

                except Exception as perr:
                    return render_template(
                        answer_template,
                        form_accepted = False,
                        backend_error = True,
                        debug_message = tools.format_err(perr)
                    )

                return render_template(
                    answer_template,
                    debug_records = (our_records if app.config['DEBUG'] else {}),
                    form_accepted = True,
                    backend_error = False
                )



# /services/user/claim_profile/
@app.route(config['PREFIX'] + config['USR_ROUTE'] + '/claim_profile/', methods=['GET', 'POST'])
def claim_profile():
    """
    For returning users (access by token as GET arg)
    """
    if request.method == 'GET':
        return_token = None
        luid = None

        # identify who came back from the return token
        if 'token' in request.args:

            return_token = sanitize(request.args['token'])

            if (return_token
                    and type(return_token) == str
                    and len(return_token) == 36):
                luid = dbcrud.get_legacy_user(return_token)

            if luid is not None:
                try:
                    return_user = User(luid)
                except ValueError:
                    return_user = None

        # claim failure cases
        if return_token is None or luid is None or return_user is None:
            mlog('INFO', 'failed claim profile GET with return_token=%s, luid=%s' % (str(return_token),str(luid)))
            return render_template(
                "message.html",
                message = """
                    <p><b>This activation link has already been used !</b></p>

                    <p>If you just created a new password for an archived profile:
                    </p>
                    <ol>
                        <li>go and click the validation link in your <b>confirmation email</b></li>
                        <li>then come back here to <span class='link-like' onclick="cmxClt.elts.box.toggleBox('auth_modal')">login</span></li>
                    </ol>
                    <br/>
                    <p>
                    Otherwise you can also register a completely new account via <span class='code'><a href="%(register_url)s">%(register_url)s</a></span>
                    </p>
                    """ % { 'register_url': url_for('register') }
            )

        # claim success
        else:
            mlog('DEBUG', "successful claim_profile GET for luid =", luid)
            # we *don't* log him in but we do put his data as return_user
            # => this way we can use templating to show the data
            return render_template(
                "claim_profile.html",
                return_user = return_user
            )
    elif request.method == 'POST':

        email = request.form['email']
        pwd = request.form['password']
        luid = request.form['return_user_luid']

        return_user = User(luid)
        info = return_user.info
        name = info['last_name']+', '+info['first_name']
        if info['middle_name']:
            name += ' '+info['middle_name']

        # we do our doors request here server-side to avoid MiM attack on result
        try:
            doors_uid = doors_register(email, pwd, name, config)
        except Exception as err:
            mlog("ERROR", "error in doors_register remote request")
            raise (err)

        mlog("DEBUG", "doors_register returned doors_uid '%s'" % doors_uid)

        if doors_uid is None:
            return render_template(
                "thank_you.html",
                form_accepted = False,
                backend_error = True,
                debug_message = "No ID was returned from the portal at registration"
            )

        else:
            try:
                db_connection = dbcrud.connect_db(config)
                dbcrud.update_scholar_cols({
                                  'doors_uid':doors_uid,
                                  'record_status': 'active',
                                  'valid_date': None
                                 },
                                 db_connection,
                                 where_luid=return_user.uid)
                db_connection.close()
                # the user is not a legacy user anymore
                # POSS: do this on first login instead
                dbcrud.rm_legacy_user_rettoken(luid)

            except Exception as perr:
                return render_template(
                    "thank_you.html",
                    form_accepted = False,
                    backend_error = True,
                    debug_message = tools.format_err(perr)
                )

            mlog('DEBUG', "successful claim_profile for luid =", luid)

            return render_template(
                "message.html",
                message = """
                <p>Your new login credentials are saved. To complete your registration:</p>
                <ol>
                    <li>go check your mailbox and click the link in your <b>confirmation email</b></li>
                    <li>then come back here to <span class='link-like' onclick="cmxClt.elts.box.toggleBox('auth_modal')">login</span></li> to your old profile with your new credentials.
                </ol>
                """
            )


# /services/user/register/
@app.route(config['PREFIX'] + config['USR_ROUTE'] + '/register/', methods=['GET','POST'])
def register():

    # debug
    # mlog("DEBUG", "register route: ", config['PREFIX'] + config['USR_ROUTE'] + '/register')

    if request.method == 'GET':
        return render_template(
            "registration_super_short_form.html"
            )
    elif request.method == 'POST':
        # ex: request.form = ImmutableMultiDict([('initials', 'R.L.'), ('email', 'romain.loth@iscpif.fr'), ('last_name', 'Loth'), ('country', 'France'), ('first_name', 'Romain'), ('my-captchaHash', '-773776109'), ('my-captcha', 'TSZVIN')])
        # mlog("DEBUG", "GOT ANSWERS <<========<<", request.form)

        # 1 - testing the captcha answer
        captcha_userinput = request.form['my-captcha']
        captcha_userhash = tools.re_hash(captcha_userinput)
        captcha_verifhash = int(request.form['my-captchaHash'])

        # dbg
        # mlog("DEBUG", str(captcha_verifhash))


        if captcha_userhash != captcha_verifhash:
            mlog("INFO", "pb captcha rejected")
            form_accepted = False

        # normal case
        else:
            mlog("INFO", "ok form accepted")
            form_accepted = True
            clean_records = {}

            # 1) handles all the inputs from form
            #    (using SOURCE_FIELDS recreates USER_COLS)
            clean_records = read_record_from_request(request)

            try:
                # 2) saves the records to db
                luid = save_form(clean_records)

            except Exception as perr:
                return render_template(
                    "thank_you.html",
                    form_accepted = False,
                    backend_error = True,
                    debug_message = tools.format_err(perr)
                )

            # all went well: we can login the user
            login_user(User(luid))

        return render_template(
            "thank_you.html",
            debug_records = (clean_records if app.config['DEBUG'] else {}),
            form_accepted = form_accepted,
            backend_error = False,
            message = """
              You can now visit elements of the members section:
              <ul style="list-style-type: none; font-size:140%%;">
                  <li>
                      <span class="glyphicon glyphicon glyphicon-education"></span>&nbsp;&nbsp;
                      <a href="/services/user/profile"> Your Profile </a>
                  </li>
                  <li>
                      <span class="glyphicon glyphicon-eye-open"></span>&nbsp;&nbsp;
                      <a href='/explorerjs.html?sourcemode="api"&type="uid"&nodeidparam=%(luid)i'> Your Map </a>
                  </li>
                  <li>
                      <span class="glyphicon glyphicon glyphicon-stats"></span>&nbsp;&nbsp;
                      <a href='/print_scholar_directory.php?query=%(luid)i'> Your Neighbor Directory and Stats </a>
                  </li>
              </ul>
            """ % {'luid': luid })





# /services/jobad/
@app.route(config['PREFIX'] + '/jobad/', methods=['GET','POST'])
@fresh_login_required
def jobad():

    # debug
    # mlog("DEBUG", "register route: ", config['PREFIX'] + config['USR_ROUTE'] + '/register')

    if request.method == 'GET':
        return render_template("jobad_form.html")
    elif request.method == 'POST':
        mlog("DEBUG", "GOT JOB AD ANSWERS <<========<<", request.form)

        # ImmutableMultiDict([('recruiter_org_text', 'A wonderful company'), ('job_valid_date', '2017/8/30'), ('mission_text', 'a very important job'), ('email', 'romain.loth@truc.org'), ('luid', '4206'),  ('keywords', 'agent-based models,cellular automata')])

        return render_template(
            "message.html",
            message = """
                Your job ad was successfully recorded. You can now find it in your <a href="/services/user/myjobs"> job-board section </a>
                """
        )


# any static pages with topbar are set in /about prefix

# /about/privacy
@app.route('/about/privacy')
def show_privacy():
    return render_template("privacy.html")



########### SUBS ###########

def parse_affiliation_records(clean_records):
    """
    Transform GUI side input data into at most 2 orgs objects for DB

    In general:
        1) the front-end inputs are less free than the DB structure
            (DB could save an array of orgids but in the inputs they're only allowed max 2 atm : lab and inst)

        2) each org has its microstructure:
            - name, acronym, class, location (base properties)
            - inst_type (specific to institutions)
            - lab_code, url, contact <= not fillable in GUI yet

        3) between themselves 2 orgs can have org_org relationships
            TODO LATER (not a priority)

        4) we want at least one of lab_label or inst_label to be NOT NULL

    Choices:
        - values are already sanitized by read_record_from_request
        - We call label the concatenated name + acronym information,
          handling here the possibilities for the input via str analysis
          (just short name, just long name, both)

        - We return a map with 2 key/value submaps for lab and institutions
    """
    new_orgs = {'lab': None, 'inst': None}
    for org_class in new_orgs:
        # can't create org without some kind of label
        if (org_class+"_label" not in clean_records
           or not len(clean_records[org_class+"_label"])):
           pass
        else:
            # submap
            new_org_info = {}

            # 1) label analysis
            clean_input = clean_records[org_class+"_label"]

            # label split attempt
            test_two_groups = match(
                                r'([^\(]+)(?: *\(([^\)]{1,30})\))?',
                                clean_input
                              )
            if (test_two_groups
                and test_two_groups.groups()[0]
                and test_two_groups.groups()[1]):
                # ex 'Centre National de la Recherche Scientifique (CNRS)'
                #         vvvvvvvvvvvvvvvv                          vvvv
                #               name                                acro
                name_candidate = test_two_groups.groups()[0]
                acro_candidate = test_two_groups.groups()[1]

                new_org_info['name'] = name_candidate.strip()
                new_org_info['acro'] = acro_candidate.strip()

                mlog("DEBUG", "parse_affiliation_records found name='%s' and acro='%s'" % (new_org_info['name'], new_org_info['acro']))
            else:
                len_input = len(clean_input)
                test_uppercase = sub(r'[^0-9A-ZÉ\.]', '', clean_input)
                uppercase_rate = len(test_uppercase) / len_input

                # special case short and mostly uppercase => just acro
                # POSS tune len and uppercase_rate
                if (len_input <= 8 or
                    (len_input <= 20 and uppercase_rate > .7)):
                    # ex 'CNRS'
                    #     vvvv
                    #     acro
                    new_org_info['acro'] = clean_input

                # normal fallback case => just name
                else:
                    # ex 'Centre National de la Recherche Scientifique' None
                    #         vvvvvvvvvvvvvvvv                          vvvv
                    #               name                                acro
                    new_org_info['name'] = clean_input

            # 2) enrich with any other optional org info
            for detail_col in ['inst_type', 'lab_code', 'locname',
                               'url', 'contact_email', 'contact_name']:

                if detail_col not in ['inst_type', 'lab_code']:
                    # this is a convention in our templates
                    org_detail = org_class + '_' + detail_col
                else:
                    org_detail = detail_col

                if org_detail in clean_records:
                    val = clean_records[org_detail]
                    if len(val):
                        new_org_info[detail_col] = val

            # 3) keep
            new_orgs[org_class] = new_org_info

    return new_orgs




def save_form(clean_records, update_flag=False, previous_user_info=None):
    """
    wrapper function for save profile/register (all DB-related form actions)

    @args :
        *clean_records*   a dict of sanitized form fields

        optional (together):
            update_flag            we update in DB instead of INSERT
            previous_user_info     iff update_flag, like current_user.info
    """

    # A) a new DB connection
    reg_db = dbcrud.connect_db(config)

    # B1) re-group the org fields into at most 2 org 'objects'
    declared_orgs = parse_affiliation_records(clean_records)

    mlog('DEBUG', 'save_form: declared values for org =', declared_orgs)

    # B2) for each optional declared org,
    #      read/fill the orgs table to get associated id(s) in DB
    orgids = []
    for oclass in ['lab', 'inst']:

        if (declared_orgs[oclass]):
            orgids.append(
                dbcrud.get_or_create_org(declared_orgs[oclass], oclass, reg_db)
            )

    mlog('DEBUG', 'save_form: found ids for orgs =', orgids)

    # B3) save the org <=> org mappings TODO LATER (not a priority)
    # dbcrud.record_org_org_link(src_orgid, tgt_orgid, reg_db)

    # C) create/update record into the primary user table
    # ----------------------------------------------------
        # TODO class User method !!
    luid = None
    if update_flag:
        luid = int(previous_user_info['luid'])
        sent_luid = int(clean_records['luid'])
        if luid != sent_luid:
            mlog("WARNING", "User %i attempted to modify the data of another user (%i)!... Aborting update" % (luid, sent_luid))
            return None
        else:
            dbcrud.save_full_scholar(clean_records, reg_db, update_user=previous_user_info)

            # remove previous image from filesystem if changed
            if (previous_user_info['pic_fname']
             and ('pic_fname' in clean_records
                  and
                  previous_user_info['pic_fname'] != clean_records['pic_fname'])):

                remove(path.join(*tools.IMAGE_SAVING_POINT, previous_user_info['pic_fname']))


    else:
        luid = int(dbcrud.save_full_scholar(clean_records, reg_db))


    # D) read/fill each keyword and save the (uid <=> kwid) pairings
    #    read/fill each hashtag and save the (uid <=> htid) pairings
    for intable in ['keywords', 'hashtags']:
        tok_field = intable
        if tok_field in clean_records:
            tok_table = tok_field
            map_table = "sch_" + ('kw' if intable == 'keywords' else 'ht')

            tokids = dbcrud.get_or_create_tokitems(
                        clean_records[tok_field],
                        reg_db,
                        tok_table
                     )

                # TODO class User method !!
                # POSS selective delete ?
            if update_flag:
                dbcrud.delete_pairs_sch_tok(luid, reg_db, map_table)

            dbcrud.save_pairs_sch_tok(
                [(luid, tokid) for tokid in tokids],
                reg_db,
                map_table
            )

    # E) overwrite the (uid <=> orgid) mapping(s)
    dbcrud.rm_sch_org_links(luid, reg_db)
    mlog("DEBUG", "removing all orgs for", luid)
    for orgid in orgids:
        mlog("DEBUG", "recording orgs:", luid, orgid)
        dbcrud.record_sch_org_link(luid, orgid, reg_db)

    # F) end connection
    reg_db.close()

    return luid


def read_record_from_request(request):
    """
    Runs all request-related form actions

    Arg:
        a flask request
        werkzeug.pocoo.org/docs/0.11/wrappers/#werkzeug.wrappers.Request

    Process:
        input SOURCE_FIELDS data ~> normalized {COLS:values}

        Custom made for comex registration forms
            - sanitization + string normalization as needed
            - pic_file field ~~> save to fs + pic_fname col
    """
    # init var
    clean_records = {}

    # sources: request.form and request.files

    # we should have all the mandatory fields (checked in client-side js)
    # POSS recheck b/c if post comes from elsewhere
    for field_info in SOURCE_FIELDS:
        field = field_info[0]
        do_sanitize = field_info[1]
        spec_type = field_info[2]
        if field in request.form:
            if do_sanitize:
                val = sanitize(request.form[field], spec_type)
                if val != '':
                    clean_records[field] = val
                else:
                    # mysql will want None instead of ''
                    val = None
            # this one is done separately at the end
            elif field == "pic_file":
                continue
            # any other fields that don't need sanitization (ex: menu options)
            else:
                clean_records[field] = request.form[field]

    # special treatment for "other" subquestions
    if 'inst_type' in clean_records:
        if clean_records['inst_type'] == 'other' and 'other_inst_type' in clean_records:
            clean_records['inst_type'] = clean_records['other_inst_type']

    # splits for kw_array and ht_array
    for tok_field in ['keywords', 'hashtags']:
        if tok_field in clean_records:
            mlog("DEBUG",
                 "in clean_records, found a field to tokenize: %s" % tok_field)
            temp_array = []
            for tok in clean_records[tok_field].split(','):
                tok = sanitize(tok)
                if tok != '':
                    temp_array.append(tok)
            # replace str by array
            clean_records[tok_field] = temp_array

            if tok_field == 'keywords' and len(temp_array) < MIN_KW:
                mlog('WARNING', 'only %i keywords instead of %i' % (len(temp_array), MIN_KW))

    # special treatment for pic_file
    if hasattr(request, "files") and 'pic_file' in request.files and request.files['pic_file']:
        new_fname = tools.pic_blob_to_filename(request.files['pic_file'])
        clean_records['pic_fname'] = new_fname
        mlog("DEBUG", "new pic with fname", new_fname)

    return clean_records


########### MAIN ###########
# this can only be used for debug
# (in general use comex-run.sh to run the app)
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8989)
