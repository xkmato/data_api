from .settings_common import *

SECRET_KEY = '5fde38c8-b49b-11e7-800e-3c970e7be43b'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'rapidpro_data_api',
        'USER': 'postgres',
        'HOST': 'localhost',
    }
}
