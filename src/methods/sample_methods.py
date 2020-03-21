import os
import utils
import models
import requests
from flask import Flask, jsonify, request
from notifications import send_email, send_fcm, send_fcm2

def attach(app):

    @app.route('/sendemail')
    def sendemailtest():
        msg = {'name':'Hello Hernan'}
        r = send_email('account_suspension','hernanjkd@gmail.com',data=msg)
        
        return str(r)


    @app.route('/sendfcm', methods=['POST'])
    def sendfcmtest():
        
        j = request.get_json()

        if j.get('single') is None:
            return jsonify(send_fcm(
                user_id=j['user_id'],
                title=j['title'],
                body=j['body'],
                data=j['data']
            ))
        else:
            return jsonify(send_fcm2(
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


    @app.route('/mailgun')
    def get_logs():
        return jsonify( requests.get(
            f"https://api.mailgun.net/v3/{os.environ.get('MAILGUN_DOMAIN')}/events",
            auth=("api", os.environ.get("MAILGUN_API_KEY")),
            params={"begin"       : "Fri, 13 DEC 2019 09:00:00 -0000",
                    "ascending"   : "yes",
                    "limit"       :  25,
                    "pretty"      : "yes",
                    "recipient" : "hernanjkd@gmail.com"}).json())

    @app.route('/ocr_image', methods=['PUT'])
    def ocr():
        import re
        import os

        utils.resolve_google_credentials()
        
        result = utils.cloudinary_uploader( 'buyin',
            request.files['image'], 'ocr', 
            ['buyin_receipt',f'user_',f'buyin_'] )
        
        msg = utils.ocr_reading( result )
        
        import regex
        r = regex.hard_rock(msg)

        return jsonify({ **r, 'text': msg })

    return app