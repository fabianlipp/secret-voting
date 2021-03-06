import json
import os
from typing import List

from flask import Flask, request, render_template
from flask_babel import Babel
from db import my_session_scope, MyDatabase, MyDatabaseSession, Poll, Vote, PollState, PollType, AnswerOption

app = Flask(__name__)

babel = Babel(app)

my_database = MyDatabase(os.getenv('DB_URL', 'sqlite:///./db.sqlite'))

EMPTY_VOTE = 'Leerer Stimmzettel'

app.config['LANGUAGES'] = [
    'de',
    'en',
    'es',
    'fr'
]

@app.route('/')
def main():
    return render_template('message.html', state="no_poll_id")


@app.route('/<poll_id>')
def vote_form(poll_id):
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        poll: Poll = session.get_poll_by_id(poll_id)
        if poll.state == PollState.prepared:
            return render_template('message.html', state="not_active", poll_label=poll.label, poll_id=poll_id)
        elif poll.state == PollState.active:
            return render_template('index.html', poll=poll)
        else:
            poll_results = session.get_results(poll_id)
            return render_template('poll_results.html', poll=poll, poll_results=poll_results)


@app.route('/<poll_id>/submit_vote', methods=["POST"])
def submit_vote(poll_id):
    token = request.form['token']
    answers = [int(x) for x in request.form.getlist('answer')]
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        poll: Poll = session.get_poll_by_id(poll_id)
        vote: Vote = session.get_vote(poll_id, token)
        if not vote:
            return render_template('message.html', poll_label=poll.label, state="token_invalid")
        if poll.state != PollState.active:
            return render_template('message.html', poll_label=poll.label, state="not_active")
        # Validation of vote
        if len(answers) > poll.numVotes:
            return render_template('message.html', poll_label=poll.label, state="too_many_votes")
        if len(answers) > 1 and session.contains_exclusive_answer(answers):
            return render_template('message.html', poll_label=poll.label, state="invalid_combination")
        vote.answerOptions.clear()
        vote.association_ids.extend(answers)
        return render_template('message.html', poll_label=poll.label, state="successful")


@app.route('/admin')
@app.route('/admin/')
def admin_overview():
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        prepared_polls = session.get_polls(PollState.prepared)
        active_polls = session.get_polls(PollState.active)
        closed_polls = session.get_polls(PollState.closed)
        return render_template('admin_overview.html', prepared_polls=prepared_polls, active_polls=active_polls,
                               closed_polls=closed_polls)


@app.route('/admin/new_poll', methods=['GET', 'POST'])
def new_poll():
    if request.method == 'GET':
        return render_template('admin_new_poll.html', poll_types=PollType.__members__.items())
    elif request.method == 'POST':
        label = request.form["label"]
        poll_type = PollType[request.form["type"]]
        if poll_type == PollType.multiPersonVote:
            num_votes = request.form["numVotes"]
        else:
            num_votes = 1
        request_answers: List[str] = request.form.getlist("answer[]")
        answer_options = [x.strip() for x in request_answers if x.strip()]
        with my_session_scope(my_database) as session:  # type: MyDatabaseSession
            poll = session.add_poll(label, poll_type, num_votes, answer_options)
            if poll_type == PollType.multiPersonVote:
                answer_option_empty = AnswerOption(EMPTY_VOTE)
                answer_option_empty.exclusive = True
                poll.answer_options.append(answer_option_empty)
            return render_template('admin_message.html', msg="create_success", poll_id=poll.poll_id)


@app.route('/admin/activate_poll/<poll_id>', methods=['GET', 'POST'])
def activate_poll(poll_id):
    if request.method == 'GET':
        with my_session_scope(my_database) as session:  # type: MyDatabaseSession
            poll = session.get_poll_by_id(poll_id)
            if poll is None or poll.state != PollState.prepared:
                return render_template('admin_message.html', msg="poll_not_prepared")
            return render_template('admin_activate_poll.html', label=poll.label, poll_id=poll.poll_id)
    elif request.method == 'POST':
        request_tokens = json.loads(request.form["tokens"])
        tokens = request_tokens['tokens']
        attendees = request_tokens['users']
        with my_session_scope(my_database) as session:  # type: MyDatabaseSession
            if session.activate_poll(poll_id, tokens, attendees):
                return render_template('admin_message.html', msg="poll_activated", poll_id=poll_id)
            else:
                return render_template('admin_message.html', msg="poll_activate_error", poll_id=poll_id)


@app.route('/admin/close_poll/<poll_id>')
def close_poll(poll_id):
    with my_session_scope(my_database) as session:  # type: MyDatabaseSession
        session.close_poll(poll_id)
        return render_template('admin_message.html', msg="poll_closed", poll_id=poll_id)

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])

@app.context_processor
def inject_config_vars():
    return dict(
        AVAILABLE_LANGUAGES=app.config['LANGUAGES'],
        CURRENT_LANGUAGE=request.accept_languages.best_match(app.config['LANGUAGES'])
    )

if __name__ == '__main__':
    Flask.run(app, debug=True, host="0.0.0.0")
