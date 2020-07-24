version: '3.7'

services:
  ballot-box:
    build: ./ballot-box/.
    ports:
      - 127.0.0.1:5002:80
    environment:
    #  - DB_URL=sqlite:///./testdb.sqlite
    #  - DB_URL=mysql+pymysql://user:password@host/database
  vote-registration:
    build: ./vote-registration/.
    ports:
      - 127.0.0.1:5001:80
