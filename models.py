from peewee import *
import os
from settings import settings
import datetime

db = SqliteDatabase(os.path.join(settings['sqlite_path'], 'slack.shortener.db'))


class Url(Model):
    name = CharField(unique=True)
    dest_url = CharField()
    created_by_id = CharField()
    created_by_username = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db
