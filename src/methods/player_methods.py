import os
import json
import regex
import utils
import actions
import requests
import cloudinary
import cloudinary.uploader
from google.cloud import vision
from functools import cmp_to_key
from datetime import datetime, timedelta
from flask import request, jsonify, render_template
from flask_jwt_simple import create_jwt, decode_jwt, get_jwt
from sqlalchemy import desc, asc, or_
from utils import APIException, role_jwt_required, isfloat, \
    hours_to_close_tournament
from models import (db, Users, Profiles, Tournaments, Swaps, Flights, 
    Buy_ins, Transactions, Devices, Chats, Messages)
from notifications import send_email, send_fcm


def attach(app):
    
    # UPDATE EMAIL
    @app.route('/users/me/email', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_email(user_id):
        
        req = request.get_json()
        utils.check_params(req, 'email', 'password', 'new_email')

        if req['email'] == req['new_email']:
            return jsonify({'message':'Your email is already '+req['new_email']})

        user = Users.query.filter_by( 
            id = user_id, 
            email = req['email'], 
            password = utils.sha256(req['password']) 
        ).first()
        
        if user is None:
            raise APIException('User not found', 404)

        user.status = 'invalid'
        user.email = req['new_email']

        db.session.commit()

        send_email( template='email_validation', emails=user.email, 
            data={'validation_link': utils.jwt_link(user.id, role='email_change')} )

        return jsonify({'message': 'Please verify your new email'}), 200


    # TEMPLATE TO CREATE AND SAVE NEW PASSWORD IF FORGOTTEN
    @app.route('/users/reset_password/<token>', methods=['GET','PUT'])
    def html_reset_password(token):

        jwt_data = decode_jwt(token)
        
        # Create new password in a template
        if request.method == 'GET':
            user = Users.query.filter_by(
                id = jwt_data['sub'], 
                email = jwt_data['role']).first()
            if user is None:
                raise APIException('User not found', 404)

            return render_template('reset_password.html',
                host = os.environ.get('API_HOST'),
                token = token,
                email = jwt_data['role']
            )
        
        # Save the new password that was chosen above
        req = request.get_json()
        utils.check_params(req, 'email', 'password')

        if len( req['password'] ) < 6:
            raise APIException('Password must be at least 6 characters long')

        user = Users.query.filter_by(
            id = jwt_data['sub'],
            email = req['email']
        ).first()
        if user is None:
            raise APIException('User not found', 404)

        user.password = utils.sha256( req['password'] )

        db.session.commit()

        return jsonify({'message': 'Your password has been updated'}), 200


    # RESET PASSWORD
    @app.route('/users/me/password', methods=['PUT'])
    def reset_password():

        req = request.get_json()
        utils.check_params(req, 'email')

        # User forgot their password
        if request.args.get('forgot') == 'true':
            user = Users.query.filter_by( email=req['email'] ).first()
            if user is None:
                raise APIException('This email is not registered', 400)

            send_email('reset_password_link', emails=req['email'], 
                data={'link':utils.jwt_link(user.id, 'users/reset_password/', req['email'])})
            
            return jsonify({
                'message': 'A link has been sent to your email to reset the password'
            }), 200

        # User knows their password
        utils.check_params(req, 'password', 'new_password')

        if req['password'] == req['new_password']:
            raise APIException('Your new password is the same as the old password')
        if len( req['new_password'] ) < 6:
            raise APIException('Your new password must be at least 6 characters long')

        user = Users.query.filter_by(
            email=req['email'],
            password=utils.sha256(req['password'])
        ).first()
        if user is None:
            raise APIException('User not found', 404)

        user.password = utils.sha256(req['new_password'])

        db.session.commit()

        return jsonify({'message': 'Your password has been changed'}), 200



    @app.route('/users/invite', methods=['POST'])
    @role_jwt_required(['user'])
    def invite_users(user_id):

        req = request.get_json()
        utils.check_params(req, 'email')

        user = Users.query.get( user_id )

        send_email('invitation_email', emails=req['email'], data={
            'user_name': f'{user.first_name} {user.last_name}'
        })

        return jsonify({'message':'Invitation sent successfully'})



    # GET A PROFILE
    @app.route('/profiles/<id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_profiles(user_id, id):
        
        jwt_data = get_jwt()

        if id == 'all':
            if jwt_data['role'] != 'admin':
                raise APIException('Access denied', 403)

            return jsonify([x.serialize() for x in Profiles.query.all()]), 200

        if id == 'me':
            id = str(user_id)

        if not id.isnumeric():
            raise APIException('Invalid id: ' + id, 400)

        user = Profiles.query.get(int(id))
        if user is None:
            raise APIException('Profile not found', 404)

        return jsonify(user.serialize()), 200


    # CREATE A PROFILE
    @app.route('/profiles', methods=['POST'])
    @role_jwt_required(['user'])
    def register_profile(user_id):
        
        prof = Profiles.query.get( user_id )
        if prof is not None:
            raise APIException('A profile already exists with "id": '+str(user_id), 400)

        req = request.get_json()
        utils.check_params(req, 'first_name', 'last_name', 'device_token')

        prof_data = {
            'first_name': req['first_name'],
            'last_name': req['last_name'],
            'nickname': req.get('nickname'),
            'hendon_url': req.get('hendon_url')
        }

        # Create user at Poker Society if there is none, get back pokersociety_id
        user = Users.query.get( user_id )
        resp = requests.post( os.environ['POKERSOCIETY_HOST'] + '/swapprofit/user',
            json={
                'api_token': utils.sha256( os.environ['POKERSOCIETY_API_TOKEN'] ),
                'email': user.email,
                'password': user.password,
                **prof_data
            })

        if not resp.ok:
            raise APIException('Error creating user in Poker Society', 500)

        data = resp.json()
        
        
        db.session.add( Profiles(
            id = user_id,
            pokersociety_id = data['pokersociety_id'],
            **prof_data
        ))
        db.session.add( Devices(
            user_id = user_id,
            token = req['device_token']
        ))
        db.session.add( Transactions(
            user_id = user_id,
            coins = 5
        ))
        
        db.session.commit()


        return jsonify({'message':'ok'}), 200

         
    # UPDATE MY PROFILE
    @app.route('/profiles/me', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_profile(user_id):

        prof = Profiles.query.get(user_id)

        req = request.get_json()
        utils.check_params(req)

        utils.update_table(prof, req, ignore=['profile_pic_url','pokersociety_id',
                                                'roi_rating','swap_rating'])

        db.session.commit()

        return jsonify(prof.serialize())


    # UPDATE PROFILE PICTURE
    @app.route('/profiles/image', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_profile_image(user_id):

        user = Users.query.get(user_id)

        if 'image' not in request.files:
            raise APIException('"image" property missing on the files array', 404)

        result = cloudinary.uploader.upload(
            request.files['image'],
            public_id = 'profile' + str(user.id),
            crop = 'limit',
            width = 450,
            height = 450,
            eager = [{
                'width': 200, 'height': 200,
                'crop': 'thumb', 'gravity': 'face',
                'radius': 100
            }],
            tags = ['profile_pic']
        )

        user.profile.profile_pic_url = result['secure_url']

        db.session.commit()

        return jsonify({'profile_pic_url': result['secure_url']}), 200


    # GET MY MOST RECENT BUYIN
    @app.route('/me/buy_ins', methods=['GET'])
    @role_jwt_required(['user'])
    def get_buy_in(user_id):

        buyin = Buy_ins.query.filter_by(user_id=user_id).order_by(Buy_ins.id.desc()).first()
        if buyin is None:
            raise APIException('Buy_in not found', 404)

        return jsonify(buyin.serialize()), 200


    # CREATE BUYIN
    @app.route('/me/buy_ins/flight/<int:id>/image', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_buyin_image(user_id, id):
        
        close_time = utils.designated_trmnt_close_time()

        flight = Flights.query.get( id )

        # Comment out to be able to buy into any flight
        if flight is None or flight.start_at < close_time:
            raise APIException(
                "Cannot buy into this flight. It either has ended, or does not exist")

        buyin = Buy_ins(
            user_id = user_id,
            flight_id = id
        )
        db.session.add(buyin)
        db.session.flush()

        if 'image' not in request.files:
            raise APIException('"image" property missing in the files array', 404)
        
        
        utils.resolve_google_credentials()
        
        result = cloudinary.uploader.upload(
            request.files['image'],
            public_id = 'buyin' + str(buyin.id),
            crop = 'limit',
            width = 1000,
            height = 1000,
            tags = ['buyin_receipt',
                'user_'+ str(user_id),
                'buyin_'+ str(buyin.id)]
        )

        def terminate_buyin():
            cloudinary.uploader.destroy( 'buyin'+str(buyin.id) )
            db.session.rollback()
            raise APIException('Take another photo')

        ocr_data = utils.ocr_reading( result )
        if list(ocr_data) == []:
            terminate_buyin()
        
        regex_data = regex.hard_rock( ocr_data )
        nones = 0
        for val in regex_data.values():
            if val is None: nones += 1
        if nones > 2:
            terminate_buyin()

        if None in [regex_data['player_name'], regex_data['casino']]:
            terminate_buyin()


        #############################################
        # Verify regex data against tournament data
        
        # Check player name
        validation = {}
        user = Profiles.query.get( user_id )
        condition = user.first_name.lower() in regex_data['player_name'].lower()
        validation['first_name'] = {
            'ocr': regex_data['player_name'],
            'database': user.first_name,
            'valid': True if condition else False
        }
        condition = user.last_name.lower() in regex_data['player_name'].lower()
        validation['last_name'] = {
            'ocr': regex_data['player_name'],
            'database': user.last_name,
            'valid': True if condition else False
        }
        condition = user.nickname.lower() in regex_data['player_name'].lower()
        validation['nickname'] = {
            'ocr': regex_data['player_name'],
            'database': user.nickname,
            'valid': True if condition else False
        }
        
        # Check casino name
        trmnt_casino = flight.tournament.casino
        print()
        print(trmnt_casino)
        print()
        validation['casino'] = {
            'ocr': regex_data['casino'],
            'database': trmnt_casino,
            'valid': trmnt_casino is not None
        }
        casino_names = regex_data['casino'].split(' ')
        if trmnt_casino is not None:
            for name in casino_names:
                if name.lower() not in trmnt_casino.lower():
                    validation['casino']['valid'] = False
                    break

        # Check date
        regex_timestamp = regex_data['receipt_timestamp']
        try:
            dt = datetime.strptime(regex_timestamp, '%B %d, %Y %I:%M %p')
        except:
            dt = None
        
        valid = False
        if dt is not None:
            close = flight.start_at + hours_to_close_tournament
            if datetime.utcnow() < close:
                valid = True
        validation['datetime'] = {
            'ocr': regex_timestamp,
            'flight_start_time': flight.start_at,
            'valid': valid
        }

        buyin.receipt_img_url = result['secure_url']
        db.session.commit()

        return jsonify({
            'buyin_id': buyin.id,
            'receipt_data': regex_data,
            'validation': validation,
            'ocr_data': ocr_data
        })

        
    # UPDATE BUYIN 
    @app.route('/me/buy_ins/<int:id>', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_buy_in(user_id, id):

        req = request.get_json()
        utils.check_params(req)

        buyin = Buy_ins.query.get(id)
        if buyin is None:
            raise APIException('Buy-in not found', 404)


        buyin_status = buyin.status._value_

        if buyin_status in ['cashed', 'busted']:
            raise APIException('This buy-in can no longer be modified')

        if request.args.get('validate') == 'true':
            if buyin_status == 'pending':
                utils.check_params(req, 'chips','table','seat')

                # Update chips, table and seat
                if req['chips'] > 999999999:
                    raise APIException('Too many characters for chips')
                if len( req['table'] ) > 20:
                    raise APIException('Too many characters for table')
                if req['table'] == '':
                    raise APIException('Table can\'t be empty')
                if req['seat'] < 1:
                    raise APIException('Seat can\'t be smaller than 1')

                buyin.chips = req['chips']
                buyin.table = req['table']
                buyin.seat = req['seat']

                buyin.status = 'active'
                send_email(template='buyin_receipt', emails=buyin.user.user.email,
                    data={
                        'receipt_url': buyin.receipt_img_url,
                        'tournament_date': buyin.flight.tournament.start_at,
                        'tournament_name': buyin.flight.tournament.name
                    })

                db.session.commit()
        
                return jsonify({'buy_in': buyin.serialize()})

            elif buyin_status == 'active':
                raise APIException('Buy-in already validated')

        elif buyin_status == 'pending':
            raise APIException('This buy-in has not been validated', 406)


        # Update status
        if req.get('status') is not None:
            buyin.status = req['status']

        # Update chips, table and seat
        if req.get('chips') is not None:
            if req['chips'] > 999999999:
                raise APIException('Too many characters for chips')
            buyin.chips = req['chips']
        if req.get('table') is not None:
            if len( req['table'] ) > 20:
                raise APIException('Too many characters for table')
            buyin.table = req['table']
        if req.get('seat') is not None:
            buyin.seat = req['seat']

        db.session.commit()
        
        return jsonify({'buy_in': buyin.serialize()})


    # GET SPECIFIC TOURNAMENT
    @app.route('/tournaments/<id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_tournaments(user_id, id):
        
        # List Flights
        if id == 'all':
            
            # Order by date: ascending or descending
            order_method = None
            if request.args.get('asc') == 'true':
                order_method = Flights.start_at.asc()
            elif request.args.get('desc') == 'true':
                order_method = Flights.start_at.desc()

            # Filter past flights and order by default asc
            if request.args.get('history') == 'true':
                flights = Flights.get(history=True)
                flights = flights.order_by(
                    Flights.start_at.desc() if order_method is None else order_method )

            # Filter current and future flights and order by default desc
            else:
                flights = Flights.get(history=False)
                if flights is None:
                    return jsonify([])

                flights = flights.order_by(
                    Flights.start_at.asc() if order_method is None else order_method )

            
            # Filter by name
            name = request.args.get('name') 
            if name is not None:
                flights = flights.filter( Flights.tournament.has(
                    Tournaments.name.ilike(f'%{name}%') ))


            # Get zip code LAT LON
            zip = request.args.get('zip', '')
            if zip.isnumeric():
                path = os.environ['APP_PATH']
                with open( path + '/src/zip_codes.json' ) as zip_file:
                    data = json.load(zip_file)
                    zipcode = data.get(zip)
                    if zipcode is None:
                        raise APIException('Zipcode not in file', 500)
                    lat = zipcode['latitude']
                    lon = zipcode['longitude']

            # Get user LAT LON
            else:
                lat = request.args.get('lat', '')
                lon = request.args.get('lon', '')
            
            # Order flights by distance, whithin the day
            if isfloat(lat) and isfloat(lon):
                flights = [{
                    'flight': f,
                    'distance': utils.distance( 
                        origin=[float(lat), float(lon)],
                        destination=[f.tournament.latitude, f.tournament.longitude] )
                } for f in flights]

                flights = sorted( flights, key=cmp_to_key(utils.sort_by_location) )

                # Pagination
                offset, limit = utils.resolve_pagination( request.args )
                flights = flights[ offset : offset+limit ]
                
                return jsonify([{
                    ** x['flight'].serialize(),
                    'casino': x['flight'].tournament.casino,
                    'address': x['flight'].tournament.address,
                    'city': x['flight'].tournament.city,
                    'state': x['flight'].tournament.state,
                    'zip_code': x['flight'].tournament.zip_code,
                    'buy_in': Buy_ins.get_latest( 
                        user_id, x['flight'].tournament_id ) is not None,
                    'distance': x['distance']
                } for x in flights]), 200


            else:
                # Pagination
                offset, limit = utils.resolve_pagination( request.args )
                flights = flights.offset( offset ).limit( limit )
                
                return jsonify([{
                    **f.serialize(),
                    'casino': f.tournament.casino,
                    'address': f.tournament.address,
                    'city': f.tournament.city,
                    'state': f.tournament.state,
                    'zip_code': f.tournament.zip_code,
                    'buy_in': Buy_ins.get_latest( user_id, f.tournament_id ) is not None
                } for f in flights]), 200
            

        # Single tournament by id
        elif id.isnumeric():
            trmnt = Tournaments.query.get(int(id))
            if trmnt is None:
                raise APIException('Tournament not found', 404)

            return jsonify( actions.swap_tracker_json( trmnt, user_id )), 200


        raise APIException('Invalid id', 400)


    # CREATE A SWAP
    @app.route('/me/swaps', methods=['POST'])
    @role_jwt_required(['user'])
    def create_swap(user_id):

        # Get sender user
        sender = Profiles.query.get(user_id)
        
        # Get request json
        req = request.get_json()
        utils.check_params(req, 'tournament_id', 'recipient_id', 'percentage')
        
        if user_id == req['recipient_id']:
            raise APIException( f'Cannot swap with yourself, user_id: {user_id}, '
                                f'recipient_id: {req["recipient_id"]}' )

        # Check for sufficient coins
        swap_cost = req.get('cost', 1)
        if swap_cost < 1:
            raise APIException('No free swaps', 400)
        if sender.get_coins() - sender.get_reserved_coins() < swap_cost:
            raise APIException('Insufficient coins to make this swap', 402)
        

        # Get recipient user
        recipient = Profiles.query.get( req['recipient_id'] )
        if recipient is None:
            raise APIException('Recipient user not found', 404)

        # Check recipient swap availability
        if recipient.swap_availability_status._value_ == 'unavailable':
            raise APIException('This person is unavailable for swaps', 401)


        # Can only send one swap offer at a time
        existing_swaps = Swaps.query.filter_by(
            sender_id = user_id,
            recipient_id = recipient.id,
            tournament_id = req['tournament_id']
        )
        unacceptable_status = ['pending','incoming','counter_incoming']
        for swap in existing_swaps:
            if swap.status._value_ in unacceptable_status:
                raise APIException(
                    f'Already have a swap with status "{swap.status._value_}"'
                    ' with this player', 401 )


        percentage = req['percentage']
        counter = req.get('counter_percentage', percentage)
        if percentage < 1 or counter < 1:
            raise APIException('Cannot swap less than %1', 400)

        # Check tournament existance
        trmnt = Tournaments.query.get( req['tournament_id'] )
        if trmnt is None:
            raise APIException('Tournament not found', 404)


        # Swap percentage availability
        sender_availability = sender.available_percentage( req['tournament_id'] )
        if percentage > sender_availability:
            raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                                f'You have available: {sender_availability}%'), 400)

        recipient_availability = recipient.available_percentage( req['tournament_id'] )
        if counter > recipient_availability:
            raise APIException(('Swap percentage too large for recipient. '
                                f'He has available to swap: {recipient_availability}%'), 400)

        # Create swap
        swap = Swaps(
            sender_id = user_id,
            tournament_id = req['tournament_id'],
            recipient_id = recipient.id,
            percentage = percentage,
            cost = swap_cost,
            status = 'pending'
        )
        counter_swap = Swaps(
            sender_id = recipient.id,
            tournament_id = req['tournament_id'],
            recipient_id = user_id,
            percentage = counter,
            cost = swap_cost,
            status = 'incoming',
            counter_swap = swap
        )
        swap.counter_swap = counter_swap

        db.session.add_all([ swap, counter_swap ])
        db.session.commit()

        # Notification
        buyin = Buy_ins.get_latest(
            user_id=sender.id, tournament_id=swap.tournament_id )
        send_fcm(
            user_id = recipient.id,
            title = "New Swap",
            body = sender.get_name()+' wants to swap',
            data = {
                'id': counter_swap.id,
                'buyin_id': buyin and buyin.id,
                'alert': sender.get_name()+' wants to swap',
                'type': 'swap',
                'initialPath': 'SwapDashboard',
                'finalPath': 'SwapOffer'
            }
        )

        return jsonify({
            'swap_id': swap.id,
            'message': 'Swap created successfully.'
        }), 200


    # UPDATE SWAP
    @app.route('/me/swaps/<int:id>', methods=['PUT'])
    @role_jwt_required(['user'])
    def update_swap(user_id, id):

        # Get sender user
        sender = Profiles.query.get(user_id)

        req = request.get_json()
        utils.check_params(req)
        

        # Get swaps
        swap = Swaps.query.get(id)
        if swap is None:
            raise APIException('Swap not found', 404)

        if sender.id != swap.sender_id:
            raise APIException('Access denied: You are not the sender of this swap', 401)
        current_percentage = swap.percentage
        if sender.get_coins() < swap.cost:
            raise APIException('Insufficient coins to see this swap', 402)

        if swap.status._value_ in ['canceled','rejected','agreed']:
            raise APIException('This swap can not be modified', 400)

        counter_swap_body = {}
        counter_swap = Swaps.query.get( swap.counter_swap_id )
        if counter_swap is None:
            raise APIException('Counter swap not found', 404)


        # Get recipient user
        recipient = Profiles.query.get( swap.recipient_id )
        if recipient is None:
            raise APIException('Recipient user not found', 404)
 

        new_status = req.get('status')
        current_status = swap.status._value_

        if 'percentage' in req and new_status not in ['agreed','rejected','canceled']:

            # Handle percentage errors
            percentage = req['percentage']
            counter = req.get('counter_percentage', percentage)
            if percentage < 1 or counter < 1:
                raise APIException('Cannot swap less than %1', 400)

            sender_availability = sender.available_percentage( swap.tournament_id )
            considering_this_swap = current_status == 'incoming'
            actions = percentage if considering_this_swap else (percentage - swap.percentage)
            if actions > sender_availability:
                raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                                    f'You have available: {sender_availability}%'), 400)

            recipient_availability = \
                recipient.available_percentage( swap.tournament_id )
            if (counter - counter_swap.percentage) > recipient_availability:
                raise APIException(('Swap percentage too large for recipient. '
                                    f'He has available to swap: {recipient_availability}%'), 400)

            # Update percentages
            swap.percentage = percentage
            counter_swap.percentage = counter


        # Handle status errors
        if current_status == 'pending':
            if new_status == 'agreed':
                raise APIException('Cannot agree a swap on a pending status', 400)
            if new_status == 'rejected':
                raise APIException('Cannot reject this swap', 400)
        if current_status in ['incoming','counter_incoming'] and new_status == 'canceled':
            raise APIException('Cannot cancel this swap', 400)
        
        # Update status
        if new_status in ['agreed','rejected','canceled']:
            if new_status == 'agreed':
                if recipient.get_coins() < swap.cost:
                    raise APIException('Recipient has insufficient coins to process this swap')
                if current_status == 'incoming':
                    overdraft = current_percentage - sender.available_percentage( swap.tournament_id )
                    if overdraft > 0:
                        raise APIException(
                            f'Cannot agree to this swap, you are overdrafting by {str(overdraft)}%', 400)
            swap.status = new_status
            counter_swap.status = new_status
        # If current swap is pending, leave statuses as they are
        elif current_status != 'pending':
            swap.status = Swaps.counter_status( swap.status._value_ )
            counter_swap.status = Swaps.counter_status( counter_swap.status._value_ )


        db.session.commit()



        if new_status == 'agreed':

            db.session.add( Transactions(
                user_id = user_id,
                coins = -swap.cost
            ))
            db.session.add( Transactions(
                user_id = recipient.id,
                coins = -swap.cost
            ))
            db.session.commit()

            user1_receipt = Buy_ins.get_latest(sender.id, swap.tournament_id)
            user2_receipt = Buy_ins.get_latest(recipient.id, swap.tournament_id)
            
            send_email( template='swap_confirmation', emails=[sender.user.email, recipient.user.email],
                data={
                    'tournament_date': swap.tournament.start_at,
                    'tournament_name': swap.tournament.name,
                    
                    'user1_name': f'{sender.first_name} {sender.last_name}',
                    'user1_prof_pic': sender.profile_pic_url,
                    'user1_percentage': swap.percentage,
                    'user1_receipt_url': user1_receipt and user1_receipt.receipt_img_url,

                    'user2_name': f'{recipient.first_name} {recipient.last_name}',
                    'user2_prof_pic': recipient.profile_pic_url,
                    'user2_percentage': counter_swap.percentage,
                    'user2_receipt_url': user2_receipt and user2_receipt.receipt_img_url
                })

        
        # Notifications
        status_to_fcm = ['counter_incoming','canceled','rejected','agreed']
        status = counter_swap.status._value_
        
        if status in status_to_fcm:
            buyin = Buy_ins.get_latest(
                user_id=sender.id, tournament_id=swap.tournament_id )
            data = {
                'counter_incoming': ('Swap Countered','countered'),
                'canceled': ('Swap Canceled','canceled'),
                'rejected':('Swap Rejected','rejected'),
                'agreed': ('Swap Agreed','agreed to')
            }
            msg = f'{sender.get_name()} {data[status][1]} your swap'
            send_fcm(
                user_id = recipient.id,
                title = data[status][0],
                body = msg,
                data = {
                    'id': counter_swap.id,
                    'buyin_id': buyin and buyin.id,
                    'alert': msg,
                    'type': 'swap',
                    'initialPath': 'SwapDashboard',
                    'finalPath': 'SwapOffer' }
            )


        return jsonify([
            swap.serialize(),
            counter_swap.serialize(),
        ])


    # GET ACTION
    @app.route('/swaps/me/tournament/<int:id>', methods=['GET'])
    @role_jwt_required(['user'])
    def get_swaps_actions(user_id, id):

        prof = Profiles.query.get(user_id)

        return jsonify(prof.get_swaps_actions(id))


    # UPDATE SWAP PAID STATUS
    @app.route('/users/me/swaps/<int:id>/done', methods=['PUT'])
    @role_jwt_required(['user'])
    def set_swap_paid(user_id, id):

        req = request.get_json()
        utils.check_params(req, 'tournament_id', 'recipient_id')

        # Security validation for single swap
        swap = Swaps.query.get(id)
        if req['tournament_id'] !=  swap.tournament_id \
            or req['recipient_id'] != swap.recipient_id:
            raise APIException('Swap data does not match json data', 400)

        if swap.status._value_ != 'agreed':
            raise APIException('This swap has not been agreed upon', 400)

        if swap.paid == True:
            raise APIException('This swap is already paid', 400)

        # Calculate swap rating for these swaps
        '''
            swap.due_at is 2 days after results come in
            2 days -> 5 stars
            4 days -> 4 stars
            6 days -> 3 stars
            8 days -> 2 stars
            9 days -> 1 star
            10+ days -> suspension (naughty list)
        '''
        now = datetime.utcnow()
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
            user = Users.query.get( user_id )
            user.status = 'suspended'


        # Set to paid and add swap_rating to all the swaps with that user and that trmnt
        swaps_to_pay = Swaps.query.filter_by(
            tournament_id = req['tournament_id'],
            recipient_id = req['recipient_id'],
            status = 'agreed'
        )
        for swap in swaps_to_pay:
            swap.swap_rating = swap_rating
            swap.paid = True

        db.session.commit()

        user = Profiles.query.get( user_id )
        user.swap_rating = user.calculate_swap_rating()
        db.session.commit()

        return jsonify({'message':'Swap/s has been paid'})


    # GET SWAP TRACKER (CURRENT/UPCOMING)
    @app.route('/me/swap_tracker', methods=['GET'])
    @role_jwt_required(['user'])
    def swap_tracker(user_id):
        
        if request.args.get('history') == 'true':
            trmnts = Tournaments.get_history(user_id=user_id)
        else:
            trmnts = Tournaments.get_live_upcoming(user_id=user_id)

        swap_trackers = []

        if trmnts is not None:
            
            for trmnt in trmnts:
                json = actions.swap_tracker_json( trmnt, user_id )
                swap_trackers.append( json )

        return jsonify( swap_trackers )


    # ADD COINS TO PROFILE
    @app.route('/me/transactions', methods=['POST'])
    @role_jwt_required(['user'])
    def add_coins(user_id):

        req = request.get_json()
        utils.check_params(req, 'coins')

        db.session.add( Transactions(
            user_id = user_id,
            coins = req['coins'],
            dollars = req.get('dollars', 0)
        ))

        db.session.commit()

        user = Profiles.query.get( user_id )
        return jsonify({'total_coins': user.get_coins()})


    # GET TRANSACTIONS
    @app.route('/users/me/transactions/report', methods=['GET'])
    @role_jwt_required(['user'])
    def transaction_report(user_id):
        
        month_ago = datetime.utcnow() - timedelta(weeks=4)

        report = Transactions.query \
                    .filter( Transactions.created_at > month_ago ) \
                    .order_by( Transactions.created_at.desc() )

        return jsonify([x.serialize() for x in report])




    @app.route('/me/chats', methods=['POST'])
    @role_jwt_required(['user'])
    def create_chat(user_id):

        req = request.get_json()
        utils.check_params(req, 'user2_id', 'tournament_id')
        
        chat = Chats.get(user_id, req['user2_id'], req['tournament_id'])
        if chat is not None:
            raise APIException('Chat already exists with id '+ str(chat.id), 400)
        
        chat = Chats(
            user1_id = user_id,
            user2_id = req['user2_id'],
            tournament_id = req['tournament_id']
        )
        db.session.add( chat )
        db.session.commit()

        return jsonify( chat.serialize() )

    @app.route('/me/chats', methods=['GET'])
    @role_jwt_required(['user'])
    def get_my_chats(user_id):
        # chats = Chats.getMine(user_id)
        chat = Chats.query \
            .filter(or_(Chats.user1_id == user_id, Chats.user2_id == user_id )) \
            .order_by( Chats.updated_at.desc() )
        
        return jsonify([x.serialize() for x in chat])
        # my_chats= []
        # if chats is not None:
        #     for chat in chats:
        #         json = actions.swap_tracker_json( chat, user_id )
        #         my_chats.append( json )        
        #     return jsonify( my_chats )


    @app.route('/chats/<int:chat_id>')
    @app.route('/chats/me/users/<int:user2_id>/tournaments/<int:trmnt_id>')
    @role_jwt_required(['user'])
    def get_chat(user_id, user2_id=None, trmnt_id=None, chat_id=None):

        if chat_id:
            chat = Chats.query.get( chat_id )
        else:
            chat = Chats.get(user_id, user2_id, trmnt_id)
        if chat is None:
            raise APIException('Chat not found', 404)

        return jsonify( chat.serialize() )



    @app.route('/messages/me/chats/<int:chat_id>', methods=['POST'])
    @role_jwt_required(['user'])
    def send_message(user_id, chat_id):

        req = utils.check_params( request.get_json(), 'user_id', 'message' )

        # messages have a 100 char limit, make sure to break it up

        db.session.add( Messages(
            chat_id = chat_id,
            user_id = user_id,
            message = req['message']
        ))
        db.session.commit()
        sender = Profiles.query.get(user_id)

        a_title = f'{sender.get_name()}'
        send_fcm(
                user_id = req['user_id'],
                title = a_title,
                body = req['message'],
                data = {
                    'id': chat_id,
                    'alert': req['message'],
                    'type': 'chat',
                    'initialPath': 'ContactsScreen',
                    'finalPath': 'ChatScreen' }
            )

        return jsonify( Chats.query.get( chat_id ).serialize() )




    return app
