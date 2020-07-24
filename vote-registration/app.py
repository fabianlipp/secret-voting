#!/usr/bin/env python

import os
import random
import string
from threading import Lock
from urllib.parse import urlparse

from flask import Flask, make_response, redirect, render_template, request, session
from flask_socketio import SocketIO, emit, join_room, close_room, disconnect
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
SAML_CONFIG_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
socketio = SocketIO(app, async_mode=async_mode)

admins = []
session_userids = {}
session_fullnames = {}
login_sessions = {}


class SamlReturnData:
    votingStatus = False
    adminStatus = False
    presenterStatus = False
    userid = ""
    fullname = ""


class VoteRegistrationData:
    registration_active = False
    registered_fullnames = []
    registered_userids = []
    registered_sessionids = []
    voting_title = ""
    voting_link = ""


vote_registration_data: VoteRegistrationData = VoteRegistrationData()
vote_registration_lock = Lock()


def init_saml_auth(req):
    return OneLogin_Saml2_Auth(req, custom_base_path=SAML_CONFIG_DIRECTORY)


def prepare_flask_request(request_data):
    # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
    url_data = urlparse(request_data.url)
    return {
        'https': 'on' if request_data.scheme == 'https' else 'off',
        'http_host': request_data.host,
        'server_port': url_data.port,
        'script_name': request_data.path,
        'get_data': request_data.args.copy(),
        'post_data': request_data.form.copy(),
        'query_string': request_data.query_string
    }


@app.route('/', methods=['GET'])
def sso():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    if auth.get_settings().get_security_data().get('localMode', False):
        return render_template('local.html', RelayState="")
    return redirect(auth.login())


@app.route('/', methods=['POST'])
def acs():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)

    token = generate_token()
    saml_return_data = SamlReturnData()

    local_mode = auth.get_settings().get_security_data().get('localMode', False)
    if local_mode:
        # Local Mode is active, do not check SAML login data
        saml_return_data.fullname = request.form.get('fullname')
        saml_return_data.userid = request.form.get('userid')
        saml_return_data.votingStatus = request.form.get('is_voting')
        saml_return_data.adminStatus = request.form.get('is_admin')
        saml_return_data.presenterStatus = request.form.get('is_presenter')
    else:
        auth.process_response()
        errors = auth.get_errors()

        if not auth.is_authenticated() or len(errors) > 0:
            # no proper login
            return render_template("message.html", msg="not_authenticated")

        attributes = auth.get_attributes()
        saml_return_data.fullname = attributes['fullname']
        saml_return_data.userid = attributes['userid']
        saml_return_data.votingStatus = attributes.get('is_voting', False)
        saml_return_data.adminStatus = attributes.get('is_admin', False)
        saml_return_data.presenterStatus = attributes.get('is_presenter', False)

    login_sessions[token] = saml_return_data

    if 'RelayState' in request.form and request.form['RelayState'] == 'admin':
        if not saml_return_data.adminStatus:
            return render_template("message.html", msg="no_admin_permissions")
        return render_template('admin.html', async_mode=socketio.async_mode, token=token, local_mode=local_mode)
    else:
        if not saml_return_data.votingStatus:
            return render_template("message.html", msg="no_voting_permissions")
        return render_template('index.html', async_mode=socketio.async_mode, token=token, local_mode=local_mode)


@app.route('/admin', methods=['GET'])
def admin():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    if auth.get_settings().get_security_data().get('localMode', False):
        return render_template('local.html', RelayState='admin')
    return redirect(auth.login('admin'))


@app.route('/presenter')
def presenter():
    # TODO: Access control (needed?)
    return render_template('presenter.html', async_mode=socketio.async_mode)


@app.route('/slo')
def slo():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    return redirect(auth.logout())


@app.route('/sls')
def sls():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    return redirect(auth.process_slo())


@app.route('/metadata')
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    sp_metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(sp_metadata)

    if len(errors) > 0:
        return make_response(', '.join(errors), 500)

    resp = make_response(sp_metadata, 200)
    resp.headers['Content-Type'] = 'text/xml'
    return resp


@app.route('/static/secret-voting.js')
def send_js():
    return app.send_static_file('secret-voting.js')


@socketio.on('voting_register', namespace='/test')
def voting_register(message):
    if not vote_registration_data.registration_active:
        emit('register_response',
             {'successful': False})
        return
    fullname = session_fullnames[request.sid]
    userid = session_userids[request.sid]
    with vote_registration_lock:
        if userid in vote_registration_data.registered_userids:
            emit('register_response',
                 {'successful': False})
            return
        vote_registration_data.registered_fullnames.append(fullname)
        vote_registration_data.registered_userids.append(userid)
        vote_registration_data.registered_sessionids.append(request.sid)
        vote_registration_data.registered_sessionids.sort()
        del session_userids[request.sid]
        del session_fullnames[request.sid]
    emit('register_response',
         {'successful': True})
    emit('register_broadcast',
         {'name': fullname,
          'registered_fullnames': vote_registration_data.registered_fullnames},
         broadcast=True)


@socketio.on('admin_voting_reset', namespace='/test')
def admin_voting_reset(message):
    if request.sid not in admins:
        return
    with vote_registration_lock:
        vote_registration_data.registration_active = True
        vote_registration_data.registered_fullnames.clear()
        vote_registration_data.registered_userids.clear()
        vote_registration_data.registered_sessionids.clear()
    emit('reset_broadcast',
         {},
         broadcast=True)


@socketio.on('admin_voting_start', namespace='/test')
def admin_voting_start(message):
    if request.sid not in admins:
        return
    with vote_registration_lock:
        vote_registration_data.registration_active = True
        vote_registration_data.registered_fullnames.clear()
        vote_registration_data.registered_userids.clear()
        vote_registration_data.registered_sessionids.clear()
        vote_registration_data.voting_title = message['voting_title']
        vote_registration_data.voting_link = message['voting_link']
    emit('reset_broadcast',
         {},
         broadcast=True)


@socketio.on('admin_voting_end', namespace='/test')
def admin_voting_end(message):
    if request.sid not in admins:
        return
    if not vote_registration_data.registration_active:
        return
    emit('voting_end_broadcast',
         {},
         broadcast=True)
    with vote_registration_lock:
        vote_registration_data.registration_active = False
        generated_tokens = []
        for sid in vote_registration_data.registered_sessionids:
            token = generate_display_token()
            generated_tokens.append(token)
            generated_tokens.sort()
            emit('generated_token',
                 {'token': token,
                  'voting_title': vote_registration_data.voting_title,
                  'voting_link': vote_registration_data.voting_link},
                 room=sid)
            close_room(sid)
            disconnect(sid=sid)
        vote_registration_data.registered_sessionids.clear()
    # TODO: Close all non-admin/non-presenter sessions?
    # TODO: Following is admin only -> admin rooom
    emit('voting_end_response',
         {'all_users': vote_registration_data.registered_fullnames,
          'all_tokens': generated_tokens})


# TODO: Do we need to handle disconnect?
# @socketio.on('disconnect_request', namespace='/test')
# def disconnect_request():
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
    global admins
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
    with vote_registration_lock:
        if userid in vote_registration_data.registered_userids:
            already_registered = True
        else:
            already_registered = False
        emit('initial_status',
             {'registration_active': vote_registration_data.registration_active,
              'registered_fullnames': vote_registration_data.registered_fullnames,
              'already_registered': already_registered,
              'fullname': fullname,
              'admin_state': admin_state})


# TODO: We could remove the user from the lists here, if we didn't remove the session-user mapping before
#  This would allow re-registration after a disconnect
# @socketio.on('disconnect', namespace='/test')
# def test_disconnect():
#    print('Client disconnected', request.sid)


def generate_token():
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(50))


def generate_display_token():
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for _ in range(8))


if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0")
