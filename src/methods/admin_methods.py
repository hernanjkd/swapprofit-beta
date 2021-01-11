from flask import ( Flask, request, jsonify, render_template, send_file, \
    make_response, redirect )
from flask_jwt_simple import JWTManager, create_jwt, decode_jwt, get_jwt, jwt_required
from sqlalchemy import desc, or_
import jwt
from utils import APIException, role_jwt_required
from notifications import send_email, send_fcm
import models as m
from models import db, Profiles, Tournaments, Swaps, Flights, Buy_ins, Devices, \
    Transactions, Users, Casinos
import pandas as pd
import actions
from datetime import datetime, timedelta
import requests
import seeds
import utils
import json
import os
import re
import pytz



def attach(app):


    @app.route('/reset_database')
    @role_jwt_required(['admin'])
    def run_seeds(user_id, **kwargs):

        print(get_jwt())

        if get_jwt()['role'] != 'admin':
            raise APIException('Access denied', 403)

        seeds.run()

        gabe = Profiles.query.filter_by(first_name='Gabriel').first()

        now = datetime.utcnow()
        # x['iat'] = now
        # x['nbf'] = now
        # x['sub'] = gabe.id
        # x['exp'] = now + timedelta(days=365)

        identity = {
            "id": gabe.id,
            "role": "admin",
            'sub': gabe.id,
            "exp": now + timedelta(days=365),
            'iat': now,
            'nbf': now
        }

        

        xx = jwt.encode(identity, os.environ['JWT_SECRET_KEY'], algorithm='HS256')

        print('x')

        return jsonify({
            "1 Gabe's id": gabe.id,
            "2 token_data": identity,
            "3 token": xx
        }, 200)


    @app.route('/create/token', methods=['POST'])
    def create_token():
        print('it is',request.get_json())

        x = request.get_json()
        now = datetime.utcnow()
        x['iat'] = now
        x['nbf'] = now
        x['sub'] = x['id']
        x['exp'] = now + timedelta(days=365)
        print(x)
        
        return jsonify( jwt.encode(x, os.environ['JWT_SECRET_KEY'], algorithm='HS256') ), 200


    @app.route('/tournaments/schedueler')
    def check_tournaments():

        def get_all_players_from_trmnt(trmnte):
            the_users = []
            for flight in trmnte.flights:
                for a_buyin in flight.buy_ins:
                    if a_buyin.user not in the_users: # no repeats
                        the_users.append( a_buyin.user )
            return the_users

        close_time = utils.designated_trmnt_close_time()

        # any tournaments that are open and latest flight start at isnt later close_time
        trmnts = db.session.query(m.Tournaments) \
            .filter( m.Tournaments.status == 'open') \
            .filter( m.Tournaments.flights.any(
                m.Flights.start_at < close_time
            ))

        if trmnts is not None:
            for trmnt in trmnts:
                latest_flight = trmnt.flights[-1]
                print(latest_flight.start_at.strftime("%c"))
                start_time = latest_flight.start_at + timedelta(hours=17)
                # lastTime = start_time.strftime("%b. %d %I:%M %p")
                if latest_flight.start_at < close_time:
                    # This tournament is over: change status and clean swaps
                    trmnt.status = 'waiting_results' 
                    swaps = db.session.query(Swaps) \
                        .filter( Swaps.tournament_id == trmnt.id ) \
                        .filter( or_(
                            Swaps.status == 'pending',
                            Swaps.status == 'incoming',
                            Swaps.status == 'counter_incoming' ) )

                    if swaps is not None:
                        for swap in swaps:
                            print('Update swap status to "canceled", id:', swap.id)
                            swap.status = 'canceled'
                        db.session.commit()

                    eww = db.session.query(m.Tournaments).get(trmnt.id)


                    users = get_all_players_from_trmnt(eww)

                    print('Update tournament status to "waiting_results", id:', trmnt.id)
                    # buyin = m.Buy_ins.get_latest(user_id=user.id, tournament_id=trmnt.id )


        ###############################################################################
        # Send fcm to all players when trmnt opens

        _5mins_ago = datetime.utcnow() - timedelta(minutes=5)
        _5mins_ahead = datetime.utcnow() + timedelta(minutes=5)

        trmnts = db.session.query(m.Tournaments) \
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

                    my_buyin = db.session.query(m.Buy_ins) \
                        .filter( Buy_ins.flight.has( tournament_id=trmnt.id )) \
                        .filter( m.Buy_ins.user_id==user.id ) \
                        .order_by( m.Buy_ins.id.desc() ).first()
        
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
                                'buyin_id': my_buyin.id,
                                'type': 'event',
                                'initialPath': 'Event Listings',
                                'finalPath': 'Event Lobby'
                            }
                        )

        ###############################################################################
        # Delete buy-ins created before close time with status 'pending'

        buyins = db.session.query(m.Buy_ins) \
            .filter_by( status = 'pending' ) \
            .filter( m.Buy_ins.flight.has( m.Flights.start_at < close_time ))

        for buyin in buyins:
            print('Deleting buy-in', buyin.id)
            db.session.delete(buyin)

        db.session.commit()

        return 'Tournaments updated are on time'
    
    @app.route('/swaps/schedueler')
    def check_swaps():
        swapsToBePaid = db.session.query(m.Swaps) \
            .filter( Swaps.due_at != None ) \
            .filter( Swaps.paid == False )

        swapsToBeConfirmed = db.session.query(m.Swaps) \
            .filter( m.Swaps.due_at != None ) \
            .filter( m.Swaps.paid == True ) \
            .filter(m.Swaps.confirmed == False) \
            .filter(m.Swaps.disputed == False)

        now = datetime.utcnow()
        users_to_update_swaprating = []
        users_to_notify = []

        # REMINDERS FOR SWAPS TO BE PAID (SEND ONE NOTIFICATION PER USER, PER TOURNAMENT ID)
        for swap in swapsToBePaid:
            user = db.session.query(m.Profiles).get( swap.sender_id )
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
                # domain = os.environ['MAILGUN_DOMAIN']
                # requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
                #     auth=(
                #         'api',
                #         os.environ.get('MAILGUN_API_KEY')),
                #     data={
                #         'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                #         'to': user.user.email,
                #         'subject': 'You are in Danger of being Suspended',
                #         'text': 'Sending text email',
                #         'html': f'''
                #             <div>trmnt.id {trmnt.id}</div><br />
                #             <div>{trmnt.start_at} trmnt.start_at</div>
                #             <div>{time} datetime.utcnow()</div>
                #             <div>{_5mins_ago} _4mins_ago</div>
                #             <div>{_5mins_ahead} _4mins_ahead</div>
                #         '''
                # })
                
            # Suspend account
            else:
                title="Account Suspension"
                body="You're account has been suspended until you pay your swaps"
                swap_rating = 0
                # user_account = session.query(m.Users).get( user.id )
                user.naughty = True
                print('Put on naughty list', user, user.id, user.naughty)
                db.session.commit()
                send_email( template='account_suspension', emails=user.email, 
                    # data={'validation_link': utils.jwt_link(user.id, role='email_change')} 
                    )
            proto = {"user_id":user.id, "trmnt_id":trmt_id, "title":title, "body":body, "update":user.result_update}
            print('Proto:', proto)

            if users_to_notify == []:
                users_to_notify.append(proto)
            else:
                for obj in users_to_notify:
                    print('obj', obj)
                    if any(obj['user_id'] == user.id):
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
            user = db.session.query(m.Profiles).get( swap.sender_id )
            a_user = db.session.query(m.Profiles).get( swap.recipient_id )

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
                    db.session.commit()
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
            swaps = db.session.query(m.Swaps) \
                .filter_by( sender_id=user_id ) \
                .filter( m.Swaps.due_at != None )
            total_swap_ratings = 0
            for swap in swaps:
                total_swap_ratings += swap.swap_rating
            return total_swap_ratings / swaps.count()

        for user in users_to_update_swaprating:
            user.swap_rating = calculate_swap_rating( user.id )
            # print(f'Updating swap rating for user {user.id} to {user.swap_rating}')
            db.session.commit()

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
        return "Swappers notified Successfully"

    @app.route('/tournaments/update')
    def update_tournaments():

        # Update from days ago or hours ago, default to 1 hour ago
        span = request.args.get('span') # days, hours
        amount = request.args.get('amount')

        if None not in [span, amount]:
            args = f'?span={span}&amount={amount}'
        else: args = ''

        resp = requests.get( 
            f"{os.environ['POKERSOCIETY_HOST']}/swapprofit/update{args}" )
        if not resp.ok:
            raise APIException( resp.content , 500)


        data = resp.json()

        for d in data[0]: 
        
            print('d', d)

            # CASINOS - ADD/UPDATE
            casinojson = d['casino']
            csno = Casinos.query.get( casinojson['id'] )

            
            # CASINO Update
            if csno is None:
                print(f'Adding csno id: {casinojson["id"]}')
                db.session.add( m.Casinos(
                    **{col:val for col,val in casinojson.items()} ))
            else:
                print(f'Updating csno id: {casinojson["id"]}')
                for col,val in casinojson.items():
                    if getattr(csno, col) != val:
                        setattr(csno, col, val)

        for d in data[1]: 
            # TOURNAMENTS - ADD/UPDATE
            trmntjson = d['tournament']
            trmnt = Tournaments.query.get( trmntjson['id'] )
            print('LISTEN', trmnt)
            x = {col:val for col,val in trmntjson.items()}
            # ADD TOURNAMENT
            if trmnt is None:
                print(f'Adding trmnt id: {trmntjson["id"]}')
                db.session.add( Tournaments( **trmntjson ))
            
            # UPDATE TOURNAMENT
            else:
                print(f'Updating trmnt id: {trmntjson["id"]}')
                for col,val in trmntjson.items():
                    if getattr(trmnt, col) != val:
                        setattr(trmnt, col, val)
                
            # FLIGHTS - ADD/UPDATE
            for flightjson in d['flights']:
                flight = Flights.query.get( flightjson['id'] )
                
                # ADD FLIGHT
                if flight is None:
                    print(f'Adding flight id: {flightjson["id"]}')
                    db.session.add( Flights(
                        **{col:val for col,val in flightjson.items()} ))
                
                # UPDATE FLIGHT
                else:
                    print(f'Updating flight id: {flightjson["id"]}')
                    for col,val in flightjson.items():
                        if getattr(flight, col) != val:
                            setattr(flight, col, val)

            db.session.commit()

        return 'Tournaments updated successfully'



    @app.route('/tournaments', methods=['POST'])
    def add_tournaments():

        return 'endpoint dissabled'

        # casino cache so not to request for same casinos
        path_cache = os.environ['APP_PATH'] + '/src/jsons/tournaments.json'
        if os.path.exists( path_cache ):
            with open( path_cache ) as f:
                cache = json.load( f )
        else: cache = {}


        # data comes in as a string
        data = json.loads( request.get_json() )

        for r in data:
            
            # Do not add these to Swap Profit
            if r['Tournament'].strip() == '' or \
            'satelite' in r['Tournament'].lower() or \
            r['Results Link'] == False:
                continue


            trmnt = Tournaments.query.get( r['Tournament ID'] )
            trmnt_name, flight_day = utils.resolve_name_day( r['Tournament'] )
            start_at = datetime.strptime(
                r['Date'][:10] + r['Time'], 
                '%Y-%m-%d%H:%M:%S' )


            trmntjson = { 
                'id': r['Tournament ID'],
                'name': trmnt_name, 
                'start_at': start_at,
                'results_link': str( r['Results Link'] ).strip()
            }
            flightjson = {
                'start_at':start_at,
                'day': flight_day
            }


            if trmnt is None:

                casino = cache.get( r['Casino ID'] )
                
                if casino is None:
                    rsp = requests.get( 
                        f"{os.environ['POKERSOCIETY_HOST']}/casinos/{r['Casino ID']}" )
                    if not rsp.ok:
                        raise APIException(f'Casino with id "{r["Casino ID"]}" not found', 404)               
                    
                    casino = rsp.json()
                    cache[ r['Casino ID'] ] = casino
                    print('casino', casino)

                trmntjson = {
                    **trmntjson,
                    'address': casino['address'].strip,
                    'city': casino['city'].strip,
                    'state': casino['state'].strip,
                    'zip_code': str( casino['zip_code'] ).strip,
                    'longitude': float( casino['longitude'] ),
                    'latitude': float( casino['latitude'] )
                }


                # Create tournament
                trmnt = Tournaments( **trmntjson )
                db.session.add( trmnt )
                db.session.flush()
                
                # Create flight
                db.session.add( Flights(
                    tournament_id=trmnt.id, 
                    **flightjson
                ))

            else:
                # Update tournament
                for db_col, val in trmntjson.items():
                    if db_col != 'start_at':
                        if getattr(trmnt, db_col) != val:
                            setattr(trmnt, db_col, val)

                flight = Flights.query.filter_by( tournament_id=trmnt.id ) \
                    .filter( or_( Flights.day == flight_day, Flights.start_at == start_at )) \
                    .first()

                # Create flight
                if flight is None:
                    db.session.add( Flights( 
                        tournament_id=trmnt.id,
                        **flightjson
                    ))
                
                # Update flight
                else:
                    for db_col, val in flightjson.items():
                        if getattr(flight, db_col) != val:
                            setattr(flight, db_col, val)

        db.session.commit()

        # Save cache
        if cache != {}:
            with open( path_cache, 'w' ) as f:
                json.dump( cache, f, indent=2 )

        return jsonify({'message':'Tournaments have been updated'}), 200


    @app.route('/results/update', methods=['POST'])
    def get_results():
        '''
            {
                "api_token": "oidf8wy373apudk",
                "tournament_id": 45,
                "tournament_buyin": 150,
                "users": {
                    "sdfoij@yahoo.com": {
                        "place": 11,
                        "winnings": 200
                    }
                }
            }
        '''

        r  = request.get_json()

        # Security token check
        if r['api_token'] != utils.sha256( os.environ['POKERSOCIETY_API_TOKEN'] ):
            return jsonify({'error':r['api_token']})
        
        # print('Buyin ID', r['tournament_buyin'])
        trmnt = Tournaments.query.get( r['tournament_id'] )
        if trmnt is None:
            return jsonify(
                {'error':'Tournament not found with id: '+ r['tournament_id']})

        trmnt_buyin = r['tournament_buyin'] 
        trmnt.results_link = (os.environ['POKERSOCIETY_HOST'] + 
            '/results/tournament/' + str(r['tournament_id']))

        # Add all players that haven't won but have swaps in this trmnt
        all_swaps_in_trmnt = Swaps.query.filter_by( tournament_id=trmnt.id ) \
                                        .filter_by( status='agreed' )

        for swap in all_swaps_in_trmnt:
            email = swap.sender_user.user.email
            if email not in r['users']:
                r['users'][email] = {
                    'place': None,
                    'winnings': None,
                }
        
        
        # Variable to set swap due date
        due_date = datetime.utcnow() + timedelta(days=4)


        # Process each player's data.. update roi and swap rating.. send email
        for email, userdata in r['users'].items():
            print('userdata', userdata)
            user = Profiles.query.filter( 
                Profiles.user.has( email=email )).first()
            if user is None:
                return jsonify(
                    {'error':'User not found with email: '+ email})
            
            # Consolidate swaps if multiple with same user
            all_agreed_swaps = user.get_agreed_swaps( r['tournament_id'] )
            swaps = {}
            
            # If user has no swaps, don't send email
            if len(all_agreed_swaps) == 0:
                continue

            print(all_agreed_swaps[0])
            for swap in all_agreed_swaps:
                print("SWAP IS", swap)
                '''
                    {
                        "2": {
                            "count": 2,
                            "counter_percentage": 11,
                            "percentage": 11,
                            "recipient_email": "katz234@gmail.com"
                        },
                        "4": {
                            "count": 1,
                            "counter_percentage": 7,
                            "percentage": 5,
                            "recipient_email": "mikitapoker@gmail.com"
                        }
                    }
                '''
                id = str( swap.recipient_id )
                if id not in swaps:
                    swaps[id] = {
                        'count': 1,
                        'percentage': swap.percentage,
                        'counter_percentage': swap.counter_swap.percentage,
                        'recipient_email': swap.recipient_user.user.email
                    }
                else:
                    swaps[id]['count'] += 1
                    swaps[id]['percentage'] += swap.percentage
                    swaps[id]['counter_percentage'] += swap.counter_swap.percentage
                
                # Set payment due date, swap_rating and result_winnings for each swap
                swap.due_at = due_date
                swap.swap_rating = 5
                swap.result_winnings = True if userdata['winnings'] != None else False
                
            
            db.session.commit()

            total_swap_earnings = 0
            total_amount_of_swaps = 0
            render_swaps = []

            # Go thru the consolidated swaps to create the email templates
            for recipient_id, swapdata in swaps.items():

                recipient = Profiles.query.get( recipient_id )
                if recipient is None:
                    return jsonify(
                        {'error':'User not found with id: '+ recipient_id})


                # Tournament buyin could be "$200" "$0++" "Day 2"
                regex = re.search( r'\$\s*(\d+)', str(trmnt_buyin) )
                entry_fee = int( regex.group(1) ) if regex else 0

                # Winnings are integers, but in case they are a string, ex "Satellite"
                to_int = lambda x: x if isinstance(x, int) else 0
                
                profit_sender = to_int( userdata['winnings'] ) - entry_fee
                amount_owed_sender = profit_sender * swapdata['percentage'] / 100                
                
                # recipient_winnings can be None
                recipient_winnings = r['users'][ swapdata['recipient_email'] ]['winnings'] or 0
                profit_recipient = to_int( recipient_winnings ) - entry_fee
                amount_owed_recipient = profit_recipient * swapdata['counter_percentage'] / 100


                render_swaps.append({
                    'amount_of_swaps': swapdata['count'],
                    'entry_fee': entry_fee,
                    
                    'sender_first_name': user.first_name,
                    'total_earnings_sender': '{:,}'.format( userdata['winnings'] ),
                    'swap_percentage_sender': swapdata['percentage'],
                    'swap_profit_sender': '{:,}'.format( profit_sender ),
                    'amount_owed_sender': '{:,}'.format( round(amount_owed_sender) ),

                    'recipient_first_name': recipient.first_name,
                    'recipient_last_name': recipient.last_name,
                    'recipient_profile_pic_url': recipient.profile_pic_url,
                    'total_earnings_recipient': '{:,}'.format( recipient_winnings ),
                    'swap_percentage_recipient': swapdata['counter_percentage'],
                    'swap_profit_recipient': '{:,}'.format( profit_recipient ),
                    'amount_owed_recipient': '{:,}'.format( round(amount_owed_recipient) )
                })
                
                total_swap_earnings -= amount_owed_sender
                total_swap_earnings += amount_owed_recipient
                total_amount_of_swaps += swapdata['count']

            if total_swap_earnings >= 0:
                for swap in all_agreed_swaps:
                    a_swap = Swaps.query.get( swap.id )
                    a_swap.paid = True
                    a_swap.paid_at = datetime.utcnow()
                    a_swap.confirmed = True
                    a_swap.confirmed_at = datetime.utcnow()

            # Update user and buy ins
            user.roi_rating = user.calculate_roi_rating()
            
            buyin = Buy_ins.get_latest( user.id, trmnt.id )
            buyin.place = userdata['place']
            buyin.winnings = userdata['winnings']


            db.session.commit()

            
            sign = '-' if total_swap_earnings < 0 else '+'
            s = 's' if total_amount_of_swaps > 1 else ''
            # print('coming in')
            a_user = Profiles.query.get(user.id)
            # print('isr esult update true', a_user.result_update, user.id)
            if a_user.result_update == True:
                send_fcm(
                    user_id = user.id,
                    title = "Results Posted",
                    body = trmnt.name + " posted their results.",
                    data = {
                        'id': trmnt.id,
                        'alert': trmnt.name + " just posted their results.",
                        'type': 'result',
                        'initialPath': 'Event Results',
                        'finalPath': 'Swap Results'
                    }
        )

            send_email('swap_results',[email], #'loustadler@hotmail.com','a@4geeksacademy.com'],
                data={
                    'tournament_date': trmnt.start_at.strftime( '%A, %B %d, %Y - %I:%M %p' ),
                    'tournament_name': trmnt.name,
                    'results_link': trmnt.results_link,
                    'total_swaps': f"{total_amount_of_swaps} swap{s}",
                    'total_swappers': f"{len(swaps)} {'person' if len(swaps) == 1 else 'people'}",
                    'total_swap_earnings': f'{sign}${"{:,.2f}".format( abs(total_swap_earnings) )}',
                    'render_swaps': render_swaps,
                    'roi_rating': round( user.roi_rating ),
                    'swap_rating': round( user.swap_rating, 1 )
                })

            


        trmnt.status = 'closed'
        db.session.commit()

        return jsonify({'message':'Results processed successfully'}), 200

    
    @app.route('/profiles/naughty/yes/<int:user_id>', methods=['PUT'])
    def naughty_list_add(user_id):
        prof = Profiles.query.get(user_id)
        print("PROFILE IS", prof)
        prof.naughty = True
        db.session.commit()

        return jsonify(prof.serialize())


    @app.route('/profiles/naughty/no/<int:user_id>', methods=['PUT'])
    def naughty_list_minus(user_id):
        prof = Profiles.query.get(user_id)
        prof.naughty = False
        db.session.commit()

        return jsonify(prof.serialize())


    @app.route('/', methods=['GET','POST'])
    @app.route('/users/login', methods=['GET','POST'])
    def login_admin():
        
        if request.method == 'GET':
            return render_template('login.html',
                host=os.environ.get('API_HOST'))

        json = request.get_json()
        utils.check_params(json, 'email', 'password')

        user = Users.query.filter_by( 
            email = json['email'],
            password = utils.sha256( json['password'] )
        ).first()
        
        if user is None:
            return jsonify({
                'login': False,
                'message':'Email and password are incorrect',
            })

        identity = {'id':user.id, 'role':'admin', 'sub':user.id}
        
        return jsonify({
            'login': True,
            'jwt': jwt.encode(identity, os.environ['JWT_SECRET_KEY'], algorithm='HS256')
        })

    ################ DEVICE REQUESTS ###################

    # GET USER DEVICE
    @app.route('/users/<int:id>/devices')
    def get_user_device(id):

        devices = Devices.query.filter_by( user_id = id )
        if devices.count() == 0:
            raise APIException('No devices registered for this user')

        return jsonify([x.serialize() for x in devices])


    # ADD USER DEVICE
    @app.route('/users/me/devices', methods=['POST'])
    @role_jwt_required(['user'])
    def add_device(user_id):
        req = request.get_json()
        utils.check_params(req, 'device_token')
        db.session.add(Devices(
            user_id = user_id,
            token = req['device_token'] ))
        db.session.commit()
        return jsonify({'message':'Device added successfully'})


    # DELETE USER DEVICE
    @app.route('/users/me/devices', methods=['DELETE'])
    @role_jwt_required(['user'])
    def delete_device(user_id):
        
        req = request.get_json()
        utils.check_params(req, 'device_token')
        
        devices = Devices.query.filter_by( token=req['device_token'] )
        for device in devices:
            db.session.delete( device )
            db.session.commit()
        
        return jsonify({'message':'Device deleted successfully'})




    @app.route('/tournaments', methods=['POST'])
    def add_tournament():
        req = request.get_json()
        db.session.add(Tournaments(
            name = req['name'],
            address = req['address'],
            start_at = datetime( *req['start_at'] ),
            end_at = datetime( *req['end_at'] ),
            longitude = None,
            latitude = None
        ))
        db.session.commit()
        search = {
            'name': req['name'],
            'start_at': datetime( *req['start_at'] )
        }
        return jsonify(Tournaments.query.filter_by(**search).first().serialize()), 200




    @app.route('/flights/<int:id>')
    def get_flights(id):
        if id == 'all':
            return jsonify([x.serialize() for x in Flights.query.all()])

        if id.isnumeric():
            flight = Flights.query.get(int(id))
            if flight is None:
                raise APIException('Flight not found', 404)
            return jsonify(flight.serialize())
        
        return jsonify({'message':'Invalid id'})




    @app.route('/flights', methods=['POST'])
    def create_flight():
        req = request.get_json()
        db.session.add(Flights(
            tournament_id = req['tournament_id'],
            start_at = datetime( *req['start_at'] ),
            end_at = datetime( *req['end_at'] ),
            day = req['day']
        ))
        db.session.commit()
        search = {
            'tournament_id': req['tournament_id'],
            'start_at': datetime(*req['start_at']),
            'end_at': datetime(*req['end_at']),
            'day': req['day']
        }
        return jsonify(Flights.query.filter_by(**search).first().serialize()), 200



    @app.route('/swaps/<int:id>')
    def get_swaps_tool(id):
        swap = Swaps.query.get( id )
        if swap is None:
            raise APIException('Swap not found', 404)
        return jsonify(swap.serialize())




    @app.route('/buy_ins/<id>')
    def get_buyins(id):
        if id == 'all':
            return jsonify([x.serialize() for x in Buy_ins.query.all()])
        return jsonify(Buy_ins.query.get(int(id)).serialize())




    @app.route('/buy_ins/<int:id>', methods=['PUT'])
    def update_buyins_tool(id):
        buyin = Buy_ins.query.get(id)
        r = request.get_json()
        buyin.place = r.get('place')
        buyin.winnings = r.get('winnings')
        db.session.commit()
        return jsonify({**buyin.serialize(),'winnings':buyin.winnings})




    @app.route('/flights/<int:id>', methods=['DELETE'])
    @role_jwt_required(['admin'])
    def delete_flight(id, **kwargs):
        db.session.delete( Flights.query.get(id) )
        db.session.commit()
        return jsonify({'message':'Flight deleted'}), 200




    @app.route('/tournaments/<int:id>', methods=['DELETE'])
    @role_jwt_required(['admin'])
    def delete_tournament(id, **kwargs):
        db.session.delete( Tournaments.query.get(id) )
        db.session.commit()
        return jsonify({'message':'Tournament deleted'}), 200




    @app.route('/buy_ins/<int:id>', methods=['DELETE'])
    @role_jwt_required(['admin'])
    def delete_buy_in(id, **kwargs):
        db.session.delete( Buy_ins.query.get(id) )
        db.session.commit()
        return jsonify({'message':'Buy in deleted'}), 200




    @app.route('/swaps', methods=['DELETE'])
    @role_jwt_required(['admin'])
    def delete_swap(**kwargs):
        req = request.get_json()
        db.session.delete( Swaps.query.get(req['sender_id'], req['recipient_id'], req['tournament_id']) )
        db.session.commit()
        return jsonify({'message':'Swap deleted'}), 200




    @app.route('/swaps/all', methods=['GET'])
    @role_jwt_required(['admin'])
    def get_swaps(**kwargs):
        
        return jsonify([x.serialize() for x in Swaps.query.all()])




    @app.route('/transactions/users/<int:id>', methods=['POST'])
    @role_jwt_required(['admin'])
    def handle_transactions(id, **kwargs):

        req = request.get_json()
        utils.check_params(req, 'coins')

        db.session.add( Transactions(
            user_id = id,
            coins = req['coins'],
            dollars = req.get('dollars', 0)
        ))

        db.session.commit()

        user = Profiles.query.get( id )
        return jsonify({ 'total_coins': user.get_coins() })



    # Endpoint to get the player ids that have swaps in the trmnt
    @app.route('/users/tournament/<int:id>', methods=['POST'])
    def get_all_users_in_trmnt(id):
        
        r  = request.get_json()

        # Security token check
        # if r['api_token'] != utils.sha256( os.environ['POKERSOCIETY_API_TOKEN'] ):
        #     return jsonify({'error':'API token does not match'})        

        trmnt = Tournaments.query.get( id )
        if trmnt is None:
            return jsonify({'error':'Tournament not found with id: '+str(id)})

        trmnt_data = {
            'tournament name': trmnt.name,
            'casino': trmnt.casino,
            'start date': trmnt.start_at }

        users = [ trmnt_data ]

        for swap in trmnt.swaps:
            user = swap.sender_user
            data = {
                'email': user.user.email,
                'first name': user.first_name,
                'last name': user.last_name,
                # 'ID (poker society)': user.pokersociety_id 
                }
            if swap.status._value_ == 'agreed':
                if data not in users:
                    users.append(data)


        return jsonify(users)


    return app