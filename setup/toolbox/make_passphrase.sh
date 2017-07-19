#! /bin/bash

export someasciikey=`< /dev/urandom tr -dc _A-Za-z0-9 | head -c128`
perl -pe "s/^PASSPHRASE=\"[^\"]+\"/PASSPHRASE=\"${someasciikey}\"/" config/parametres_comex.ini > temp.ini
mv temp.ini config/parametres_comex.ini
echo "updated passphrase with random string"
