from fabric.context_managers import settings, cd
from fabric.operations import run, sudo

__author__ = 'kenneth'


def deploy(user='www-data', git_hash=None):
    source = 'https://github.com/rapidpro/data_api.git'
    proc_name = 'api'
    path = '/var/www/data_api'
    workon_home = '/var/www/.virtualenvs/api/bin/'

    print "Starting deployment"
    with settings(warn_only=True):
        if run("test -d %s" % path).failed:
            run("git clone %s %s" % (source, path))
            with cd(path):
                run("git config core.filemode false")
    with cd(path):
        run("git stash")
        if not git_hash:
            run("git pull %s master" % source)
        else:
            run("git fetch")
            run("git checkout %s" % git_hash)
        run('%spip install -r requirements.txt' % workon_home)
        run('%spython manage.py collectstatic --noinput' % workon_home)

        sudo("chown -R %s:%s ." % (user, user))
        sudo("chmod -R ug+rwx .")

    sudo("supervisorctl restart %s" % proc_name)
