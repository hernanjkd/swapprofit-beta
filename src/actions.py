import os
import json
import utils
import requests
from sqlalchemy import or_
from utils import isfloat
from datetime import datetime
from models import db, Profiles, Buy_ins, Swaps, Tournaments, Flights, Casinos, Results, Users




def swap_tracker_json(trmnt, user_id):

    my_buyin = Buy_ins.get_latest( user_id=user_id, tournament_id=trmnt.id )
    final_profit = 0

    swaps = Swaps.query.filter_by(
        sender_id = user_id,
        tournament_id = trmnt.id
    )

    # separate swaps by recipient id
    swaps_by_recipient = {}
    for swap in swaps:
        rec_id = str(swap.recipient_id)
        data = swaps_by_recipient.get( rec_id, [] )
        swaps_by_recipient[ rec_id ] = [ *data, swap ]
    
    # Loop through swaps to create swap tracker json and append to 'swaps_buyins'
    swaps_buyins = []
    for rec_id, swaps in swaps_by_recipient.items():
        recipient_buyin = Buy_ins.get_latest(
                user_id = rec_id,
                tournament_id = trmnt.id
            )

        # Catch ERRORS
        if recipient_buyin is None or my_buyin is None:
            swap_data_for_error_message = [{
                'recipient_name': f'{x.recipient_user.first_name} {x.recipient_user.last_name}',
                'sender_name': f'{x.sender_user.first_name} {x.sender_user.last_name}',
                'tournament_name': x.tournament.name 
            } for x in swaps]
            if recipient_buyin is None:
                return { 
                    'ERROR':'Recipient has swaps with user in this tournament but no buy-in',
                    'recipient buyin': None,
                    'swaps with user': swap_data_for_error_message }
            if my_buyin is None:
                return { 
                    'ERROR':'User has swaps in this tournament but no buy-in',
                    'buyin': None,
                    'user swaps': swap_data_for_error_message }

        # Structure and fill most properties for swap tracker json
        recipient_user = Profiles.query.get( rec_id )
        data = {
            'recipient_user': recipient_user.serialize(),
            'recipient_buyin': recipient_buyin.serialize(),
            'their_place': recipient_buyin.place,
            'you_won': my_buyin.winnings if my_buyin.winnings else 0,
            'they_won': recipient_buyin.winnings if recipient_buyin.winnings else 0,
            'available_percentage': recipient_user.available_percentage(trmnt.id),
            'agreed_swaps': [],
            'other_swaps': []
        }

        # Fill in properties: 'agreed_swaps' and 'other_swaps' lists
        you_owe_total = 0
        they_owe_total = 0
        for swap in swaps:
            single_swap_data = { **swap.serialize(),
                'counter_percentage': swap.counter_swap.percentage,
                'they_paid': swap.counter_swap.paid,
                'they_confirmed': swap.counter_swap.confirmed, }
            
            if swap.status._value_ == 'agreed':
                you_owe = ( float(my_buyin.winnings) * swap.percentage / 100 ) \
                    if isfloat(my_buyin.winnings) else 0
                they_owe = ( float(recipient_buyin.winnings) 
                    * swap.counter_swap.percentage / 100 ) \
                    if isfloat(recipient_buyin.winnings) else 0
                you_owe_total += you_owe
                they_owe_total += they_owe
                data['agreed_swaps'].append({
                    **single_swap_data,
                    'you_owe': you_owe,
                    'they_owe': they_owe
                })
            else:
                data['other_swaps'].append(single_swap_data)

        # Fill in final properties
        data['you_owe_total'] = you_owe_total
        data['they_owe_total'] = they_owe_total
        final_profit -= you_owe_total
        final_profit += they_owe_total

        # IF user doesn't owe anything to other guy, 
        # make all agreed swaps paid for themselves
        # if final_profit >= 0:
        #     for swap in data['agreed_swaps']:
        #         # swap['paid'] = True
        #         the_swap = Swaps.query.get( swap.id)
        #         print('the_swap', the_swap)
        #         the_swap.paid = True
        #         the_swap.paid_at = datetime.utcnow()
        #         the_swap.confirmed = True
        #         the_swap.confirmed_at = datetime.utcnow()


        # Append json
        swaps_buyins.append(data)

    return {
        'tournament': trmnt.serialize(),
        'my_buyin': my_buyin and my_buyin.serialize(),
        'buyins': swaps_buyins,
        'final_profit': final_profit
    }



# Save all the data in the json files in the db
def load_tournament_file():



    path = os.environ['APP_PATH']
    with open( path + '/src/jsons/tournaments.json' ) as f:
        data = json.load( f )


    # casino cache so not to request for same casinos
    path_cache = os.environ['APP_PATH'] + '/src/jsons/casinos.json'
    if os.path.exists( path_cache ):
        with open( path_cache ) as f:
            cache = json.load(f)
    else: cache = {}


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
            print("THIS CASINO", f'{casino}') 
            trmntjson = {
                **trmntjson,
                'casino': casino['name'],
                'address': casino['address'].strip(),
                'city': casino['city'].strip(),
                'state': casino['state'].strip(),
                'zip_code': str( casino['zip_code'] ).strip(),
                'longitude': float( casino['longitude'] ),
                'latitude': float( casino['latitude'] )
            }

            # Create tournament
            trmnt = Tournaments(
                **trmntjson
            )
            db.session.add( trmnt )
            db.session.flush()
                     
            # Create flight
            db.session.add( Flights( 
                tournament_id=trmnt.id,
                **flightjson
            ))

        else:
            # Create flight
            db.session.add( Flights( 
                tournament_id=trmnt.id,
                **flightjson
            ))
            

        db.session.commit()

    return True


    '''
    {
        "api_token": 1
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
    trmnt_data = {}
    print('hello')
    
    for index, r in df.iterrows():
        # print('r', r)
        # Get the trmnt data that's in the first row
        if index == 0:
            
            # Check trmnt existance
            trmnt = Tournaments.query.get( r['Tournament ID'] )
            print('trmnt.buy_in', trmnt.buy_in)

            if trmnt is None:
                return None, {
                    'error':'This tournament ID was not found: '+ str(r['Tournament ID'])
                }
            print('tournament', trmnt)
            trmnt.results_link = (os.environ['API_HOST'] + '/results/tournament/' + str(r['Tournament ID']) )

            # Check to see if file was uploaded already
            entry = Results.query.filter_by(
                tournament_id = r['Tournament ID']
            ).first()
            
            if entry is not None:
                return None, {
                    'error':'This tournament ID has already been uploaded: '+ str(trmnt.id)
                }
            
            # Swap Profit JSON
            trmnt_data = {
                'api_token': utils.sha256( os.environ['API_TOKEN'] ),
                'tournament_id': trmnt.id,
                'tournament_buyin': trmnt.buy_in,
                'users': {}
            }

        user_id = r['User ID'] or None
        
        # Add user to the Swap Profit JSON
        if user_id:
            user = Users.query.get( user_id )
            if user is None:
                db.session.rollback()
                return None, {
                    'error':'Couldn\'t find user with ID: '+ str(user_id)
                }
            # Swap Profit JSON
            trmnt_data['users'][user.email] = {
                'place': r['Place'],
                'winnings': r['Winnings']
                # 'user_id': user.id
            }

        # Add to PokerSociety database
        db.session.add( Results(
            tournament_id = trmnt_data['tournament_id'],
            user_id = user_id,
            full_name = r['Full Name'],
            place = r['Place'],
            nationality = r['Nationality'],
            winnings = r['Winnings']
        ))

    # If no errors, commit all data
    db.session.commit()
    # swapprofit = Subscribers.query.filter_by(company_name='Swap Profit').first()
    # if swapprofit is None:
    #     return 'Swap Profit not a subscriber'
    # resp = requests.post( 
    #         os.environ['SWAPPROFIT_API_HOST'] + '/results/update',
    #         json=trmnt_data )
    # print('resp', resp)

    return trmnt_data, {
        'message': 'Results excel processed successfully'
    }