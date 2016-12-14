## Nginx configuration

Independantly from the backends like mysql or doors, the comex app is in two parts:
  - the legacy php comex app
  - the new python registration app

A good way to make the two coexist is to use nginx as follows

### 1) Install nginx
If you don't already have nginx on the deployment machine, follow these steps first:
```
sudo service apache2 stop

sudo apt install nginx-full

# check the status
sudo service nginx status
```


### 2) Replace nginx conf by our *comex+reg* configuration

Create the conf files for comex
```
cd /etc/nginx/sites-available
sudo nano comex.conf
```

This below is a full config exemple you can paste in nano:
  - it serves the comex app (legacy php), in `/`
  - it also serves registration app, in `/services/user/register`  


```ini
# Full server config: php comex as root and api + reg as services subpath
# ========================================================================
server {
    listen 80 ;
    listen [::]:80 ;

    server_name communityexplorer.org;

    # adapt path to your php docroot
    root /home/me/comex2 ;

    # get the logs in a custom place
    # (adapt paths)
    access_log /home/me/somewhere/access.log ;
    error_log /home/me/somewhere/error.log ;

    location / {
        index     index.html index.php ;
    }

    location ~ \.php$ {
        include   snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php7.0-fpm.sock;

        # here we adapted $documentroot to our real php docroot
        fastcgi_param SCRIPT_FILENAME /home/me/comex2/$fastcgi_script_name;
        #                             ----------------
    }

    # no root here => independant app serving both services/user (formerly know as regcomex) and services/api (ex formerly known as comex_install)
    # (but /locationpath must match this app's default route)
    location /services {
        # point to gunicorn server
        proxy_pass http://0.0.0.0:9090;
        proxy_redirect     off;

        # useful to keep track of original IP before reverse-proxy
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host $server_name;
    }

    # faster static serving
    location /static {
        alias  /home/me/comex2/static/;
        autoindex on;
    }

    location ~ /\.ht {
        deny all;
    }
}
```

Finally, to enable the conf:

```
cd /etc/nginx/sites-enabled
sudo ln -s ../sites-available/regcomex.conf
```

**NB:**   
If you use this configuration without changing anything else than the paths, then *remove* all other confs from `sites-enabled` (because this one is written to be standalone)