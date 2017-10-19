# ReadOnly API for Rapidpro data warehouse


# Dev Setup / Installation

## Prerequisites

- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Python](https://www.python.org/downloads/)
- [Virtualenv](https://virtualenv.pypa.io/en/stable/)
- [Virtualenvwrapper](https://virtualenvwrapper.readthedocs.io/en/latest/)
- [MongoDB](https://docs.mongodb.com/manual/administration/install-community/)

## Setup Virtualenv

`mkvirtualenv --no-site-packages rapidpro-dataapi`

## Install requirements:

Make sure you are in the root directory of the repository then run:

`pip install -r requirements.txt`

## Configure settings

If you need non-default settings, create a `localsettings.py` file in `data_api`.
Else you can use `settings_dev`.

For all `./manage.py` commands, replace `[settings module]` with whichever settings module you need, e.g. `data_api.settings_dev`

If you don't want to specify your settings module every time, just add

`export DJANGO_SETTINGS_MODULE=data_api.localsettings`

to your `$VIRTUAL_ENV/bin/postactivate` file.

And add `unset DJANGO_SETTINGS_MODULE` to `$VIRTUAL_ENV/bin/predeactivate` to avoid it messing with other virtualenvs.

## Setup Database

```
sudo -u postgres createdb rapidpro_data_api
./manage.py migrate --settings=[settings module]
```

## Run Server

`./manage.py runserver --settings [settings module]`
