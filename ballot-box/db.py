import enum
from contextlib import contextmanager
from sqlite3 import Connection as SQLite3Connection
from typing import List

import sqlalchemy.engine
from sqlalchemy import Column, Integer, String, ForeignKey, event, create_engine, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session, Query
from sqlalchemy.sql.expression import literal_column

Base = declarative_base()


class PollState(enum.Enum):
    prepared = 0
    active = 1
    closed = 2


class Poll(Base):
    __tablename__ = "poll"
    poll_id = Column(Integer, primary_key=True)
    state = Column(Enum(PollState), nullable=False, default=PollState.prepared)
    label = Column(String(1024), nullable=False)

    answer_options: List = relationship("AnswerOption")
    votes: List = relationship("Vote")

    #def __init__(self, chat_id, username, first_name, last_name, time_start=None):
    #    self.chat_id = chat_id
    #    self.username = username
    #    self.first_name = first_name
    #    self.last_name = last_name

    #    if time_start is not None:
    #        self.time_start = time_start
    #    else:
    #        self.time_start = int(time.time())
    #    self.last_msg = None

    #def __repr__(self):
    #    return "<User(chat_id='%s', username='%s', first_name='%s', last_name='%s')>" \
    #           % (self.chat_id, self.username, self.first_name, self.last_name)


class AnswerOption(Base):
    __tablename__ = "answer_option"
    answer_id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey(Poll.poll_id), nullable=False)
    label = Column(String(1024), nullable=False)

    def __init__(self, label):
        self.label = label


class Vote(Base):
    __tablename__ = "vote"
    poll_id = Column(Integer, ForeignKey(Poll.poll_id), primary_key=True)
    token = Column(String(20), primary_key=True)
    answer_id = Column(Integer, ForeignKey(AnswerOption.answer_id), nullable=True)
    answer_option = relationship("AnswerOption")

    def __init__(self, token):
        self.answer_id = None
        self.token = token


class MyDatabaseSession:
    session = None

    def __init__(self, session: Session):
        self.session = session

    def commit(self):
        self.session.commit()

    def close(self):
        self.session.close()

    def rollback(self):
        self.session.rollback()

    def get_poll_by_id(self, poll_id: int) -> Poll:
        return self.session.query(Poll).filter(Poll.poll_id == poll_id).first()

    def get_polls(self, state: PollState) -> List[Poll]:
        return self.session.query(Poll).filter(Poll.state == state).all()

    def add_poll(self, label: str, answer_options: List[str]) -> Poll:
        poll = Poll()
        poll.label = label
        poll.state = PollState.prepared
        for answer_label in answer_options:
            poll.answer_options.append(AnswerOption(answer_label))
        self.session.add(poll)
        self.session.flush()
        return poll

    def activate_poll(self, poll_id: int, tokens: List[str]) -> bool:
        poll = self.get_poll_by_id(poll_id)
        if poll is None or poll.state != PollState.prepared:
            return False
        poll.state = PollState.active
        for token in tokens:
            poll.votes.append(Vote(token))
        return True

    def close_poll(self, poll_id: int):
        poll: Poll = self.get_poll_by_id(poll_id)
        poll.state = PollState.closed

    def get_vote(self, poll_id, token) -> Vote:
        return self.session.query(Vote).filter(Vote.poll_id == poll_id, Vote.token == token).first()

    def get_votes(self, poll_id) -> List[Vote]:
        return self.session.query(Vote).filter(Vote.poll_id == poll_id).all()

    def get_results(self, poll_id) -> List:
        # This union of queries simulates a full outer join
        q1: Query = self.session.query(Vote.answer_id, AnswerOption.label, func.count(Vote.token).label("count"))\
            .join(AnswerOption, isouter=True)\
            .filter(Vote.poll_id == poll_id).group_by(Vote.answer_id)
        q2: Query = self.session.query(AnswerOption.answer_id, AnswerOption.label, literal_column("0").label("count"))\
            .join(Vote, isouter=True)\
            .filter(AnswerOption.poll_id == poll_id, Vote.token.is_(None))
        return q1.union(q2).all()


class MyDatabase:
    db_engine = None

    def __init__(self, database_url):
        self.db_engine = create_engine(database_url, pool_pre_ping=True, echo=False)
        try:
            Base.metadata.create_all(self.db_engine)
            # print("Tables created")
        except Exception as e:
            print("Error occurred during Table creation!")
            print(e)
        self.Session = sessionmaker(bind=self.db_engine)

    def get_session(self) -> MyDatabaseSession:
        return MyDatabaseSession(self.Session())


@contextmanager
def my_session_scope(db: MyDatabase):
    """Provide a transactional scope around a series of operations."""
    session = db.get_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


@event.listens_for(sqlalchemy.engine.Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


def db_test(database_url):
    db = MyDatabase(database_url)
    with my_session_scope(db) as session:  # type: MyDatabaseSession
        poll1 = session.add_poll("test-poll", ["ja", "nein"], )
        poll2 = session.add_poll("test-poll-beta", ["ja", "nein", "vielleicht"])
        poll3 = session.add_poll("test-poll-gamma", ["ja", "nein", "vielleicht"])
        session.activate_poll(poll1.poll_id, ["abc1", "abc2"])
        session.activate_poll(poll2.poll_id, ["def1", "def2", "def3"])

#db_test('sqlite:///./testdb.sqlite')
