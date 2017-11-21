## Developer's overview

The app **communityexplorer.org** integrates 5 distinct parts:
  1. a dedicated client library `whoswho.js` for the **topbar filters**
  2. the graph exploration client library `tinawebJS` for the **MAP views**
  3. a PHP part that creates the **DIRECTORY views**
  4. a python3 flask server for the app's **user and job services** and the data API's
  5. a MySQL server for the **user data**

This complex and partly redundant structure is inherited from several years of development.
  - in production there is no need to worry about it as all is integrated by the [docker-compose wrapper](https://github.com/moma/comex2/tree/master/setup/dockers).
  - in development, you may want to run each part directly. This document is about such a use case.

-------

### Running in dev

In development, it is more natural to run the python and php parts of the app *without* the docker wrapper.
This way one can see the effects of changes without the bother of committing them, pulling them in the image and rebuilding the image.

Another difference is that without the docker wrapper, the app will be available on `0.0.0.0:9090` instead of port 8080.

#### Minimal run commands

```
# get the code
git clone https://github.com/moma/comex2

# get prerequisites
sudo apt install php7.0-fpm php7.0-mysql python3 libmysqlclient-dev
cd $INSTALL_DIR
sudo pip3 install -r setup/requirements.txt
```

Then to run the comex2 server for development just do:
```
bash comex-run.sh -d     # => port 9090
```

At this point you're running a python gunicorn webserver pointing to the files in `/services`. You can connect to `0.0.0.0:9090` and checkout the app, but you won't have the php, DB access and authentication elements working yet.

-------

#### Full dev config
  1. php serving
  2. mysql database
  3. doors authentication server
  4. gunicorn webserver (linked to 1 & 2 via `$SQL_HOST` and `$DOORS_HOST`)

##### 1) Set up your php
Configure the serving of our php documents in your nginx with something like this:

```
location ~ \.php$ {
    include snippets/fastcgi-php.conf;
    fastcgi_pass unix:/run/php/php7.0-fpm.sock;
    # here adapt documentroot to your real path to comex
    fastcgi_param SCRIPT_FILENAME /home/romain/comex2$fastcgi_script_name;
    #                             -------------------
    #                                 documentroot
}
```


##### 2) Set up your mysql database

###### If you have your own local mysql
```
# edit ini file to put the correct SQL_HOST (or IP)
nano config/parametres_comex.ini
```
Then just create the table following [the table specifications](https://github.com/moma/comex2/blob/master/doc/table_specifications.md)

###### If you want a dedicated mysql in docker

  - Follow the detailed steps in [mysql_prerequisites](https://github.com/moma/comex2/blob/master/setup/dockers/mysql_prerequisites.md): it will explain how to create the docker and connect to it.

  - Then create the table following [the table specifications](https://github.com/moma/comex2/blob/master/doc/table_specifications.md)
  - Now run it as follows:

```
# run the database docker
docker start comex_db

# read its IP
docker inspect comex_db | jq -r '.[0].NetworkSettings.IPAddress'

# edit ini file to put it as SQL_HOST
nano config/parametres_comex.ini
```

##### 3) Set up a doors connection
Again, the environment variable `DOORS_HOST` must simply be set to the doors server's hostname or IP, and `DOORS_PORT` to the doors server's exposed port.

###### If you have a doors server
```
# edit ini file to put it as DOORS_HOST and DOORS_PORT
nano config/parametres_comex.ini
```

###### If you have no doors server

For tests you can use a self-deployed doors container, available from ISCPIF on [this repository](https://github.com/ISCPIF/doors-docker)


##### 4) Run the regomex app with gunicorn
```
bash comex-run.sh -d
```

The user DB service is then accessible locally on `0.0.0.0:9090/services/user`

The API server is then accessible locally on `0.0.0.0:9090/services/api`
(for instance `services/api/aggs?field=keywords&like=biol`)

**Remark:** the prefix `/services` and the routes `/user` and `/api` can both be changed in the config file

-------


#### Detailed links
For further development work, we list here pointers to the main elements of the app. The code is commented.

###### Server-side
  - the mySQL server:
    - it has its own docker in  [`setup/dockers/comex2_mysql_server`](https://github.com/moma/comex2/tree/master/setup/dockers/comex2_mysql_server)
    - when it's run for the first time, it looks for the data under `data/shared_mysql_data/`
    - if the directory doesn't exist, it creates the tables
    - otherwise it uses the data that is already there


  - the PHP directory pages:
    - the entry point is [`print_directory.php`](https://github.com/moma/comex2/blob/master/print_directory.php)
    - the dependencies are under [`php_library`](https://github.com/moma/comex2/tree/master/php_library)


  - [python services for user management and data APIs](https://github.com/moma/comex2/tree/master/services)
    - all the services views are in `services/main.py`
    - `services/user.py` handles DB add/modify/remove scholars
    - `services/dbdatapi.py` contains
      - a facet agregation API (used for autocompletes)
      - DB extraction functions to create bipartite graphs for the **MAP data**
    - uses the [templates](https://github.com/moma/comex2/tree/master/templates)
      - `base_layout.html` is the common part to all templates
      - `rootindex.html` is the index.html template

###### Client-side
 - whoswho.js topbar: [static/js/whoswho.js](https://github.com/moma/comex2/blob/master/static/js/whoswho.js)
 - user forms validation:
  - [static/js/comex_user_shared.js](https://github.com/moma/comex2/blob/master/static/js/comex_user_shared.js)
  - [static/js/comex_user_shared_auth.js](https://github.com/moma/comex2/blob/master/static/js/comex_user_shared_auth.js)
 - tinawebJS graph exploration:
   - [static/tinawebJS](https://github.com/moma/comex2/blob/master/static/tinawebJS)
   - integrated via git-subtree from [this upstream repo](https://github.com/moma/ProjectExplorer)
   - using the settings from [this preset file](https://github.com/moma/comex2/blob/master/static/tinawebJS/twpresets/settings_explorerjs.comex.js)
   - using modules made especially for comex
     - module to load and display the comex topbar CSS and JS inside the tina explorer view [static/tinawebModules/comexTopBarLoader](https://github.com/moma/comex2/blob/master/static/tinawebModules/comexTopBarLoader)
     - module to allow a dynamical demo (pauses on user action) [static/tinawebModules/comexTopBarLoader](https://github.com/moma/comex2/blob/master/static/tinawebModules/comexTopBarLoader)
