### About deployment of ProjectExplorer

This directory contains the copy of "tina2" from the ProjectExplorer repo:
https://github.com/moma/ProjectExplorer


#### Sub-tree creation
It was added via:
```
git remote add subtreeProjectExplorer https://github.com/moma/ProjectExplorer
git subtree add --squash --prefix=static/tinawebJS subtreeProjectExplorer master
```

#### Configuration

We generated the production html file:
```
cd static/tinawebJS
bash twtools/adapt_html_paths.sh 'static/tinawebJS/'
cd ../..
ln -s static/tinawebJS/explorerjs.prod.html explorerjs.html
```

And we used the adapted settings file (comex branding and no relatedDoc):
```
cd static/tinawebJS/
cp twpresets/settings_explorerjs.comex.js settings_explorerjs.js
```

#### To pull an upstream version
```
# go to the repo root
cd comex2

# pull upstream remote (and possibly merge + git commit)
git subtree pull --squash --prefix=static/tinawebJS subtreeProjectExplorer master

# also update with the comex presets (or diff and hand fix) and html prod file
cd static/tinawebJS
cp twpresets/settings_explorerjs.comex.js settings_explorerjs.js
git add settings_explorerjs.js
bash twtools/adapt_html_paths.sh 'static/tinawebJS/'
```
