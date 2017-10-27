"""
utility functions
"""
__author__    = "CNRS"
__copyright__ = "Copyright 2016 ISCPIF-CNRS"
__email__     = "romain.loth@iscpif.fr"

# for reading config
from configparser import ConfigParser
from os           import environ, path
from sys          import stdout
from urllib.parse import unquote
from ctypes       import c_int32
from traceback    import format_tb
from datetime     import date, datetime

# ========================== FILL REALCONFIG ===================================

# the main config dict (filled and exposed by this module only)
# --------------------
REALCONFIG = {}


# the expected and default values
CONFIGMENU = [
            # logging
            {"sec": 'main',   "var":'LOG_LEVEL',  "def": "INFO"             },
            {"sec": 'main',   "var":'LOG_FILE',   "def": 'logs/services.log'},
            {"sec": 'main',   "var":'LOG_TEE',    "def": True               },

            # subserver
            {"sec": 'main',    "var":'COMEX_HOST',   "def": '0.0.0.0'       },
            {"sec": 'main',    "var":'COMEX_PORT',   "def": '9090'          },
            {"sec": 'main',    "var":'PASSPHRASE',   "def": 's3cr3t k3y'    },

            {"sec": 'routes',  "var":'PREFIX',       "def": '/services'     },
            {"sec": 'routes',  "var":'USR_ROUTE',    "def": '/user'         },
            {"sec": 'routes',  "var":'API_ROUTE',    "def": '/api'          },

            # requirements
            {"sec": 'backends',   "var":'SQL_HOST',     "def": '172.17.0.2' },
            {"sec": 'backends',   "var":'SQL_PORT',     "def": '3306'       },
            {"sec": 'backends',   "var":'DOORS_HOST',   "def": '0.0.0.0'    },
            {"sec": 'backends',   "var":'DOORS_PORT',   "def": '443'        },
            {"sec": 'backends',   "var":'DOORS_NOSSL',  "def": False        },

            # data processing
            {"sec": 'content',    "var":'HAPAX_THRESHOLD',   "def": '1 '    }
          ]


IMAGE_SAVING_POINT = ['data', 'shared_user_img']
BLOB_SAVING_POINT = ['data', 'shared_user_files']

def home_path():
    """
    returns ./../.. in any OS
    """
    return path.dirname(path.dirname(path.realpath(__file__)))


def read_config():
    """
    reads all global config vars trying in order:
        1) env variables of the same name
        2) the config file $HOME/config/parametres_comex.ini
        3) hard-coded default values

    Effect: fills the var REALCONFIG
              (no return value)
    """
    our_home = home_path()

    print('_^_'+our_home)

    ini = ConfigParser()
    inipath = path.join(our_home, "config", "parametres_comex.ini")
    ini.read(inipath)

    # check sections
    if len(ini.keys()) <= 1:
        print("WARNING: the config file at '%s' seems empty, I will use env or default values" % inipath)

    for k in ini.keys():
        if k not in ['DEFAULT', 'backends', 'main', 'routes', 'content']:
            print("WARNING: ignoring section  '%s'" % k)

    # read ini file and use 2 fallbacks: env or default
    for citem in CONFIGMENU:
        section = citem['sec']
        varname = citem['var']
        default = citem['def']
        is_bool = (type(default) == bool)

        if varname in environ:
            if is_bool:
                REALCONFIG[varname] = (environ[varname] == 'true')
            else:
                REALCONFIG[varname] = environ[varname]

            # for dbg
            # print("ini debug: '%10s' ok from env" % varname)

        elif section in ini and varname in ini[section]:
            if is_bool:
                REALCONFIG[varname] = ini.getboolean(section, varname)
            else:
                REALCONFIG[varname] = ini.get(section, varname)

            # for dbg
            # print("ini debug: '%10s' ok from file" % varname)

        else:
            REALCONFIG[varname] = default

            # for dbg
            # print("ini debug: '%10s' ok from default" % varname)

    # also add our project home since we have it and we'll need it
    REALCONFIG['HOME'] = our_home


# ----------------------------------------
# let's do it now
read_config()

# ok! (REALCONFIG is now ready to export)
# ---------------------------------------



# ============================ other tools =====================================

from urllib.parse import urlparse, urljoin, unquote
def is_safe_url(target, host_url):
    """
    Checks if url is ok for redirects
    cf. http://flask.pocoo.org/snippets/62/
    """
    ref_url = urlparse(host_url)
    test_url = urlparse(urljoin(host_url, target))
    return (test_url.scheme in ('http', 'https')
            and ref_url.netloc == test_url.netloc)


def re_hash(userinput, salt="verylonverylongverylonverylongverylonverylong"):
    """
    Build the captcha's verification hash server side
    (my rewrite of keith-wood.name/realPerson.html python's version)

    NB the number of iterations is prop to salt length

    << 5 pads binary repr by 5 zeros on the right (including possible change of sign)
    NB in all languages except python it truncates on the left
        => here we need to emulate the same mechanism
        => using c_int32() works well
    """
    hashk = 5381

    value = userinput.upper() + salt

    # debug
    # print("evaluated value:"+value)

    for i, char in enumerate(value):
        hashk = c_int32(hashk << 5).value + hashk + ord(char)

        # debug iterations
        # print(str(i) + ": " + str(hashk))

    return hashk


def restparse(paramstr):
    """
    "keyA[]=valA1&keyB[]=valB1&keyB[]=valB2&keyC=valC"

    => {
        "keyA": [valA1],
        "keyB": [valB1, valB2],
        "keyC": valC
        }

    NB better than flask's request.args (aka MultiDict)
       because we remove the '[]' and we rebuild the arrays
    """
    resultdict = {}
    components = paramstr.split('&')
    for comp in components:
        (keystr, valstr) = comp.split('=')

        # type array
        if len(keystr) > 2 and keystr[-2:] == "[]":
            key = unquote(keystr[0:-2])

            if key in resultdict:
                resultdict[key].append(unquote(valstr))
            else:
                resultdict[key] = [unquote(valstr)]

        # atomic type
        else:
            key = unquote(keystr)
            resultdict[key]=unquote(valstr)

    return resultdict


def mlog(loglvl, *args):
    """
    prints the logs to the output file specified in config (by default: ./services.log)

    loglvl is simply a string in ["DEBUG", "INFO", "WARNING", "ERROR"]

    config['LOG_TEE'] (bool) decides if logs also go to STDOUT
    """
    levels = {"DEBUGSQL":-1, "DEBUG":0, "INFO":1, "WARNING":2, "ERROR":3}

    timestamp = datetime.now().isoformat()

    if 'LOG_FILE' in REALCONFIG:
        try:
            logfile = open(REALCONFIG["LOG_FILE"], "a")    # a <=> append
        except:
            print("can't open the logfile indicated in "+REALCONFIG["HOME"]+"/config/parametres_comex.ini, so using STDOUT instead" )
            logfile = stdout

        if loglvl in levels:
            if levels[loglvl] >= levels[REALCONFIG["LOG_LEVEL"]]:
                print(loglvl+':'+timestamp+':', *args, file=logfile)
                if REALCONFIG["LOG_TEE"]:
                    print(loglvl+':'+timestamp+':', *args)
        if loglvl not in levels:
            first_arg = loglvl
            loglvl = "INFO"
            if levels[loglvl] >= levels[REALCONFIG["LOG_LEVEL"]]:
                print(loglvl+':'+timestamp+':', first_arg, *args, file=logfile)
                if REALCONFIG["LOG_TEE"]:
                    print(loglvl+':'+timestamp+':', first_arg, *args)

        logfile.close()
    else:
        print("WARNING: attempt to use mlog before read_config")


mlog("INFO", "conf\n  "+"\n  ".join(["%s=%s"%(k['var'],REALCONFIG[k['var']]) for k in CONFIGMENU if k['var'] != 'PASSPHRASE']))


def format_err(err):
    """
    Formats the exceptions for HTML display
    """
    return "ERROR ("+str(err.__doc__)+"):<br/>" + ("<br/>".join(format_tb(err.__traceback__)+[repr(err)]))


from uuid   import uuid4
from imghdr import what   # diagnoses filetype and returns ext
def save_blob_and_get_filename(blob, blobtype):
    """
    Saves a blob, returns the relative path

    Input blob: werkzeug.datastructures.FileStorage

    usage:
      - for any binary file, the blobtype argument will become the extension
        new_fname = tools.save_blob_and_get_filename(request.files['some_pdf'], "pdf")
        exemple result:
            output "ABCDEF.pdf"
            + saved in /data/shared_user_files/ABCDEF.pdf

      - for a picture, you should use blobtype 'pic':
        (saving path will be different and ext will be guessed by imghdr.what)
        new_fname = tools.save_blob_and_get_filename(request.files['pic_file'], "pic")
        exemple result:
            output "12345.png"
            + saved in /data/shared_user_img/12345.png
    """
    # random 32 hex chars
    filename = uuid4().hex

    if blobtype == "pic":
        # our path starts with a working copy of the saving point
        path_elts=list(IMAGE_SAVING_POINT)
        # for pics, the filext is guessed
        fileext = what(blob.stream)
    else:
        path_elts=list(BLOB_SAVING_POINT)
        fileext = blobtype

    fbasename = str(filename)+'.'+str(fileext)
    path_elts.append(fbasename)
    new_blob_relpath = path.join(*path_elts)
    # save
    blob.save(new_blob_relpath)
    # filename
    return fbasename


def prejsonize(dict_of_vals):
    """
    Prepares dict_of_vals good for dumping in json format for client-side needs
    => esp. useful for datetime values that json.dumps can't handle alone
    """

    serializable_dict = {}
    for k,v in dict_of_vals.items():
        # mlog('DEBUG', 'user: jsonize_uinfo k=v', k, '=' , v)

        # most values are already serializable
        if (type(v) not in [date, datetime]):
            serializable_dict[k] = v

        # when k is a non-empty date field
        else:
            serializable_dict[k] = v.isoformat()
            #   date   "YYYY-MM-DD"
            # datetime "YYYY-MM-DDTHH:MM:SS"

    return serializable_dict
