
import os
from flask import Flask, request, jsonify, url_for, redirect
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from flask_jwt_simple import JWTManager, jwt_required, create_jwt, decode_jwt, get_jwt
from utils import APIException, generate_sitemap, check_params, validation_link, update_table
from dummy_data import buy_ins, flights, swaps, profiles, tournaments
from models import db, Users, Profiles, Tournaments, Swaps, Flights, Buy_ins, Transactions, Tokens
from datetime import datetime, timedelta
import hashlib

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DB_CONNECTION_STRING')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
jwt = JWTManager(app)


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code


###############################################################################
#
# Must always pass just one dictionary when using create_jwt(), even if empty
# The expiration is for timedelta, so any keyworded argument that fits it
#
#       create_jwt( {'id':100,'role':'admin','exp':15} )
#
###############################################################################
@jwt.jwt_data_loader
def add_claims_to_access_token(kwargs):    
    now = datetime.utcnow()
    kwargs = kwargs if isinstance(kwargs, dict) else {}
    id = kwargs['id'] if 'id' in kwargs else None
    role = kwargs['role'] if 'role' in kwargs else 'invalid'
    exp = kwargs['exp'] if 'exp' in kwargs else 15
    
    return {
        'exp': now + timedelta(minutes=exp),
        'iat': now,
        'nbf': now,
        'sub': id,
        'role': role
    }




# Notes: 'admin' will have access even if arg not passed
def role_jwt_required(valid_roles=['invalid']):
    def decorator(func):
        
        @jwt_required
        def wrapper(*args, **kwargs):         
            
            jwt_role = get_jwt()['role']
            valid = True if jwt_role == 'admin' else False

            for role in valid_roles:
                if role == jwt_role:
                    valid = True
                    
            if not valid:    
                raise APIException('Access denied', 401)

            return func(*args, **kwargs)
        
        # change wrapper name so it can be used for more than one function
        wrapper.__name__ = func.__name__

        return wrapper
    return decorator




#############################################################################
## DELETE ENDPOINT - JUST FOR TESTING - DELETE ENDPOINT - JUST FOR TESTING ##
#############################################################################
@app.route('/create/token', methods=['POST'])
def create_token():
    return jsonify( create_jwt(request.get_json()) ), 200

@app.route('/testing')
# @role_jwt_required(['user'])
def testing():
    raise APIException('read this msg', 406)

@app.route('/fill_database')
def fill_database():
    return {'message':'ok'}, 200

@app.route('/tournaments', methods=['POST'])
def add_tournament():
    body = request.get_json()

    db.session.add(Tournaments(
        name = body['name'],
        address = body['address'],
        start_at = datetime( *body['start_at'] ),
        end_at = datetime( *body['end_at'] ),
        longitude = None,
        latitude = None
    ))
    db.session.commit()

    search = {
        'name': body['name'],
        'start_at': datetime( *body['start_at'] )
    }
    return jsonify(Tournaments.query.filter_by(**search).first().serialize()), 200
#############################################################################
## DELETE ENDPOINT - JUST FOR TESTING - DELETE ENDPOINT - JUST FOR TESTING ##
#############################################################################




@app.route('/users/validate/<token>', methods=['GET'])
def validate(token):
    
    jwt_data = decode_jwt(token)
    
    if jwt_data['role'] == 'invalid':
        user = Users.query.get(jwt_data['sub'])
        if not user.valid:
            user.valid = True
            db.session.commit()

    return jsonify({
        'message': 'Your email has been validated',
        'jwt': create_jwt({
            'id': jwt_data['sub'],
            'role': 'user',
            'exp': 600000
        })
    }), 200




@app.route('/users', methods=['POST'])
def register_user():

    body = request.get_json()
    check_params(body, 'email', 'password')

    m = hashlib.sha256()
    m.update(body['password'].encode('utf-8'))


    # If user exists and failed to validate his account
    user = Users.query.filter_by( email=body['email'], password=m.hexdigest() ).first()
    if user and not user.valid:
        return jsonify({'validation_link': validation_link(user.id)}), 200

    elif user and user.valid:
        raise APIException('User already exists', 405)
    
    db.session.add(Users(
        email = body['email'], 
        password = m.hexdigest()
    ))
    db.session.commit()
    
    user = Users.query.filter_by(email=body['email']).first()

    return jsonify({
        'message': 'Please verify your email',
        'validation_link': validation_link(user.id)
    }), 200




@app.route('/users/token', methods=['POST'])
def login():

    body = request.get_json()
    check_params(body, 'email', 'password')

    m = hashlib.sha256()
    m.update(body['password'].encode('utf-8'))

    user = Users.query.filter_by( email=body['email'], password=m.hexdigest() ).first()

    if not user:
        raise APIException('The log in information is incorrect', 401)

    if not user.valid:
        raise APIException('Email not validated', 405)
    
    return jsonify({
        'jwt': create_jwt({
            'id': user.id,
            'role': 'user',
            'exp': body['exp'] if 'exp' in body else 15
        })
    }), 200




@app.route('/users/<id>/email', methods=['PUT'])
@role_jwt_required(['user'])
def update_email(id):

    if id == 'me':
        id = str(get_jwt()['sub'])

    if not id.isnumeric():
        raise APIException('Invalid id: ' + id, 400)

    body = request.get_json()
    check_params(body, 'email', 'password', 'new_email')

    m = hashlib.sha256()
    m.update(body['password'].encode('utf-8'))

    user = Users.query.filter_by( id=int(id), email=body['email'], password=m.hexdigest() ).first()
    if not user:
        raise APIException('Invalid parameters', 400)

    user.valid = False
    user.email = body['new_email']

    db.session.commit()

    return jsonify({
        'message': 'Please verify your new email',
        'validation_link': validation_link(user.id)
    }), 200




@app.route('/users/<id>/password', methods=['PUT'])
@role_jwt_required(['user'])
def reset_password(id):

    if id == 'me':
        id = str(get_jwt())['sub']

    if not id.isnumeric():
        raise APIException('Invalid id: ' + id, 400)

    body = request.get_json()
    check_params(body, 'email', 'password', 'new_password')

    m = hashlib.sha256()
    m.update(body['password'].encode('utf-8'))

    user = Users.query.filter_by( id=int(id), email=body['email'], password=m.hexdigest() ).first()
    if not user:
        raise APIException('Invalid parameters', 400)

    m = hashlib.sha256()
    m.update(body['new_password'].encode('utf-8'))

    user.password = m.hexdigest()

    db.session.commit()

    return jsonify({'message': 'Your password has been changed'}), 200




@app.route('/users/forgot_password/<token>', methods=['POST','PUT'])
def forgot_password(token):
    
    jwt_data = decode_jwt(token)

    return 'ok'




# id can be the user id, 'me' or 'all'
@app.route('/profiles/<id>', methods=['GET'])
@role_jwt_required(['user'])
def get_profiles(id):

    jwt_data = get_jwt()

    if id == 'all':
        if jwt_data['role'] != 'admin':
            raise APIException('Access denied', 401)
        
        return jsonify([x.serialize() for x in Profiles.query.all()]), 200

    if id == 'me':
        id = str(jwt_data['sub'])

    if not id.isnumeric():
        raise APIException('Invalid id: ' + id, 400)

    user = Profiles.query.get(int(id))
    if not user:
        raise APIException('User not found', 404)
    
    return jsonify(user.serialize()), 200




@app.route('/profiles', methods=['POST'])
@role_jwt_required(['user'])
def register_profile():
    
    user = Users.query.get(get_jwt()['sub'])
    if not user:
        raise APIException('User not found', 404)

    body = request.get_json()
    check_params(body, 'first_name', 'last_name')

    db.session.add(Profiles(
        first_name = body['first_name'],
        last_name = body['last_name'],
        username = body['username'] if 'username' in body else None,
        hendon_url = body['hendon_url'] if 'hendon_url' in body else None,
        profile_pic_url = body['profile_pic_url'] if 'profile_pic_url' in body else None,
        user = user
    ))
    db.session.commit()

    return {'message':'ok'}, 200




@app.route('/profiles/<id>', methods=['PUT'])
@role_jwt_required(['user'])
def update_profile(id):

    if id == 'me':
        id = str(get_jwt())['sub']

    if not id.isnumeric():
        raise APIException('Invalid id: ' + id, 400)

    prof = Profiles.query.get(int(id))
    if not prof:
        raise APIException('User not found', 404)

    body = request.get_json()    
    check_params(body)
    
    update_table(prof, body)

    db.session.commit()

    return jsonify(prof.serialize())



# Can search by id, 'name' or 'all'
@app.route('/tournaments/<id>', methods=['GET'])
@role_jwt_required(['user'])
def get_tournaments(id):

    if id == 'all':
        return jsonify([x.serialize() for x in Tournaments.query.all()]), 200

    if id.isnumeric():
        trnmt = Tournaments.query.get(int(id))
    else:
        trnmt = Tournaments.query.filter(Tournaments.name.ilike(f'%{id}%')).all()
    
    if not trnmt:
        raise APIException('Tournament not found', 404)
    
    if isinstance(trnmt, list):
        return jsonify([x.serialize() for x in trnmt]), 200

    return jsonify(trnmt.serialize()), 200




@app.route('/swaps', methods=['GET'])
def get_swaps():
    prof = Profiles.query.get(7)
    return str(prof.available_percentage(1))
    # return jsonify( [x.serialize() for x in Swaps.query.all()] )




@app.route('/swaps/me', methods=['POST'])
@role_jwt_required(['user'])
def create_swaps():
    
    body = request.get_json()
    check_params(body, 'tournament_id', 'recipient_id', 'percentage')

    id = int(get_jwt()['sub'])

    prof = Profiles.query.get(id)
    if not prof:
        raise APIException('User not found', 404)

    available = prof.available_percentage( body['tournament_id'] )

    if body['percentage'] > available:
        raise APIException(('Swap percentage too large. You can not exceed 50% per tournament. '
                            f'You have available: {available}%'), 400)

    db.session.add(Swaps(
        sender_id = id,
        tournament_id = body['tournament_id'],
        recipient_id = body['recipient_id'],
        percentage = body['percentage']
    ))
    db.session.commit()

    return {'message':'ok'}, 200




if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT)
