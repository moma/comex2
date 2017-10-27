To remember the setup

#### Dir permissions
```
cd /path/to/comex2

# dirs must have u+x to be readable in unix
sudo find . -type d -exec chmod 755 {} +

# files don't need +x, except php
sudo find . -type f -exec chmod 644 {} +
sudo chmod 755 *.php

# and all this belongs to www-data group
sudo chown -R :www-data .
```

For the `data` directory:
  - we need root ownership for the mysql part (accessed by the mysql docker)
  - and www-data for the pictures

```
# data must be writeable
sudo chmod 774 data
sudo chown :www-data data

# mysql data more restrictive
sudo find data/shared_mysql_data/ -type d -exec chmod 750 {} +
sudo find data/shared_mysql_data/ -type f -exec chmod 640 {} +

# and accessible by docker user
sudo chown -R 999:www-data data/shared_mysql_data

# data also contains shared user dirs
sudo chown -R :www-data data/shared_user_img
sudo chown -R :www-data data/shared_user_files
```
