import os
import utils
import models as m
from sqlalchemy import create_engine, func, asc, or_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

engine = create_engine( os.environ.get('DATABASE_URL'))
Session = sessionmaker( bind=engine )
session = Session()

'''
close_time = utils.designated_trmnt_close_time()
trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.status == 'open') \
    .filter( m.Tournaments.flights.any(
        m.Flights.start_at < close_time
    ))

if trmnts is not None:
    for trmnt in trmnts:
        latest_flight = trmnt.flights.pop()
        if latest_flight.start_at < close_time:
            
            # This tournament is over: change status and clean swaps
            print('update tournament', trmnt.id)
            trmnt.status = 'waiting_results'
            swaps = session.query(m.Swaps) \
                .filter_by( tournament_id = trmnt.id ) \
                .filter( or_( 
                    m.Swaps.status == 'pending', 
                    m.Swaps.status == 'incoming',
                    m.Swaps.status == 'counter_incoming' ) )

            for swap in swaps:
                print('update swap', swap.id)
                swap.status = 'canceled'

            session.commit()


# Delete buy-ins created before close time with status 'pending'
buyins = session.query(m.Buy_ins) \
    .filter_by( status = 'pending' ) \
    .filter( m.Buy_ins.flight.has( m.Flights.start_at < close_time ))

for buyin in buyins:
    print('deleting buy-in', buyin.id)
    session.delete(buyin)

session.commit()
'''

y = session.query(m.Swaps).filter_by(sender_id=1)
print(y.count())