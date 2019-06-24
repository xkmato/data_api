# Some General Information about the Production UNICEF Instance

## Azure Install

We are in the process of setting up the warehouse on a new Azure instance to be
the new production environment.
These are the details of that environment.

Sample config files can be found in [the `config_files` directory](./config_files/).

| Information | Value |
| ----------- | ----- |
| Url  | TBD |
| Host  | 23.97.220.55 |
| Admin User | dwadmin |
| Project User | rapidpro |
| Project Home | /home/rapidpro/projects/rapidpro_warehouse |
| Virtualenv Home | /home/rapidpro/.virtualenvs/rapidpro-warehouse/ |
| Server log | /home/rapidpro/logs/ |
| Settings | /home/rapidpro/projects/rapidpro_warehouse/data_api/settings_production.py |
| Supervisor Config | /home/rapidpro/services/rapidpro-supervisor.conf |
| Nginx Config | /etc/nginx/sites-available/rapidpro-warehouse |
| Database URL | unipgdwhdb.postgres.database.azure.com |
| Database User | rprodwusr@unipgdwhdb |
| Database Name | rprodw |


## Superset VM

Superset is also being setup on the Azure environment.
These are the details of that environment.

| Information | Value |
| ----------- | ----- |
| Url  | TBD |
| Host  | 40.113.110.13 |
| Admin User | dwadmin |
| Project User | superset |
| Project Home | /home/superset/projects/superset/ |
| Virtualenv Home | /home/superset/.virtualenvs/superset/ |
| Server log | TBD |
| Settings | /home/superset/projects/superset/superset_config.py |
| Supervisor Config | /home/superset/services/superset-supervisor.conf |
| Nginx Config | /etc/nginx/sites-enabled/superset |
| Database URL | unipgdwhdb.postgres.database.azure.com |
| Database User | rprodwusr@unipgdwhdb |
| Database Name | rprodw |

## Legacy Install

This information applies to the legacy machine running in AWS.
It is in the process of being phased out.

| Information | Value |
| ----------- | ----- |
| Url  | https://data.uniceflabs.org/ |
| Host  | 52.209.114.249 |
| User | www-data |
| Project Home | /var/www/data_api |
| Virtualenv Home | /var/www/.virtualenvs/api |
| Server log | /mnt/data1/data/log/api/server.log |
| Settings | /var/www/data_api/data_api/settings.py |
| Supervisor Config | /etc/supervisor/supervisord.conf |
| Nginx Config | /etc/nginx/sites-enabled/api.conf |
| SQL Database | /var/www/data_api/db.sqlite3 |
| Mongo Database (deprecated) | rapidpro-v2-test |

### Redash

The same machine is also running redash.
Here is some information about that setup.
It mostly mirrors the [installation script](https://raw.githubusercontent.com/getredash/redash/master/setup/ubuntu/bootstrap.sh)
though a few changes were made to run it in a virtualenv.

| Information | Value |
| ----------- | ----- |
| Url  | http://redash.uniceflabs.org/ |
| Host  | 52.209.114.249 |
| User | redash |
| Project Home | /opt/redash/current |
| Virtualenv Home | /usr/local/share/virtualenvs/redash/ |
| Settings | /opt/redash/current/.env |
| Supervisor Config | /etc/supervisor/conf.d/redash.conf |
| Nginx Config | /etc/nginx/sites-available/redash |
| Logs | /var/log/supervisor/ |


### Mail server

The mail is being routed through a local mail server using `postfix`.
You can use `systemd` to check its status or start/stop it. E.g.

```bash
$ sudo service postfix status
$ sudo service postfix start
```

## (Legacy) Recovering from a Reboot

**These instructions likely don't apply to the current Azure environment.**

When the machine last rebooted, the EBS data volume where mongo and log files reside did not mount, 
resulting in nothing being able to run. 
To fix this the drive must be remounted as per [Amazon's instructions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-using-volumes.html)
and then the appropriate services brought online.

These commands worked last time, though the location of the data volume should be confirmed
with `lsblk` before starting.

```bash
sudo mount /dev/xvdf /mnt/data1/
sudo service mongod start
sudo service supervisor start
```
