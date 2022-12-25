from flask import Flask, request
import requests

app = Flask(__name__)

def generate_passcode(lock_id, start_date, end_date):
  # Set up TTlock API endpoint and headers
  api_endpoint = 'https://openapi.ttlock.com/1.0/lock/sendTempPassword'
  headers = {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/x-www-form-urlencoded'
  }

  # Set up request data
  data = {
    'lockId': lock_id,
    'startDate': start_date,
    'endDate': end_date,
    'passwordType': 1  # 1 for temporary passcode
  }

  # Make request to TTlock API
  response = requests.post(api_endpoint, headers=headers, data=data)

  # Extract passcode from response
  passcode = response.json()['password']
  return passcode

def send_email(to_address, passcode):
  import smtplib

  # Set up SMTP server
  smtp_server = smtplib.SMTP('smtp.example.com')

  # Set up email message
  from_address = 'noreply@example.com'
  subject = 'Meeting Room Passcode'
  body = 'Your passcode for the meeting room is: {}'.format(passcode)
  msg = 'Subject: {}\n\n{}'.format(subject, body)

  # Send email
  smtp_server.sendmail(from_address, to_address, msg)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
  # Extract booking data from request
  booking_data = request.get_json()

  # Generate passcode using TTlock API
  passcode = generate_passcode(booking_data['lock_id'], booking_data['start_date'], booking_data['end_date'])

  # Send email with passcode to user
  send_email(booking_data['email'], passcode)

  return 'Success'

if __name__ == '__main__':
  app.run()
