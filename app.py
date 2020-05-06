#!/usr/bin/env python

import random
import string
from threading import Lock

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, close_room

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

registered_usernames = []
registered_rooms = []
generated_tokens = []
voting_active = True


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('voting_register', namespace='/test')
def voting_register(message):
    global voting_active
    if not voting_active:
        return
    registered_usernames.append(message['data'])
    token = generate_token()
    while token in registered_rooms:
        token = generate_token()
    registered_rooms.append(token)
    registered_rooms.sort()
    join_room(token)
    emit('register_response',
         {'successful': True})
    emit('register_broadcast',
         {'name': message['data'],
          'all_users': registered_usernames},
         broadcast=True)


@socketio.on('voting_reset', namespace='/test')
def voting_reset(message):
    global voting_active
    voting_active = True
    registered_usernames.clear()
    generated_tokens.clear()
    emit('reset_broadcast',
         {},
         broadcast=True)


@socketio.on('voting_end', namespace='/test')
def voting_end(message):
    global voting_active
    if not voting_active:
        return
    voting_active = False
    for room in registered_rooms:
        token = generate_token()
        generated_tokens.append(token)
        generated_tokens.sort()
        emit('generated_token',
             {'token': token},
             room=room)
        close_room(room)
    registered_rooms.clear()
    emit('voting_end_response',
         {'all_users': registered_usernames,
          'all_tokens': generated_tokens})


# TODO: Do we need to handle disconnect?
#@socketio.on('disconnect_request', namespace='/test')
#def disconnect_request():
#    @copy_current_request_context
#    def can_disconnect():
#        disconnect()
#
#    session['receive_count'] = session.get('receive_count', 0) + 1
#    # for this emit we use a callback function
#    # when the callback function is invoked we know that the message has been
#    # received and it is safe to disconnect
#    emit('my_response',
#         {'data': 'Disconnected!', 'count': session['receive_count']},
#         callback=can_disconnect)


# TODO: Load current voting state on connect
#@socketio.on('connect', namespace='/test')
#def test_connect():


#@socketio.on('disconnect', namespace='/test')
#def test_disconnect():
#    print('Client disconnected', request.sid)


def generate_token():
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(20))


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
