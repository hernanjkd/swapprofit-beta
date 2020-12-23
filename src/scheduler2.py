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
from models import ( db, Profiles, Tournaments, Swaps, Flights, Buy_ins, Devices, \
    Transactions, Users )

engine = create_engine( os.environ.get('DATABASE_URL') )
Session = sessionmaker( bind=engine )
session = Session()

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
swapsToBePaid = session.query(m.Swaps) \
    .filter( m.Swaps.due_at != None ) \
    .filter( m.Swaps.paid == False )

swapsToBeConfirmed = session.query(m.Swaps) \
    .filter( m.Swaps.due_at != None ) \
    .filter( m.Swaps.paid == True ) \
    .filter(m.Swaps.confirmed == False) \
    .filter(m.Swaps.disputed == False)

now = datetime.utcnow()
users_to_update_swaprating = []
users_to_notify = []

# REMINDERS FOR SWAPS TO BE PAID (SEND ONE NOTIFICATION PER USER, PER TOURNAMENT ID)
for swap in swapsToBePaid:
    user = session.query(m.Profiles).get( swap.sender_id )
    # swap due_at has 4 days after results posted
    print("User that has to pay: ", user)
    first_due = swap.due_at 
    time_after_due_date = now - swap.due_at
    trmt_id = swap.tournament_id
    title = ''
    body = ''
    if now < swap.due_at:
        title="5 Star Reminder"
        body="Pay before Swap Due"
    elif time_after_due_date < timedelta(days=2):
        title="4 Star Reminder"
        body="Pay before 2 Days after Due Date"
    elif time_after_due_date < timedelta(days=4):
        title="3 Star Reminder"
        body="Pay before 4 Days after Due Date"
    elif time_after_due_date < timedelta(days=6):
        title="2 Star Reminder"
        body="Pay before 6 Days after Due Date"
    elif time_after_due_date < timedelta(days=8):
        title="1 Star Reminder"
        body="8 days after results"
    elif time_after_due_date < timedelta(days=9):
        title="Warning: Account Suspension"
        body="9 days after results"
        time=datetime.utcnow()
        domain = os.environ['MAILGUN_DOMAIN']
        requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
            auth=(
                'api',
                os.environ.get('MAILGUN_API_KEY')),
            data={
                'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                'to': user.user.email,
                'subject': 'You are in Danger of being Suspended',
                'text': 'Sending text email',
                'html': f'''
                    <div>trmnt.id {trmnt.id}</div><br />
                    <div>{trmnt.start_at} trmnt.start_at</div>
                    <div>{time} datetime.utcnow()</div>
                    <div>{_5mins_ago} _4mins_ago</div>
                    <div>{_5mins_ahead} _4mins_ahead</div>
                '''
        })
        
    # Suspend account
    else:
        title="Account Suspension"
        body="You're account has been suspended until you pay your swaps"
        swap_rating = 0
        # user_account = session.query(m.Users).get( user.id )
        user.naughty = True
        print('Put on naughty list', user, user.id, user.naughty)
        session.commit()
        send_email( template='account_suspension', emails=user.email, 
            # data={'validation_link': utils.jwt_link(user.id, role='email_change')} 
            )

    proto = {"user_id":user.id, "trmnt_id":trmt_id, "title":title, "body":body, "update":user.result_update}
    print('Proto:', proto)

    if users_to_notify == []:
        users_to_notify.append(proto)
    else:
        for objx in users_to_notify:
            print('obj', objx)
            if any(objx['user_id'] == user.id):
                print("Success!")
                index = -1
                for i, obj in enumerate(users_to_notify):
                    if obj['user_id'] == user.id:
                        index = i
                        if users_to_notify[i]['trmnt_id'] != trmt_id:
                            print("Sending to User Id:", proto['user_id'])
                            users_to_notify.append(proto)
                        else:
                            print("Same tournament")



# REMINDERS FOR SWAPS TO BE CONFIRMED (SEND ONE NOTIFICATION PER USER, PER TOURNAMENT ID)
for swap in swapsToBeConfirmed:
    user = session.query(m.Profiles).get( swap.sender_id )
    a_user = session.query(m.Profiles).get( swap.recipient_id )

    time_after_due_date = swap.paid_at - swap.due_at
    trmt_id = swap.tournament_id
    title = None
    body = None
    swap_rating = None

    #If User had failed to confirm paid swaps after 5 days
    if now >= swap.paid_at + timedelta(days=5):
        if time_after_due_date < timedelta(days=0):
            swap_rating = 5
        elif time_after_due_date < timedelta(days=2):
            swap_rating = 4
        elif time_after_due_date < timedelta(days=4):
            swap_rating = 3
        elif time_after_due_date < timedelta(days=6):
            swap_rating = 2
        elif time_after_due_date < timedelta(days=8):
            swap_rating = 1
        else:
            swap_rating = 0
        title="Swap Confirmation Auto-Completed"
        body="You Swap Rating has been updated accordingly."
        swap.confirmed = True

        # ADD TO SWAP RATINGS TO UPDATE
        if swap.swap_rating != swap_rating:
            # print(f'Updating swap rating for swap {swap.id} from {swap.swap_rating} to {swap_rating}')
            swap.swap_rating = swap_rating
            session.commit()
            users_to_update_swaprating.append(user)
        
        # ADD TO USERS TO UPDATE ( ONE PER PERSON SWAPPED WITH, PER TOURNAMENT)
        proto = {"user_id":user.id, "trmnt_id":trmt_id, "title":title, "body":body, "update":user.result_update}
        if any(obj['user_id'] == user.id for obj in users_to_notify):
            index = -1
            for i, obj in enumerate(users_to_notify):
                if obj['user_id'] == user.id:
                    index = i
                    if users_to_notify[i]['trmnt_id'] != trmt_id:
                        users_to_notify.append(proto)
                    else:
                        print("Same tournament")
    else:
        # if now < swap.paid_at + timedelta(days=2) and now > swap.paid_at + timedelta(days=1):
        if now > swap.paid_at:
            title="Confirm Swap Payment"
            body="Confirm the swap payment made to you"
        elif now > swap.paid_at + timedelta(days=4) and now < swap.paid_at + timedelta(days=5):
            title="Your Confirmation will be Autocompleted"
            body="Confirm or Dispute before 5 days have pass after being paid"
        
        # ADD TO USERS TO UPDATE ( ONE PER PERSON SWAPPED WITH, PER TOURNAMENT)
        proto = {"user_id":a_user.id, "trmnt_id":trmt_id, "title":title, "body":body, "update":user.result_update}
        print("Proto: ", proto)
        if users_to_notify == []:
            users_to_notify.append(proto)
        else:
            if any(obj['user_id'] == a_user.id for obj in users_to_notify):
                index = -1
                for i, obj in enumerate(users_to_notify):
                    if obj['user_id'] == a_user.id:
                        index = i
                        if users_to_notify[i]['trmnt_id'] != trmt_id:
                            users_to_notify.append(proto)
                        else:
                            print("Same tournament")
    

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

for a_user in users_to_notify:
    print("User being notified",a_user['user_id'], " about ", a_user['body'])
    if a_user['update'] == True:
        send_fcm(
            user_id = a_user['user_id'],
            title = a_user['title'],
            body = a_user['body'],
            data = {
                'id': a_user['trmnt_id'],
                'alert': a_user['body'],
                'type': 'result',
                'initialPath': 'Event Results',
                'finalPath': 'Swap Results'
            }
        )