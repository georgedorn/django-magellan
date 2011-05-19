from django.db.models.signals import post_syncdb
from django.db.models import get_models
import intranet_search.models



def fix_profile_key_field(sender, **kwargs):
    """
    Lame fix for django's sqlite support being mostly borked re: autoincrement fields;
    this could be genericized to handle all models in the module, but for now I'm just doing
    this the hacky way.
    """
    from django.db import connection, transaction
    if 'sqlite' not in connection.settings_dict['ENGINE']:
        return
    cursor = connection.cursor()
    table_name = "intranet_search_spiderprofile"
    
    res = cursor.execute("select sql from sqlite_master where name = '%s'" % table_name)
    schema = res.fetchone()[0]
    if 'AUTOINCREMENT' in schema:
        return #already done
    
    #drop the old table
    cursor.execute("drop table %s" % table_name)

#    #rename the table
#    tmp_table_name = "tmp_table_for_spiderprofile"
#    cursor.execute('ALTER TABLE "%s" RENAME TO "%s"' % (table_name, tmp_table_name))
#    
    #create new table with correct schema
    new_schema = schema.replace('"id" INTEGER NOT NULL,', '"id" INTEGER PRIMARY KEY,')
    cursor.execute(new_schema)
    
    
    
post_syncdb.connect(fix_profile_key_field, sender=intranet_search.models)
