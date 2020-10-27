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
import requests

engine = create_engine( os.environ.get('DATABASE_URL') )
Session = sessionmaker( bind=engine )
session = Session()



###############################################################################
# Helper function to get all users from a trmnt

def get_all_players_from_trmnt(trmnt):
    the_users = []
    for flight in trmnt.flights:
        for a_buyin in flight.buy_ins:
            print('a_buyin .user',a_buyin.user )
            if a_buyin.user not in the_users: # no repeats
                the_users.append( a_buyin.user )
    return the_users


# Set tournaments to waiting for results, cancel all pending swaps
close_time = utils.designated_trmnt_close_time()
trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.status == 'open') \
    .filter( m.Tournaments.flights.any(
        m.Flights.start_at < close_time
    ))

for trmnt in trmnts:
    latest_flight = trmnt.flights.pop()
    print('timesss',latest_flight.start_at, close_time)
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
            buyin = m.Buy_ins.get_latest(
                user_id=user.id, tournament_id=trmnt.id )
            time = datetime.utcnow()
            domain = os.environ['MAILGUN_DOMAIN']
            requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
                auth=(
                    'api',
                    os.environ.get('MAILGUN_API_KEY')),
                data={
                    'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                    'to': f'{user.user.email}',
                    'subject': trmnt.name + ' has just ended',
                    'text': 'Sending text email',
                    'html': f'''
                        <div>trmnt.id {trmnt.id}</div><br />
                        <div>{trmnt.start_at} trmnt.start_at</div>
                        <div>{time} datetime.utcnow()</div>
                        
                    '''
                })
            print('Sending notification that trmnt closed to user id: ', user.id)
            if user.event_update is True:
                send_fcm(
                    user_id = user.id,
                    title = "Event Ended",
                    body = f'{trmnt.name} closed at {close_time}',
                    data = {
                        'id': trmnt.id,
                        'buy_in': buyin and buyin.id,
                        'alert': f'{trmnt.name} closed at {close_time}',
                        'type': 'results',
                        'initialPath': 'Event Results',
                        'finalPath': 'Swap Results' }
                )
            else:
                print("Not Sending")


###############################################################################
# Send fcm to all players when trmnt opens

_4mins_ago = datetime.utcnow() - timedelta(minutes=4)
_4mins_ahead = datetime.utcnow() + timedelta(minutes=4)

trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.start_at < _4mins_ahead) \
    .filter( m.Tournaments.start_at > _4mins_ago )

for trmnt in trmnts:
    users = get_all_players_from_trmnt( trmnt )
    for user in users:
        buyin = m.Buy_ins.get_latest(
            user_id=user.id, tournament_id=trmnt.id )
        time=datetime.utcnow()
        domain = os.environ['MAILGUN_DOMAIN']
        requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
            auth=(
                'api',
                os.environ.get('MAILGUN_API_KEY')),
            data={
                'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                'to': f'{user.user.email}',
                'subject': trmnt.name + ' has just started',
                'text': 'Sending text email',
                'html': f'''
                    <div>trmnt.id {trmnt.id}</div><br />
                    <div>{trmnt.start_at} trmnt.start_at</div>
                    <div>{time} datetime.utcnow()</div>
                    <div>{_4mins_ago} _4mins_ago</div>
                    <div>{_4mins_ahead} _4mins_ahead</div>
                '''
        })
        if user.event_update is True:
            send_fcm(
                user_id = user.id,
                title = "Event Started",
                body = f'{trmnt.name}  opened at ' + f'{trmnt.start_at}',
                data = {
                    'id': trmnt.id,
                    'buy_in': buyin and buyin.id,
                    'alert': f'{trmnt.name}  opened at ' + f'{trmnt.start_at}',
                    'type': 'event',
                    'initialPath': 'Event Listings',
                    'finalPath': 'Event Lobby' }
            )
        else:
            print('Not Sending')



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
    trmt_id = swap.tournament_id
    if swap.due_at > now:
        swap_rating = 5
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "5 Star",
                body = "You're account has been suspended until you've paid the swaps you owe",
                data = {
                    'id': trmnt.id,
                    'alert': "You're account has been suspended until you've paid the swaps you owe",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results' }
            )
    elif time_after_due_date < timedelta(days=2):
        swap_rating = 4
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "4 Star",
                body = "2 days",
                data = {
                    'id': trmt_id,
                    'alert': "4 star",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results' }
            )
    elif time_after_due_date < timedelta(days=4):
        swap_rating = 3
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "3 Star",
                body = "4 days",
                data = {
                    'id': trmt_id,
                    'alert': "3 Star",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results' }
            )
    elif time_after_due_date < timedelta(days=6):
        swap_rating = 2
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "2 Star",
                body = "6 Days",
                data = {
                    'id': trmt_id,
                    'alert': "2 Star",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results'
                }
            )
    elif time_after_due_date < timedelta(days=7):
        swap_rating = 1
        send_fcm(
            user_id = user.id,
            title = "1 Star",
            body = "7 Days",
            data = {
                'id': trmt_id,
                'alert': "1 Star",
                'type': 'result',
                'initialPath': 'Event Results',
                'finalPath': 'Swap Results' 
            }
        )

    # Suspend account
    else:
        swap_rating = 0
        user_account = session.query(m.Users).get( user.id )
        user_account.naughty = True
        print('Put on naughty list', user.id)
        session.commit()
        send_fcm(
            user_id = user.id,
            title = "Account Suspension",
            body = "You're account has been suspended until you've paid the swaps you owe",
            data = {
                'id': trmt_id,
                'alert': "You're account has been suspended until you've paid the swaps you owe",
                'type': 'result',
                'initialPath': 'Event Results',
                'finalPath': 'Swap Results'
            }
        )     

    if swap.swap_rating != swap_rating:
        # print(f'Updating swap rating for swap {swap.id} from {swap.swap_rating} to {swap_rating}')
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
    # print(f'Updating swap rating for user {user.id} to {user.swap_rating}')
    session.commit()
