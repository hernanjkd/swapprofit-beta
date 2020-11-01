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
import requests
from datetime import datetime, timedelta
import pytz
import utils
import models as m
from sqlalchemy import create_engine, func, asc, or_
from sqlalchemy.orm import sessionmaker
from notifications import send_email, send_fcm
from models import db, Profiles, Tournaments, Swaps, Flights, Buy_ins, Devices, \
    Transactions, Users

engine = create_engine( os.environ.get('DATABASE_URL') )
Session = sessionmaker( bind=engine )
session = Session()



###############################################################################
# Helper function to get all users from a trmnt

def get_all_players_from_trmnt(trmnte):
    the_users = []
    for flight in trmnte.flights:
        for a_buyin in flight.buy_ins:
            if a_buyin.user not in the_users: # no repeats
                the_users.append( a_buyin.user )
    return the_users

# Set tournaments to waiting for results, cancel all pending swaps
# this is now MINUS 17 hours
close_time = utils.designated_trmnt_close_time()

# any tournaments that are open and latest flight start at isnt later close_time
trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.status == 'open') \
    .filter( m.Tournaments.flights.any(
        m.Flights.start_at < close_time
    ))

if trmnts is not None:
    for trmnt in trmnts:
                   
        latest_flight = trmnt.flights[-1]
        print(latest_flight.start_at.strftime("%c"))
        start_time = latest_flight.start_at + timedelta(hours=17)
        lastTime = start_time.strftime("%b. %d %I:%M %p")
        if latest_flight.start_at < close_time:
            # This tournament is over: change status and clean swaps
            trmnt.status = 'waiting_results' 
            swaps = session.query(Swaps) \
                .filter( Swaps.tournament_id == trmnt.id ) \
                .filter( or_(
                    Swaps.status == 'pending',
                    Swaps.status == 'incoming',
                    Swaps.status == 'counter_incoming' ) )

            if swaps is not None:
                for swap in swaps:
                    print('Update swap status to "canceled", id:', swap.id)
                    swap.status = 'canceled'
                session.commit()

            eww = session.query(m.Tournaments).get(trmnt.id)


            users = get_all_players_from_trmnt(eww)

            # if users is not None:
            #     for user in users:
            #         time = datetime.utcnow()
            #         domain = os.environ['MAILGUN_DOMAIN']
            #         requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
            #         auth=(
            #             'api',
            #             os.environ.get('MAILGUN_API_KEY')),
            #         data={
            #             'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
            #             'to': user.user.email,
            #             'subject': 'Event Ended: ' + trmnt.name,
            #             'text': 'Sending text email',
            #             'html': f'''
            #                 <div>trmnt.id {trmnt.id}</div><br />
            #                 <div>{trmnt.start_at} trmnt.start_at</div>
            #                 <div>{time} datetime.utcnow()</div>
                            
            #             '''
            #         })

            #         # buyin = m.Buy_ins.get_latest(user_id=user.id, tournament_id=trmnt.id )
                    
            #         # Send fcm to all players when trmnt closes
            #         if user.event_update is True:
            #             send_fcm(
            #                 user_id = user.id,
            #                 title = "Event Ended",
            #                 body = trmnt.name + ' closed at ' + lastTime,
            #                 data = {
            #                     'id': trmnt.id,
            #                     # 'buy_in': buyin and buyin.id,
            #                     'alert': 'Event Ended: ' + trmnt.name,
            #                     'type': 'result',
            #                     'initialPath': 'Event Results',
            #                     'finalPath': 'Swap Results',
            #                 }
            #             )
            print('Update tournament status to "waiting_results", id:', trmnt.id)
            # buyin = m.Buy_ins.get_latest(user_id=user.id, tournament_id=trmnt.id )


###############################################################################
# Send fcm to all players when trmnt opens

_5mins_ago = datetime.utcnow() - timedelta(minutes=5)
_5mins_ahead = datetime.utcnow() + timedelta(minutes=5)

trmnts = session.query(m.Tournaments) \
    .filter( m.Tournaments.start_at < _5mins_ahead) \
    .filter( m.Tournaments.start_at > _5mins_ago )

if trmnts is not None:
    for trmnt in trmnts:
        users = get_all_players_from_trmnt( trmnt )
        for user in users:
            # buyin = m.Buy_ins.get_latest(user_id=user.id, tournament_id=trmnt.id )
            time=datetime.utcnow()
            domain = os.environ['MAILGUN_DOMAIN']
            requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
                auth=(
                    'api',
                    os.environ.get('MAILGUN_API_KEY')),
                data={
                    'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                    'to': user.user.email,
                    'subject': 'Event Started: ' + trmnt.name,
                    'text': 'Sending text email',
                    'html': f'''
                        <div>trmnt.id {trmnt.id}</div><br />
                        <div>{trmnt.start_at} trmnt.start_at</div>
                        <div>{time} datetime.utcnow()</div>
                        <div>{_5mins_ago} _4mins_ago</div>
                        <div>{_5mins_ahead} _4mins_ahead</div>
                    '''
            })

            # buyin = m.Buy_ins.query.get_latest(user_id=user.user.id, tournament_id=trmnt.id )
            if user.event_update is True:
                isdst_now_in = lambda zonename: bool(datetime.now(pytz.timezone(zonename)).dst())
                y = 0 if isdst_now_in(trmnt.time_zone) else -1
                z = y + int(trmnt.time_zone[7:])
                est = pytz.timezone(trmnt.time_zone).localize(trmnt.start_at) + timedelta(hours=z)
                start_time = est.strftime("%b. %d, %a. %I:%M %p")

                send_fcm(
                    user_id = user.id,
                    title = "Event Started",
                    body = trmnt.name + '\nopened at ' + start_time,
                    data = {
                        'id': trmnt.id,
                        'alert': trmnt.name + '\nopened at ' + start_time,
                        'type': 'event',
                        'initialPath': 'Event Listings',
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
    trmt_id = swap.tournament_id
    if swap.due_at > now:
        swap_rating = 5
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "5 Star Reminder",
                body = "2 days after results",
                data = {
                    'id': trmnt.id,
                    'alert': "You're account has been suspended until you've paid the swaps you owe",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results'
                }
            )
    elif time_after_due_date < timedelta(days=2):
        swap_rating = 4
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "4 Star Reminder",
                body = "4 days after results",
                data = {
                    'id': trmt_id,
                    'alert': "4 star",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results'
                }
            )
    elif time_after_due_date < timedelta(days=4):
        swap_rating = 3
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "3 Star Reminder",
                body = "6 days after results",
                data = {
                    'id': trmt_id,
                    'alert': "3 Star",
                    'type': 'result',
                    'initialPath': 'Event Results',
                    'finalPath': 'Swap Results'
                }
            )
    elif time_after_due_date < timedelta(days=6):
        swap_rating = 2
        if user.result_update is True:
            send_fcm(
                user_id = user.id,
                title = "2 Star Reminder",
                body = "8 Days after results",
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
            title = "1 Star Reminder",
            body = "9 Days after results",
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
        # user_account = session.query(m.Users).get( user.id )
        user.naughty = True
        print('Put on naughty list', user, user.id, user.naughty)
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
                'finalPath': 'Swap Results',
            }
        )

    if swap.swap_rating != swap_rating:
        # print(f'Updating swap rating for swap {swap.id} from {swap.swap_rating} to {swap_rating}')
        swap.swap_rating = swap_rating
        session.commit()
        users_to_update_swaprating.append(user)


# # Helper function to calculate the swap rating, used below
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
