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
resp = requests.get( os.environ['POKERSOCIETY_HOST'] + '/swapprofit/update?span=all' )

if not resp.ok:
    print( resp.content )
    exit()


data = resp.json()

print('data', data)


for d in data[0]: 
        
    print('d', d)

    # CASINOS - ADD/UPDATE
    casinojson = d['casino']
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

for d in data[1]: 
    # TOURNAMENTS - ADD/UPDATE
    trmntjson = d['tournament']
    trmnt = session.query( m.Tournaments ).get( trmntjson['id'] )
    print('LISTEN', trmnt)
    x = {col:val for col,val in trmntjson.items()}
    # ADD TOURNAMENT
    if trmnt is None:
        print(f'Adding trmnt id: {trmntjson["id"]}')
        session.add( m.Tournaments( **trmntjson ))
    
    # UPDATE TOURNAMENT
    else:
        print(f'Updating trmnt id: {trmntjson["id"]}')
        for col,val in trmntjson.items():
            if getattr(trmnt, col) != val:
                setattr(trmnt, col, val)
        
    # FLIGHTS - ADD/UPDATE
    for flightjson in d['flights']:
        flight = session.query( m.Flights ).get( flightjson['id'] )
        
        # ADD FLIGHT
        if flight is None:
            print(f'Adding flight id: {flightjson["id"]}')
            session.add( m.Flights(
                **{col:val for col,val in flightjson.items()} ))
        
        # UPDATE FLIGHT
        else:
            print(f'Updating flight id: {flightjson["id"]}')
            for col,val in flightjson.items():
                if getattr(flight, col) != val:
                    setattr(flight, col, val)

    session.commit()