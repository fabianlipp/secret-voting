import json
from typing import List

from flask import Flask, g, request, render_template
from db import my_session_scope, MyDatabase, MyDatabaseSession, Poll, Vote

app = Flask(__name__)

my_database = MyDatabase('sqlite:///./testdb.sqlite')


@app.route('/<poll_id>')
def vote_form(poll_id):
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        poll: Poll = session.get_poll_by_id(poll_id)
        if not poll.active:
            return render_template('message.html', state="not_active", poll_label=poll.label, poll_id=poll_id)
        return render_template('index.html', poll_id=poll_id, poll_label=poll.label, answer_options=poll.answer_options)


@app.route('/<poll_id>/submit_vote', methods=["POST"])
def submit_vote(poll_id):
    token = request.form['token']
    answer = request.form['answer']
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        poll: Poll = session.get_poll_by_id(poll_id)
        vote: Vote = session.get_vote(poll_id, token)
        if not vote:
            return render_template('message.html', poll_label=poll.label, state="token_invalid")
        if not poll.active:
            return render_template('message.html', poll_label=poll.label, state="not_active")
        vote.answer_id = answer
        return render_template('message.html', poll_label=poll.label, state="successful")


@app.route('/admin')
@app.route('/admin/')
def admin_overview():
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        active_polls = session.get_polls(True)
        closed_polls = session.get_polls(False)
        return render_template('admin_overview.html', active_polls=active_polls, closed_polls=closed_polls)


@app.route('/admin/new_poll', methods=['GET', 'POST'])
def new_poll():
    if request.method == 'GET':
        return render_template('admin_new_poll.html')
    elif request.method == 'POST':
        label = request.form["label"]
        request_answers: List[str] = request.form.getlist("answer[]")
        answer_options = [x.strip() for x in request_answers if x.strip()]
        request_tokens = json.loads(request.form["tokens"])
        tokens = request_tokens['tokens']
        with my_session_scope(my_database) as session:  # type: MyDatabaseSession
            poll = session.add_poll(label, True, answer_options, tokens)
            return render_template('admin_message.html', msg="create_success", poll_id = poll.poll_id)


@app.route('/admin/close_poll/<poll_id>')
def close_poll(poll_id):
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        session.close_poll(poll_id)
        return render_template('admin_message.html', msg="poll_closed", poll_id=poll_id)


@app.route('/admin/poll_results/<poll_id>')
def poll_results(poll_id):
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        poll = session.get_poll_by_id(poll_id)
        answer_options = session.get_results(poll_id)
        votes = session.get_votes(poll_id)
        return render_template('admin_poll_results.html', poll=poll, answer_options=answer_options, votes=votes)


if __name__ == '__main__':
    Flask.run(app, debug=True, host="0.0.0.0")
