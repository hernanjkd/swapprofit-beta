from flask import request, jsonify, render_template
from flask_jwt_simple import JWTManager, create_jwt, get_jwt, jwt_required
from sqlalchemy import desc, or_
from utils import APIException, role_jwt_required
from notifications import send_email
import models as m
from models import db, Profiles, Tournaments, Swaps, Flights, Buy_ins, Devices, \
    Transactions, Users
from datetime import datetime, timedelta
import requests
import seeds
import utils
import json
import os
import re
from notifications import send_email, send_fcm



def attach(app):


    @app.route('/reset_database')
    @jwt_required
    def run_seeds():

        if get_jwt()['role'] != 'admin':
            raise APIException('Access denied', 403)

        seeds.run()

        lou = Profiles.query.filter_by(nickname='Lou').first()

        return jsonify({
            "1 Lou's id": lou.id,
            "2 token_data": {
                "id": lou.id,
                "role": "admin",
                "exp": 600000
            },
            "3 token": create_jwt({
                    'id': lou.id,
                    'role': 'admin',
                    'exp': 600000
                })
        })




    @app.route('/create/token', methods=['POST'])
    def create_token():
        return jsonify( create_jwt(request.get_json()) ), 200

    @app.route('/tournaments/onTime')
    def check_tournaments():
       # Update from days ago or hours ago, default to 1 hour ago
        span = request.args.get('span') # days, hours
        amount = request.args.get('amount')

        if None not in [span, amount]:
            args = f'?span={span}&amount={amount}'
        else: args = ''

        resp = requests.get( 
            f"{os.environ['POKERSOCIETY_HOST']}/swapprofit/update{args}" )
        if not resp.ok:
            raise APIException( resp.content.decode("utf-8")[-233:] , 500)

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

        trmnts = db.session.query(m.Tournaments) \
            .filter( m.Tournaments.status == 'open') \
            .filter( m.Tournaments.flights.any(
                m.Flights.start_at < close_time
            ))
        print('trmts', db.session.query(m.Tournaments).filter( m.Tournaments.status == 'open'))
        for trmnt in trmnts:
            latest_flight = trmnt.flights.pop()
            if latest_flight.start_at < close_time:
                    
                # This tournament is over: change status and clean swaps
                print('Update tournament status to "waiting_results", id:', trmnt.id)
                trmnt.status = 'waiting_results'
                swaps = db.session.query(m.Swaps) \
                    .filter_by( tournament_id = trmnt.id ) \
                    .filter( or_( 
                        m.Swaps.status == 'pending', 
                        m.Swaps.status == 'incoming',
                        m.Swaps.status == 'counter_incoming' ) )

                for swap in swaps:
                    print('Update swap status to "canceled", id:', swap.id)
                    swap.status = 'canceled'

                db.session.commit()

                
                # Send fcm to all players when trmnt closes
                users = get_all_players_from_trmnt( trmnt )
                for user in users:
                    buyin = m.Buy_ins.get_latest(
                        user_id=user.id, tournament_id=trmnt.id )
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
                    time = datetime.utcnow()
                    domain = os.environ['MAILGUN_DOMAIN']
                    requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
                        auth=(
                            'api',
                            os.environ.get('MAILGUN_API_KEY')),
                        data={
                            'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                            'to': ['gherndon5@gmail.com'],
                            'subject': trmnt.name + ' has just ended',
                            'text': 'Sending text email',
                            'html': f'''
                                <div>trmnt.id {trmnt.id}</div><br />
                                <div>{trmnt.start_at} trmnt.start_at</div>
                                <div>{time} datetime.utcnow()</div>
                                
                            '''
                        })

        ###############################################################################
        # Send fcm to all players when trmnt opens

        _4mins_ago = datetime.utcnow() - timedelta(minutes=4)
        _4mins_ahead = datetime.utcnow() + timedelta(minutes=4)

        trmnts = db.session.query(m.Tournaments) \
            .filter( m.Tournaments.start_at < _4mins_ahead) \
            .filter( m.Tournaments.start_at > _4mins_ago )

        for trmnt in trmnts:
            print('Tournament just started with id: ', trmnt.id)

            users = get_all_players_from_trmnt( trmnt )
            for user in users:
                buyin = m.Buy_ins.get_latest(
                    user_id=user.id, tournament_id=trmnt.id )
                print('Sending notification that trmnt started to user, id: ', user.id, user.event_update)
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
            time=datetime.utcnow()
            # LOG            
            domain = os.environ['MAILGUN_DOMAIN']
            requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
                auth=(
                    'api',
                    os.environ.get('MAILGUN_API_KEY')),
                data={
                    'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                    'to': ['gherndon5@gmail.com'],
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



        ###############################################################################
        # Delete buy-ins created before close time with status 'pending'

        buyins = db.session.query(m.Buy_ins) \
            .filter_by( status = 'pending' ) \
            .filter( m.Buy_ins.flight.has( m.Flights.start_at < close_time ))

        for buyin in buyins:
            print('Deleting buy-in', buyin.id)
            db.session.delete(buyin)

        db.session.commit()

        swaps = db.session.query(m.Swaps) \
            .filter( m.Swaps.due_at != None ) \
            .filter( m.Swaps.paid == False )

        now = datetime.utcnow()
        users_to_update_swaprating = []

        for swap in swaps:
            user = db.session.query(m.Profiles).get( swap.sender_id )
            time_after_due_date = now - swap.due_at
            trmt_id = swap.tournament_id
            if swap.due_at > now:
                swap_rating = 5
                if user.result_update is True:
                    send_fcm(
                        user_id = user.id,
                        title = "5 Star",
                        body = "Yee",
                        data = {
                            'id': trmt_id,
                            'alert': "Yess",
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
                            'finalPath': 'Swap Results' }
                    )
            elif time_after_due_date < timedelta(days=14):
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
                        'finalPath': 'Swap Results' }
                )

            # Suspend account
            else:
                swap_rating = 0
                user_account = db.session.query(m.Users).get( user.id )
                user_account.naughty = True
                print('Put on naughty list', user.id)
                db.session.commit()
                send_fcm(
                    user_id = user.id,
                    title = "Account Suspension",
                    body = "You're account has been suspended until you've paid the swaps you owe",
                    data = {
                        'id': trmt_id,
                        'alert': "You're account has been suspended until you've paid the swaps you owe",
                        'type': 'result',
                        'initialPath': 'Event Results',
                        'finalPath': 'Swap Results' }
                )
                

            if swap.swap_rating != swap_rating:
                print(f'Updating swap rating for swap {swap.id} from {swap.swap_rating} to {swap_rating}')
                swap.swap_rating = swap_rating
                db.session.commit()
                
                users_to_update_swaprating.append(user)


        # Helper function to calculate the swap rating, used below
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
            print(f'Updating swap rating for user {user.id} to {user.swap_rating}')
            db.session.commit()
    
        return 'Tournaments checked successfully'
    

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
            raise APIException( resp.content.decode("utf-8")[-233:] , 500)


        data = resp.json()
        for d in data:

            # TOURNAMENTS
            trmntjson = d['tournament']
            trmnt = Tournaments.query.get( trmntjson['id'] )
            if trmnt is None:
                print(f'Adding trmnt id: {trmntjson["id"]}')
                db.session.add( Tournaments(
                    **{col:val for col,val in trmntjson.items()} ))
            else:
                print(f'Updating trmnt id: {trmntjson["id"]}')
                for col,val in trmntjson.items():
                    if getattr(trmnt, col) != val:
                        setattr(trmnt, col, val)
                
            # FLIGHTS
            for flightjson in d['flights']:
                flight = Flights.query.get( flightjson['id'] )
                if flight is None:
                    print(f'Adding flight id: {flightjson["id"]}')
                    db.session.add( Flights(
                        **{col:val for col,val in flightjson.items()} ))
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
            return jsonify({'error':'API Token does not match'})
        
        
        trmnt = Tournaments.query.get( r['tournament_id'] )
        if trmnt is None:
            return jsonify(
                {'error':'Tournament not found with id: '+ r['tournament_id']})

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
                    'winnings': None
                }
        
        
        # Variable to set swap due date
        due_date = datetime.utcnow() + timedelta(days=2)


        # Process each player's data.. update roi and swap rating.. send email
        for email, userdata in r['users'].items():
            
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

            
            for swap in all_agreed_swaps:
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
                regex = re.search( r'\$\s*(\d+)', r['tournament_buyin'] )
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


            # Update user and buy ins
            user.roi_rating = user.calculate_roi_rating()
            
            buyin = Buy_ins.get_latest( user.id, trmnt.id )
            buyin.place = userdata['place']
            buyin.winnings = userdata['winnings']


            db.session.commit()

            
            sign = '-' if total_swap_earnings < 0 else '+'
            s = 's' if total_amount_of_swaps > 1 else ''
            
            send_email('swap_results',['gherndon5@gmail.com'], #'loustadler@hotmail.com','a@4geeksacademy.com'],
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



    # 
    @app.route('/profiles/naughty/yes/<int:user_id>', methods=['PUT'])
    def naughty_list_add(user_id):
        prof = Profiles.query.get(user_id)
        prof['naughty'] = True
        db.session.commit()

        return jsonify(prof.serialize())

    @app.route('/profiles/naughty/no/<int:user_id>', methods=['PUT'])
    def naughty_list_minus(user_id):
        prof = Profiles.query.get(user_id)
        prof['naughty'] = False
        db.session.commit()

        return jsonify(prof.serialize()) 

    @app.route('/users/<int:id>/devices')
    def get_user_device(id):

        devices = Devices.query.filter_by( user_id = id )
        if devices.count() == 0:
            raise APIException('No devices registered for this user')

        return jsonify([x.serialize() for x in devices])




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
        if r['api_token'] != utils.sha256( os.environ['POKERSOCIETY_API_TOKEN'] ):
            return jsonify({'error':'API token does not match'})        

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
                'ID (poker society)': user.pokersociety_id }
            if swap.status._value_ == 'agreed':
                if data not in users:
                    users.append(data)


        return jsonify(users)


    return app