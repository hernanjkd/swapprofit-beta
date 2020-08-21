'''
    THIS FILE IS DESIGNED TO RUN EVERY 10 MINS

    Closes trmnts by setting their status to "waiting_for_results"
    
    Cancels all swaps after trmnt closure with a status of "pending" "incoming" 
    "counter_incoming"
    
    Deletes all buy_ins when trmnt closes that have a status of "pending"

    Notifies all players that have a buy_in in a trmnt when the trmnt
    starts or ends

    Keeps track of the swap payment status, calculates swap rating and saves it,
    suspends users when swap payment is not received
'''

import os
import utils
import models as m
from sqlalchemy import create_engine, func, asc, or_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from notifications import send_email, send_fcm


engine = create_engine( os.environ.get('DATABASE_URL') )
Session = sessionmaker( bind=engine )
session = Session()



###############################################################################
# Helper function to get all users from a trmnt

def get_all_players_from_trmnt(trmnt):
    users = []
    for flight in trmnt.flights:
        for buyin in flight.buy_ins:
            if buyin.user not in users: # no repeats
                users.append( buyin.user )
    return users


# Set tournaments to waiting for results, cancel all pending swaps
close_time = utils.designated_trmnt_close_time()
trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.status == 'open') \
    .filter( m.Tournaments.flights.any(
        m.Flights.start_at < close_time
    ))

for trmnt in trmnts:
    latest_flight = trmnt.flights.pop()
    if latest_flight.start_at < close_time:
            
        # This tournament is over: change status and clean swaps
        print('Update tournament status to "waiting_results", id:', trmnt.id)
        trmnt.status = 'waiting_results'
        swaps = session.query(m.Swaps) \
            .filter_by( tournament_id = trmnt.id ) \
            .filter( or_( 
                m.Swaps.status == 'pending', 
                m.Swaps.status == 'incoming',
                m.Swaps.status == 'counter_incoming' ) )

        for swap in swaps:
            print('Update swap status to "canceled", id:', swap.id)
            swap.status = 'canceled'

        session.commit()

        
        # Send fcm to all players when trmnt closes
        users = get_all_players_from_trmnt( trmnt )
        for user in users:
            print('Send notification that trmnt closed to user id: ', user.id)
            send_fcm(
                user_id = user.id,
                title = "Event Ended",
                body = f'{trmnt.name} closed at {close_time}',
                data = {
                    'id': trmnt.id,
                    # 'buyin_id': buyin and buyin.id,
                    'alert': f'{trmnt.name} closed at {close_time}',
                    'type': 'results',
                    'initialPath': 'Swap Results',
                    'finalPath': 'Profit Results'
                }
            )



###############################################################################
# Send fcm to all players when trmnt opens

_4mins_ago = datetime.utcnow() - timedelta(minutes=4)
_4mins_ahead = datetime.utcnow() + timedelta(minutes=4)

trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.start_at < _4mins_ahead ) \
    .filter( m.Tournaments.start_at > _4mins_ago )

for trmnt in trmnts:
    print('Tournament just started with id: ', trmnt.id)

    users = get_all_players_from_trmnt( trmnt )
    for user in users:
        print('Send notification that trmnt started to user, id: ', user.id)
        send_fcm(
            user_id = user.id,
            title = "Event Started",
            body = trmnt.name +' opened at ' + trmnt.start_at,
            data = {
                'id': trmnt.id,
                'alert': trmnt.name +' opened at' + trmnt.start_at,
                'type': 'event',
                'initialPath': 'Event Results',
                'finalPath': 'Event Lobby'
            }
        )



###############################################################################
# Delete buy-ins created before close time with status 'pending'

buyins = session.query(m.Buy_ins) \
    .filter_by( status = 'pending' ) \
    .filter( m.Buy_ins.flight.has( m.Flights.start_at < close_time ))

for buyin in buyins:
    print('Deleting buy-in', buyin.id)
    session.delete(buyin)

session.commit()



###############################################################################
# Calculate Swap Rating and suspend users
'''
    swap.due_at is 2 days after results come in
    2 days -> 5 stars
    4 days -> 4 stars
    6 days -> 3 stars
    8 days -> 2 stars
    9 days -> 1 star
    10+ days -> suspension (naughty list)
'''
swaps = session.query(m.Swaps) \
    .filter( m.Swaps.due_at != None ) \
    .filter( m.Swaps.paid == False )

now = datetime.utcnow()
users_to_update_swaprating = []

for swap in swaps:
    user = session.query(m.Profiles).get( swap.sender_id )
    time_after_due_date = now - swap.due_at
    
    if swap.due_at > now:
        swap_rating = 5
    elif time_after_due_date < timedelta(days=2):
        swap_rating = 4
    elif time_after_due_date < timedelta(days=4):
        swap_rating = 3
    elif time_after_due_date < timedelta(days=6):
        swap_rating = 2
    elif time_after_due_date < timedelta(days=7):
        swap_rating = 1

    # Suspend account
    else:
        swap_rating = 0
        user_account = session.query(m.Users).get( user.id )
        if user_account.status._value_ != 'suspended':
            print('Suspending user', user.id)
            user_account.status = 'suspended'
            session.commit()
        

    if swap.swap_rating != swap_rating:
        print(f'Updating swap.id {swap.id} from {swap.swap_rating} to {swap_rating}')
        swap.swap_rating = swap_rating
        session.commit()
        
        users_to_update_swaprating.append(user)


# Helper function to calculate the swap rating, used below
def calculate_swap_rating(user_id):
    swaps = session.query(m.Swaps) \
        .filter_by( sender_id=user_id ) \
        .filter( m.Swaps.due_at != None )
    total_swap_ratings = 0
    for swap in swaps:
        total_swap_ratings += swap.swap_rating
    return total_swap_ratings / swaps.count()

for user in users_to_update_swaprating:
    user.swap_rating = calculate_swap_rating( user.id )
    print(f'Updating swap_rating for user {user.id} to {user.swap_rating}')
    session.commit()