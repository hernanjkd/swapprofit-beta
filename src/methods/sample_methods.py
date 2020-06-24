import os
import utils
import models
import requests
import cloudinary
import cloudinary.uploader
from flask import Flask, jsonify, request
from notifications import send_email, send_fcm

def attach(app):

    @app.route('/sendemail')
    def sendemailtest():
        msg = {'name':'Hello Hernan'}
        r = send_email('account_suspension','hernanjkd@gmail.com',data=msg)
        
        return str(r)


    @app.route('/sendfcm', methods=['POST'])
    def sendfcmtest():
        
        j = request.get_json()

        return jsonify(send_fcm(
            user_id=j['user_id'],
            title=j['title'],
            body=j['body'],
            data=j['data']
        ))
       

    @app.route('/testing', methods=['GET'])
    def first_endpoint():
        Tournaments = models.Tournaments
        t = Tournaments.query.filter(
            Tournaments.name.ilike('%Hialeah - $50,000 Guaranteed%')
        ).first()
        f = [x.start_at for x in t.flights]
        return jsonify({
            'trmnt': t.start_at,
            'flights': f
        })


    @app.route('/mailgun', methods=['POST'])
    def mailgun():
        emails = request.get_json().get('emails')
        if emails is None:
            return 'Send {"emails":[]}'

        key = os.environ.get('MAILGUN_API_KEY')
        domain = os.environ.get('MAILGUN_DOMAIN')

        logs = []
        for email in emails:
            ok = requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
                auth=('api', key),
                data={
                    'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
                    'to': email,
                    'subject': 'Testing',
                    'text': 'Hello World',
                    'html': '<h1>Hello World</h1>'
                }).status_code == 200
            logs.append({'email':email,'ok':ok})

        return jsonify(logs)


    @app.route('/ocr_image', methods=['PUT'])
    def ocr():
        import re
        import os

        utils.resolve_google_credentials()
        
        result = cloudinary.uploader.upload(
            request.files['image'],
            public_id='ocr',
            crop='limit',
            width=1000,
            height=1000,
            tags=['buyin_receipt',f'user_',f'buyin_']
        )

        msg = utils.ocr_reading( result )
        
        import regex
        r = regex.hard_rock(msg)

        return jsonify({ **r, 'text': msg })

   
   @app.route('/receipt/testing', methods=['PUT'])
   def receipttesting():

        close_time = utils.designated_trmnt_close_time()

        flight = Flights.query.get( id )
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

        if None in \
            [regex_data['first_name'], regex_data['last_name'], regex_data['casino']]:
            terminate_buyin()

        # Check regex data against tournament data
        # Check casino and tournament name?
        # Check name
        validation = {}
        user = Profiles.query.get( user_id )
        validation['first_name'] = \
            True if user.first_name in regex_data['player_name'] else False
        validation['last_name'] = \
            True if user.last_name in regex_data['player_name'] else False
        
        validation['casino'] = True
        casino_name = regex_data['casino'].split(' ')
        # trmnt_casino = get trmnt casino name
        # for x in casino_name:
        #     if x not in trmnt_casino:
        #         validation['casino'] = False

        buyin.receipt_img_url = result['secure_url']
        db.session.commit()

        return jsonify({
            'buyin_id': buyin.id,
            'receipt_data': regex_data,
            'validation': validation
        })
   
    return app