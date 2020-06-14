# Setup

```
git clone https://github.com/fabianlipp/secret-voting/
cd secret-voting
cp docker-compose.yml{,.tpl}
cp vote-registration/settings.json{,.tpl}
# edit settings
docker-compose build && docker-compose up -d
```

# Vote Registration

## Configuration

The SAML ACS expects the Attributes `userid`, `fullname`, `is_admin` (opt.), `is_presenter` (opt.)

## Usage

You can watch three different views:

- voter `<url>/`
- election officer `<url>/admin`
- presentation `<url>/presenter`

# Ballot Box

## Usage

t.b.d

## Details

This script is based on the example code by Flask-SocketIO (https://github.com/miguelgrinberg/Flask-SocketIO).

socket.io rooms:
- Session IDs
- Admins
- Presenters
