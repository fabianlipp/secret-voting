This script is based on the example code by Flask-SocketIO (https://github.com/miguelgrinberg/Flask-SocketIO).

## Setup

```
cd secret-voting
docker-compose build --no-cache && docker-compose up -d
```


## Configuration

The SAML ACS expects the Attributes `userid`, `fullname`, `is_admin` (opt.), `is_presenter` (opt.)


## Usage

You can watch three different views:

- voter `<url>/`
- election officer `<url>/admin`
- presentation `<url>/presenter`


## Details

socket.io rooms:
- Session IDs
- Admins
- Presenters
