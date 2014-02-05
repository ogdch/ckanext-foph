ckanext-foph
============

Harvester for the Federal Office of Public Health (FOPH).

## Installation

Use `pip` to install this plugin. This example installs it in `/home/www-data`

```bash
source /home/www-data/pyenv/bin/activate
pip install -e git+https://github.com/ogdch/ckanext-foph.git#egg=ckanext-foph --src /home/www-data
cd /home/www-data/ckanext-foph
pip install -r pip-requirements.txt
python setup.py develop
```

Make sure to add `foph` and `foph_harvester` to `ckan.plugins` in your config file.

### For development
* install the `pre-commit.sh` script as a pre-commit hook in your local repositories:
** `ln -s ../../pre-commit.sh .git/hooks/pre-commit`

## Run harvester

```bash
source /home/www-data/pyenv/bin/activate
paster --plugin=ckanext-foph harvester gather_consumer -c development.ini &
paster --plugin=ckanext-foph harvester fetch_consumer -c development.ini &
paster --plugin=ckanext-foph harvester run -c development.ini
```
