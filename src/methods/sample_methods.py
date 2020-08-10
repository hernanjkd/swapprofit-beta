import os
import utils
import models as m
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
       

    @app.route('/testing', methods=['POST'])
    def first_endpoint():
        pass
        # r = request.get_json()
        # user = m.Users.query.filter_by(email=r['email']).first()
        # if user.password == utils.sha256(r['password']):
        #     return 'true'
        # else: return 'false'
        


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


   
    return app