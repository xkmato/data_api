## Importing Rapidpro Data

Due to the long time it takes to import an organization's data, 
it is recommended that organizations are imported via the command line.

This also allows for importing multiple large organizations in parallel, 
since the Rapidpro API throttling can be a bottleneck.

Use the following steps to run the management command in a new screen 
(which will allow the command to run beyond the duration of an ssh session):

```bash
ssh dwadmin@rapidpro-api.unicef.io
# enter provided password - can get from Cory or Paramjit
screen
sudo -u rapidpro -i
workon rapidpro-warehouse
# you should be automatically moved to the /home/rapidpro/projects/rapidpro_warehouse directory
./manage.py sync_organization_data [org_api_key] --debug
```

For a complete list of options see the 
[sync_organization_data management command](https://github.com/rapidpro/data_api/blob/master/data_api/staging/management/commands/sync_organization_data.py)

This process can be used to run an initial import or an update of an organization's data.

## Checking status

Generally the best way to check the status of an import is to resume the screen and look at the output.

This can be done using `screen -r [id]` where `[id]` is the id if the screen session. 

You can also check the status using the [django admin](http://rapidpro-api.unicef.io/admin).

Specifically the list of [sync checkpoints](http://rapidpro-api.unicef.io/admin/staging/synccheckpoint/)
can be filtered to show what is currently running / has run for a particular organization.

You can also check if an import for a particular data model is still running by filtering the
data model type to that organization and checking if the total number of objects increases over time. 

## Recovering from failure

If an import fails there may be a dangling sync checkpoint left behind, which will prevent data for that 
particular org / data model from being imported again.

To resolve this issue you can go to the list of [running sync check points](http://rapidpro-api.unicef.io/admin/staging/synccheckpoint/?is_running__exact=1)
and delete the offending checkpoint.
This wil cause the data model to be *completely reingested* the next time the import runs for that org.

Note that you should not delete the checkpoint if the import for that model is still running!
