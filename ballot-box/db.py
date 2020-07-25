import enum
from contextlib import contextmanager
from sqlite3 import Connection as SQLite3Connection
from typing import List

import sqlalchemy.engine
from sqlalchemy import Column, Integer, String, ForeignKey, event, create_engine, func, Enum, Table, \
    ForeignKeyConstraint, Boolean
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session, Query
from sqlalchemy.sql.expression import literal_column

Base = declarative_base()


class PollState(enum.Enum):
    prepared = 0
    active = 1
    closed = 2


class PollType(enum.Enum):
    singleVote = 0
    multiPersonVote = 1


class Poll(Base):
    __tablename__ = "poll"
    poll_id = Column(Integer, primary_key=True)
    state = Column(Enum(PollState), nullable=False, default=PollState.prepared)
    label = Column(String(1024), nullable=False)
    type = Column(Enum(PollType), nullable=False, default=PollType.singleVote)
    numVotes = Column(Integer, nullable=False, default=1)

    answer_options: List = relationship("AnswerOption")
    votes: List = relationship("Vote")
    attendees: List = relationship("Attendee")


association_table = Table('voteAnswers', Base.metadata,
                          Column('poll_id', Integer, primary_key=True),
                          Column('token', String(20), primary_key=True),
                          Column('answer_id', Integer, ForeignKey('answer_option.answer_id'), primary_key=True),
                          ForeignKeyConstraint(('poll_id', 'token'), ('vote.poll_id', 'vote.token'))
                          )


class VoteAnswers(Base):
    __table__ = association_table
    vote = relationship("Vote", backref="association_recs")


class AnswerOption(Base):
    __tablename__ = "answer_option"
    answer_id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey(Poll.poll_id), nullable=False)
    label = Column(String(1024), nullable=False)
    exclusive = Column(Boolean, nullable=False, default=False)

    votes = relationship("Vote", secondary=association_table)

    def __init__(self, label):
        self.label = label


class Vote(Base):
    __tablename__ = "vote"
    poll_id = Column(Integer, ForeignKey(Poll.poll_id), primary_key=True)
    token = Column(String(20), primary_key=True)

    answerOptions = relationship("AnswerOption", secondary=association_table)
    association_ids = association_proxy(
        "association_recs", "answer_id",
        creator=lambda aid: VoteAnswers(answer_id=aid))

    def __init__(self, token):
        self.token = token


class Attendee(Base):
    __tablename__ = "attendee"
    attendee_id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey(Poll.poll_id))
    name = Column(String(255))

    def __init__(self, name):
        self.name = name


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

    def add_poll(self, label: str, poll_type: PollType, num_votes: int, answer_options: List[str]) -> Poll:
        poll = Poll()
        poll.label = label
        poll.state = PollState.prepared
        poll.type = poll_type
        poll.numVotes = num_votes
        for answer_label in answer_options:
            poll.answer_options.append(AnswerOption(answer_label))
        self.session.add(poll)
        self.session.flush()
        return poll

    def activate_poll(self, poll_id: int, tokens: List[str], attendees: List[str]) -> bool:
        poll = self.get_poll_by_id(poll_id)
        if poll is None or poll.state != PollState.prepared:
            return False
        poll.state = PollState.active
        for token in tokens:
            poll.votes.append(Vote(token))
        for attendee in attendees:
            poll.attendees.append(Attendee(attendee))
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
        q1: Query = self.session.query(AnswerOption.answer_id, AnswerOption.label, func.count(Vote.token).label("count"))\
            .select_from(Vote)\
            .join(VoteAnswers, isouter=True)\
            .join(AnswerOption, isouter=True)\
            .filter(Vote.poll_id == poll_id).group_by(AnswerOption.answer_id)
        q2: Query = self.session.query(AnswerOption.answer_id, AnswerOption.label, literal_column("0").label("count"))\
            .join(VoteAnswers, isouter=True)\
            .filter(AnswerOption.poll_id == poll_id, VoteAnswers.token.is_(None))
        return q1.union(q2).all()

    def contains_exclusive_answer(self, answer_options: List[Integer]) -> bool:
        return self.session.query(AnswerOption)\
                   .filter(AnswerOption.exclusive)\
                   .filter(AnswerOption.answer_id.in_(answer_options))\
                   .first() is not None


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
