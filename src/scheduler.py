import os
import utils
from sqlalchemy import create_engine, func, asc, or_
from sqlalchemy.orm import sessionmaker
from models import Tournaments, Flights, Swaps
from datetime import datetime, timedelta

engine = create_engine( os.environ.get('DATABASE_URL'))
Session = sessionmaker( bind=engine )
session = Session()

# Close tournaments
close_time = utils.designated_trmnt_close_time()
trmnts = session.query(Tournaments) \
            .filter( Tournaments.status == 'open') \
            .filter( Tournaments.flights.any(
                Flights.start_at < close_time
            ))

if trmnts is not None:
    for trmnt in trmnts:
        latest_flight = trmnt.flights.pop()
        if latest_flight.start_at < close_time:
            
            # This tournament is over: change status and clean swaps
            trmnt.status = 'waiting_results'
            swaps = session.query(Swaps) \
                .filter_by( tournament_id = trmnt.id ) \
                .filter( or_( 
                    Swaps.status == 'pending', 
                    Swaps.status == 'incoming',
                    Swaps.status == 'counter_incoming' ) )

            for swap in swaps:
                swap.status = 'canceled'

            db.session.commit()



