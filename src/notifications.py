import os
import requests
from flask import render_template
from models import Devices
from utils import APIException
# from pyfcm import FCMNotification

push_service = None
FIREBASE_KEY = os.environ.get('FIREBASE_KEY')
if(FIREBASE_KEY and FIREBASE_KEY != ''):
    push_service = FCMNotification(api_key=FIREBASE_KEY)

EMAIL_NOTIFICATIONS_ENABLED = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED')



def send_email(template, emails, data={}):
    
    if EMAIL_NOTIFICATIONS_ENABLED != 'TRUE':
        raise APIException('Emails are not enabled', 500)
        
    template = get_template_content(template, data, ['email'])
    domain = os.environ.get('MAILGUN_DOMAIN')

    for email in emails:
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
        
        if r.status_code != 200:
            raise APIException(f'Error sending email to {email}', 500)

    return True


def send_sms(template, phone_number, data={}):

    template = get_template_content(template, data, ['email', 'fms'])
    
    TWILIO_SID = os.environ.get('TWILIO_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    message = client.messages \
                    .create(
                        body=template['fms'],
                        from_='+15017122661',
                        to='+15558675310'
                    )



def send_fcm(template, user_id, data={}):
    
    devices = Devices.query.filter_by( user_id = user_id )
    registration_ids = [device.token for device in devices]

    if(len(registration_ids) == 0 or push_service is None):
        return False
    
    content = get_template_content(template, data, ['fms'])

    if 'fms' not in content:
        raise APIException(
            f'The template {template} does not seem to have a valid FMS version')

    message_title = content['subject']
    message_body = content['fms']
    if 'data' not in data:
        raise APIException('There is no data for the notification')
    message_data = data['data']

    result = push_service.notify_multiple_devices(
        registration_ids=registration_ids,
        message_title=message_title,
        message_body=message_body,
        data_message=message_data
    )

    if(result['failure'] or not result['success']):
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
        'account_suspension': 'Swap Account Suspension'
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
        # 'terms_conditions_link': ''
        # 'mail_settings_link': '',
        # 'unsubscribe_link': '',
        # 'facebook_link': 'https://facebook.com/',
        # 'twitter_link': 'https://twitter.com/',
        # 'instagram_link': 'https://instagram.com/',
        # 'mailchimp_link': 'https://mailchimp.com/'
    }

    if formats is None or 'email' in formats:
        templates['text'] = render_template( template +'.txt', **template_data)
        templates['html'] = render_template( template +'.html', **template_data)

    if formats is not None and 'fms' in formats:
        templates['fms'] = render_template( template +'.fms', **template_data)

    
    return templates
