import couchdb
import json
from pprint import pprint

dbhost = 'http://127.0.0.1:5984'
dbname = 'polygons'

couch = couchdb.Server(dbhost)
db = couch.create(dbname)

with open('geojsonfile_mapshaper_simplified.json') as data_file:
    data = json.load(data_file)

for geometry in data["features"]:
    db.save(geometry)