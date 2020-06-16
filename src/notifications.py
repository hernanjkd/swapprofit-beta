import os
import utils
import requests
from flask import render_template, jsonify
from models import Devices
from utils import APIException
from pyfcm import FCMNotification

push_service = None
FIREBASE_KEY = os.environ.get('FIREBASE_KEY')
if FIREBASE_KEY is not None:
    push_service = FCMNotification( api_key=FIREBASE_KEY )

EMAIL_NOTIFICATIONS_ENABLED = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED')



def send_email(template, emails, data={}):
    
    if EMAIL_NOTIFICATIONS_ENABLED != 'TRUE':
        raise APIException('Emails are not enabled', 500)
        
    template = get_template_content(template, data, ['email'])
    domain = os.environ.get('MAILGUN_DOMAIN')

    
    r = requests.post(f'https://api.mailgun.net/v3/{domain}/messages',
        auth=(
            'api',
            os.environ.get('MAILGUN_API_KEY')),
        data={
            'from': f'{domain} <mailgun@swapprofit.herokuapp.com>',
            'to': emails,
            'subject': template['subject'],
            'text': template['text'],
            'html': template['html']
    })
    
    return r.status_code == 200



def send_fcm(user_id, title, body, data={}):

    devices = Devices.query.filter_by( user_id = user_id )
    registration_ids = [device.token for device in devices]

    if len(registration_ids) == 0 or push_service is None:
        return False

    result = push_service.notify_multiple_devices(
        registration_ids = registration_ids,
        message_title = title,
        message_body = body,
        data_message = data
    )
    
    if result['failure'] or not result['success']:
        raise APIException('Problem sending the notification')

    return result
    


def get_template_content(template, data={}, formats=None):
    
    subjects = {
        'email_validation': 'Swap Profit Email Verification',
        'welcome': 'Welcome to Swap Profit!',
        'swap_confirmation': 'Swap Confirmation',
        'buyin_receipt': 'Your receipt has been uploaded!',
        'wrong_receipt': 'Oops! We have an issue with your receipt!',
        'swap_results': 'Swap Results',
        'payment_reminder': 'Swap Payment Reminder',
        'account_suspension': 'Swap Account Suspension',
        'reset_password_link': 'Reset Password',
        'invitation_email': "You've been invited to Swap Profit",
        'swap_incoming_notification': 'You have an incoming swap!',
        'swap_agreed_notification': 'Your swap has been agreed!'
    }

    templates = {
        'subject': subjects.get(template)
    }

    template_data = {
        **data,
        'API_URL': os.environ.get('API_HOST'),
        'COMPANY_NAME': 'Swap Profit',
        'COMPANY_LEGAL_NAME': 'Swap Profit LLC',
        'COMPANY_ADDRESS': '700 Executive Center Drive #29, West Palm Beach, FL 33401'
    }

    if formats is None or 'email' in formats:
        templates['text'] = render_template( template +'.txt', **template_data)
        templates['html'] = render_template( template +'.html', **template_data)

    if formats is not None and 'fms' in formats:
        templates['fms'] = render_template( template +'.fms', **template_data)

    
    return templates
