import json
import requests
import google.auth
import base64
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from google.cloud import bigquery

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



def get_email_and_name_by_id(member_id):
    api_url = f"https://app.officernd.com/api/v1/organizations/worq/members/{member_id}"
    params = get_ornd_auth()
    response = requests.get(api_url, headers=params)
    response_json = response.json()
    email = response_json["email"]
    name = response_json["name"]
    return {"email": email, "name": name}

def process_webhook(request):
  # Extract webhook data from request
  data = request.get_json()

  # Retrieve passcode from TTlock API
  lock_id = data['lock_id']
  passcode_response = requests.get(f'https://api.ttlock.com/v3/passcodes/{lock_id}')
  passcode_response_data = passcode_response.json()
  passcode = passcode_response_data['passcode']

  # Add passcode to webhook data
  data['passcode'] = passcode

  # Insert data into BigQuery table
  table_id = "my-project.my_dataset.my_table"
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
