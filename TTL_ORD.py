import json
import requests
import google.auth
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import time
from google.cloud import bigquery
from google.cloud import functions

# Set up BigQuery client
client = bigquery.Client()
scopes = ['https://www.googleapis.com/auth/gmail.send']
creds, project = google.auth.default(scopes=scopes)

def send_email(to, passcode):
    try:
        service = build('gmail', 'v1', credentials=creds)
        message = create_message(to, passcode)
        send_message = (service.users().messages().send(userId="me", body=message).execute())
        print(F'{to} Message Id: {send_message["id"]}')
    except HttpError as error:
        print(F'An error occurred: {error}')
        send_message = None
    return send_message


def create_message(to, passcode):
    message = MIMEText(f'Your passcode for the meeting room is: {passcode}')
    message['to'] = to
    message['subject'] = 'Meeting Room Passcode'
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def get_ornd_auth():
    post_payload = {
        "client_id": "HD9V1j6sI1aLieZ5",
        "client_secret": "iKeTMUaVXew1EwqQQSSRb2AC6vbehWQY",
        "grant_type": "client_credentials",
        "scope": "officernd.api.read"
    }
    options = {
        "method" : "post",
        "payload" : post_payload
    }
    pre_response = requests.post('https://identity.officernd.com/oauth/token', options)
    pre_response_json = pre_response.json()
    access_token = pre_response_json["access_token"]
    headers = {
        "Authorization" : f"Bearer {access_token}"
    }
    params = {
        "method": "get",
        "headers": headers
    }
    return params

def generate_passcode( start_date, end_date, name, company):
    today = int(time.time())
    url = "https://euapi.ttlock.com/v3/keyboardPwd/get"
    headers = {
        "ContentType": "application/x-www-form-urlencoded",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "clientId": "254709733a6c4331995b4771e0bce143",
        "accessToken": "c0cb52a1308dc477a43b02c77fbc663d",
        "lockId": "6758026",
        "keyboardPwdType": 3,
        "keyboardPwdName": f"{name} | {company}",
        "startDate": start_date,
        "endDate": end_date,
        "date": today
    }
    response = requests.post(url, headers=headers, data=payload)
    return response.json()


def get_email_and_name_by_id(member_id):
    api_url = f"https://app.officernd.com/api/v1/organizations/worq/members/{member_id}"
    params = get_ornd_auth()
    response = requests.get(api_url, headers=params)
    response_json = response.json()
    email = response_json["email"]
    name = response_json["name"]
    return {"email": email, "name": name}



@functions.http(method='POST', path='/process-webhook')
def process_webhook(request):
  # Extract webhook data from request
  data = request.get_json()

  # Generate passcode and retrieve response data
  start_date = data['start_date']
  end_date = data['end_date']
  name = data['name']
  company = data['company']
  response_data = generate_passcode( start_date, end_date, name, company)

    # Add response data to webhook data
  passcode = response_data['passcode']
  data['passcode'] = response_data['passcode']
  data['keyboardPwdId'] = response_data['keyboardPwdId']

  # Insert data into BigQuery table
  table_id = "splendid-sector-327407.SG1.SG1_TTL_Cloud"
  table = client.get_table(table_id)
  rows_to_insert = [data]
  errors = client.insert_rows(table, rows_to_insert)

  if errors == []:
    print("New row added to table")
    
    # Extract user id from webhook data
    user_id = data['member']

    # Retrieve user email and name
    user_info = get_email_and_name_by_id(user_id)
    user_email = user_info['email']
    user_name = user_info['name']

    # Send email to user with passcode
    send_email(user_email, passcode)
  else:
    print(errors)
