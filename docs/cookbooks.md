## Importing a new Rapidpro org

To import an org there are two options.

1. Use [the UI](https://data.uniceflabs.org/ui/import_org)
2. Run [the management command](https://github.com/rapidpro/data_api/blob/master/data_api/api/management/commands/fetch_all.py) 

The UI is a good option for small orgs or importing a single org at a time.
Data will be synced the next time the warehouse updates (currently daily).

Using the management command is a good option if you are importing multiple large organizations 
in parallel, since the Rapidpro API throttling tends to be the main bottleneck.

### Using the management command

Use the following steps to run the management command in a new screen 
(which will allow the command to run beyond the duration of an ssh session):

```bash
ssh data.uniceflabs.org
screen
sudo -u www-data bash
source /var/www/.virtualenvs/api/bin/activate
cd /var/www/data_api
./manage.py fetch_all [api_key] --debug
```
