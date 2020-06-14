version: '3.7'

services:
  ballot-box:
    build: ./ballot-box/.
    command: gunicorn --bind 0.0.0.0:5002 app:app --worker-class eventlet
    ports:
      - 127.0.0.1:5002:5002
  vote-registration:
    build: ./vote-registration/.
    command: gunicorn --bind 0.0.0.0:5001 app:app --worker-class eventlet
    ports:
      - 127.0.0.1:5001:5001
