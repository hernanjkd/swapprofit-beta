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

resp = requests.get( os.environ['POKERSOCIETY_HOST'] + '/swapprofit/update?span=all' )

if not resp.ok:
    print( resp.content.decode("utf-8")[-233:] )
    exit()


data = resp.json()

for d in data:

    # TOURNAMENTS
    trmntjson = d['tournament']
    trmnt = session.query( m.Tournaments ).get( trmntjson['id'] )
    if trmnt is None:
        print(f'Adding trmnt id: {trmntjson["id"]}')
        session.add( m.Tournaments(
            **{col:val for col,val in trmntjson.items()} ))
    else:
        print(f'Updating trmnt id: {trmntjson["id"]}')
        for col,val in trmntjson.items():
            if getattr(trmnt, col) != val:
                setattr(trmnt, col, val)
        
    # FLIGHTS
    for flightjson in d['flights']:
        flight = session.query( m.Flights ).get( flightjson['id'] )
        if flight is None:
            print(f'Adding flight id: {flightjson["id"]}')
            session.add( m.Flights(
                **{col:val for col,val in flightjson.items()} ))
        else:
            print(f'Updating flight id: {flightjson["id"]}')
            for col,val in flightjson.items():
                if getattr(flight, col) != val:
                    setattr(flight, col, val)

    session.commit()