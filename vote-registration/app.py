#!/usr/bin/env python

import os 
import random
import string
from threading import Lock

from flask import Flask, redirect, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, close_room, disconnect

from urllib.parse import urlparse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
#app.config['SECRET_KEY'] = 'secret!'
app.config['SAML_CONFIG'] = os.path.dirname(os.path.abspath(__file__))
socketio = SocketIO(app, async_mode=async_mode)
#thread = None
#thread_lock = Lock()

registered_fullnames = []
registered_userids = []
registered_sessionids = []
generated_tokens = []
admins = []
session_userids = {}
session_fullnames = {}
registration_active = True
login_sessions = {}

class SamlReturnData:
    adminStatus = False
    presenterStatus = False
    userid = ""
    fullname = ""

def init_saml_auth(req):
    return OneLogin_Saml2_Auth(req, custom_base_path=app.config['SAML_CONFIG'])

def prepare_flask_request(request):
    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    url_data = urlparse(request.url)
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy(),
        'query_string': request.query_string
    }

@app.route('/', methods=['GET'])
def sso():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req) 
    return redirect(auth.login())

@app.route('/', methods=['POST'])
def acs():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    auth.process_response()
    errors = auth.get_errors()

    if not auth.is_authenticated() or len(errors) > 0:
        # no proper login
        # TODO error message
        return "Login error"

    attributes = auth.get_attributes()
    token = generate_token()

    saml_return_data = SamlReturnData()
    saml_return_data.fullname = attributes['fullname']
    saml_return_data.userid = attributes['userid']
    saml_return_data.adminStatus = attributes.get('is_admin', False)
    saml_return_data.presenterStatus = attributes.get('is_presenter', False)
    login_sessions[token] = saml_return_data

    if 'RelayState' in request.form and request.form['RelayState'] == 'admin':
        if not saml_return_data.adminStatus:
            # TODO error messag
            return "Access denied"

        return render_template('admin.html', async_mode=socketio.async_mode, token=token)

    else:
        return render_template('index.html', async_mode=socketio.async_mode, token=token)


@app.route('/admin', methods=['GET'])
def admin_get():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    #return redirect(auth.login(request.url))
    return redirect(auth.login('admin'))


@app.route('/presenter')
def presenter():
    # TODO: Access control (needed?)
    return render_template('presenter.html', async_mode=socketio.async_mode)


# TODO SAML SLS 

@app.route('/static/secret-voting.js')
def send_js():
    return app.send_static_file('secret-voting.js')


@socketio.on('voting_register', namespace='/test')
def voting_register(message):
    global registration_active
    if not registration_active:
        return
    fullname = session_fullnames[request.sid]
    userid = session_userids[request.sid]
    if userid in registered_userids:
        emit('register_response',
             {'successful': False})
        return
    registered_fullnames.append(fullname)
    registered_userids.append(userid)
    registered_sessionids.append(request.sid)
    registered_sessionids.sort()
    del session_userids[request.sid]
    del session_fullnames[request.sid]
    emit('register_response',
         {'successful': True})
    emit('register_broadcast',
         {'name': fullname,
          'registered_fullnames': registered_fullnames},
         broadcast=True)


# TODO: Check admin permissions in these calls
@socketio.on('admin_voting_reset', namespace='/test')
def admin_voting_reset(message):
    global registration_active, admins
    if request.sid not in admins:
        return
    registration_active = True
    registered_fullnames.clear()
    generated_tokens.clear()
    emit('reset_broadcast',
         {},
         broadcast=True)


@socketio.on('admin_voting_end', namespace='/test')
def admin_voting_end(message):
    global registration_active, admins
    if request.sid not in admins:
        return
    if not registration_active:
        return
    registration_active = False
    emit('voting_end_broadcast',
         {},
         broadcast=True)
    for sid in registered_sessionids:
        token = generate_display_token()
        generated_tokens.append(token)
        generated_tokens.sort()
        emit('generated_token',
             {'token': token},
             room=sid)
        close_room(sid)
        disconnect(sid=sid)
    registered_sessionids.clear()
    # TODO: Close all non-admin/non-presenter sessions?
    # TODO: Following is admin only -> admin rooom
    emit('voting_end_response',
         {'all_users': registered_fullnames,
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


@socketio.on('connect', namespace='/test')
def connect():
    global admins, registration_active, registered_fullnames
    token = request.args.get('token')
    saml_return_data: SamlReturnData = login_sessions[token]
    del login_sessions[token]
    if saml_return_data.adminStatus:
        admins.append(request.sid)
        admin_state = True
    else:
        admin_state = False
    userid = saml_return_data.userid
    fullname = saml_return_data.fullname
    session_userids[request.sid] = userid
    session_fullnames[request.sid] = fullname
    if userid in registered_userids:
        already_registered = True
    else:
        already_registered = False
    emit('initial_status',
         {'registration_active': registration_active,
          'registered_fullnames': registered_fullnames,
          'already_registered': already_registered,
          'fullname': fullname,
          'admin_state': admin_state})
    print("Connected")


# TODO: We could remove the user from the lists here, if we didn't remove the session-user mapping before
#  This would allow re-registration after a disconnect
#@socketio.on('disconnect', namespace='/test')
#def test_disconnect():
#    print('Client disconnected', request.sid)


# TODO: Not used
def generate_token():
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(50))


def generate_display_token():
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(8))


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
