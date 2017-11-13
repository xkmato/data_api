from fabric.context_managers import settings, cd
from fabric.operations import run, sudo
from fabric.state import env

__author__ = 'kenneth'


def production():
    env.hosts = ['52.209.114.249']
    env.rapidpro_user = 'www-data'


def deploy(restart_celery=False, user='www-data', git_hash=None):
    source = 'https://github.com/rapidpro/data_api.git'
    proc_name = 'api'
    path = '/var/www/data_api'
    workon_home = '/var/www/.virtualenvs/api/bin/'

    env.rapidpro_user = env.rapidpro_user or user

    print "Starting deployment"
    with settings(warn_only=True):
        if run("test -d %s" % path).failed:
            run("git clone %s %s" % (source, path))
            with cd(path):
                run("git config core.filemode false")
    with cd(path):
        _rapidpro_sudo("git stash")
        if not git_hash:
            _rapidpro_sudo("git pull %s master" % source)
        else:
            _rapidpro_sudo("git fetch")
            _rapidpro_sudo("git checkout %s" % git_hash)
        _rapidpro_sudo('%spip install -r requirements.txt' % workon_home)
        _rapidpro_sudo('%spython manage.py collectstatic --noinput' % workon_home)

        sudo("chown -R %s:%s ." % (user, user))
        sudo("chmod -R ug+rwx .")

    sudo("supervisorctl restart %s" % proc_name)
    if restart_celery:
        sudo("supervisorctl restart %s_celery" % proc_name)


def _rapidpro_sudo(command):
    """
    Runs a command as env.rapidpro_user
    """
    sudo(command, user=env.rapidpro_user)
