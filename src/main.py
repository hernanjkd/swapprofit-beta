
import os
import actions
import utils
import json
from flask import ( Flask, request, jsonify, render_template, send_file, 
    make_response, redirect )
from flask_migrate import Migrate
from admin import SetupAdmin
from flask_cors import CORS
from flask_jwt_simple import JWTManager, create_jwt, decode_jwt, get_jwt, jwt_required
import pandas as pd
from models import Tournaments, Results, Users
from utils import APIException
from datetime import datetime, timedelta
from methods import player_methods, public_methods, sample_methods, admin_methods
from models import db

def create_app(testing=False):
    app = Flask(__name__)
    app.url_map.strict_slashes = False


    if testing:
        app.config['JWT_SECRET_KEY'] = 'dev_asdasd'
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://sample.sqlite'
        app.config['TESTING'] = True
    else:
        app.secret_key = os.environ.get('FLASK_KEY')
        app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    MIGRATE = Migrate(app, db)
    db.init_app(app)
    CORS(app)

    jwt = JWTManager(app)
    SetupAdmin(app)

    @app.errorhandler(APIException)
    def handle_invalid_usage(error):
        return jsonify(error.to_dict()), error.status_code

    ######################################################################
    # Takes in a dictionary with id, role and expiration date in minutes
    #        create_jwt({ 'id': 100, 'role': 'admin', 'exp': 15 })
    ######################################################################
    @jwt.jwt_data_loader
    def add_claims_to_access_token(kwargs={}):
        now = datetime.utcnow()
        kwargs = kwargs if isinstance(kwargs, dict) else {}
        id = kwargs.get('id')
        role = kwargs.get('role', 'invalid')
        exp = kwargs.get('exp', 15)

        return {
            'exp': now + timedelta(minutes=exp),
            'iat': now,
            'nbf': now,
            'sub': id,
            'role': role
        }


    # @app.route('/results/tournament/<int:id>')
    # def get_results(id):
        
    #     trmnt = Tournaments.query.get( id )

    #     results = Results.query.filter_by( tournament_id=id ) \
    #                             .order_by( Results.place.asc() )
        
    #     template_data = {}
    #     if trmnt:
    #         template_data['trmnt_name'] = trmnt.name
    #         if trmnt.casino:
    #             template_data['casino'] = trmnt.casino.name

    #     if results.count() == 0:
    #         results = False
        
    #     else:
    #         obj = []
    #         for x in results:
    #             obj.append({
    #                 'place': x.place,
    #                 'full_name': x.full_name,
    #                 'winnings': x.winnings,
    #                 'nationality': x.nationality
    #             })
    #         results = json.dumps(obj)

        
    #     return render_template('results_table.html',
    #         **template_data,
    #         results = json.dumps(obj)
    #     )

    app = sample_methods.attach(app)
    app = player_methods.attach(app)
    app = public_methods.attach(app)
    app = admin_methods.attach(app)

    return app

app = create_app()

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT)
