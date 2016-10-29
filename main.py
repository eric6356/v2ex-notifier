#!/usr/bin/env python
# coding: utf-8

import argparse
import base64
import feedparser
import os
import pickle
import httplib2
import sys
from email.mime.text import MIMEText
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

SCOPES = 'https://www.googleapis.com/auth/gmail.send'
NOTI_URL = os.environ.get('NOTI_URL')
BASE_DIR = os.environ.get('BASE_DIR', os.getcwd())
RECEIVER = os.environ.get('RECEIVER')


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    secret_file_path = os.path.join(BASE_DIR, 'client_secret.json')
    credential_path = os.path.join(BASE_DIR, 'credential.json')
    store = Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(secret_file_path, SCOPES)
        flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
        credentials = tools.run_flow(flow, store, flags)

    return credentials


def create_message(entry):
    """Create a message for an email from a feed entry.
    Args:
        entry: feed entry.

    Returns:
        An object containing a base64url encoded email object.
    """
    html = '{0}<br><a style="font-size: 85%; color: gray;" href={1}>{1}</a>'.format(entry.summary, entry.link)
    message = MIMEText(html, 'html')
    message['to'] = RECEIVER
    message['from'] = 'V2EX-NOTI'
    subject = entry.title or '{} 感谢了你'.format(entry.author)
    message['subject'] = '[V2EX-NOTI] {}'.format(subject)

    if sys.version_info > (3, 0):
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    else:
        raw = base64.urlsafe_b64encode(message.as_string())

    return {'raw': raw}


def send_messages(messages):
    """Send all messages
    Args:
        messages: messages to be sent
    Returns:
         Sent messages
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    resource = service.users().messages()
    messages = [resource.send(userId='me', body=one).execute() for one in messages]
    return messages


def main():
    messages = []
    feeds = feedparser.parse(NOTI_URL)
    pickle_path = os.path.join(BASE_DIR, 'last-entry.pickle')
    if not os.path.exists(pickle_path):
        pickle.dump(feeds.entries[0], open(pickle_path, 'wb'))
        print('init')
        return

    old_entry = pickle.load(open(pickle_path, 'rb'))
    for e in feeds.entries:
        if old_entry != e:
            messages.append(create_message(e))
        else:
            break
    if messages:
        pickle.dump(feeds.entries[0], open(pickle_path, 'wb'))
        send_messages(messages)
        print('{} message(s) sent'.format(len(messages)))
    else:
        print('no new feed')


if __name__ == '__main__':
    main()
