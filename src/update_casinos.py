from sqlalchemy import create_engine, func, asc, or_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import requests
import utils
import models as m
import os

engine = create_engine( os.environ.get('DATABASE_URL'))
Session = sessionmaker( bind=engine )
session = Session()

# STARTS IN THE POKERSOCIETY DATABASE
resp = requests.get( os.environ['POKERSOCIETY_HOST'] + '/swapprofit/casinos/update?span=all' )

if not resp.ok:
    print( resp.content )
    exit()


data = resp.json()

print('data',data)

for d in data:

    # CASINOS - ADD/UPDATE
    casinojson = d
    csno = session.query( m.Casinos ).get( casinojson['id'] )

    
    
    # CASINO Update
    if csno is None:
        print(f'Adding csno id: {casinojson["id"]}')
        session.add( m.Casinos(
            **{col:val for col,val in casinojson.items()} ))
    else:
        print(f'Updating csno id: {casinojson["id"]}')
        for col,val in casinojson.items():
            if getattr(csno, col) != val:
                setattr(csno, col, val)
        
    

   

    session.commit()