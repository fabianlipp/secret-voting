This script is based on the example code by Flask-SocketIO (https://github.com/miguelgrinberg/Flask-SocketIO).

Setup:
* Python 3
* Install packages from requirements.txt via pip
* Install one of the packages for socket handling, e.g. eventlet, via pip
* Run app.py


Used headers:
- X-Secret-Voting-Admin: true/false
- X-Secret-Voting-Id: Unique ID for each user
- X-Secret-Voting-Fullname: The fullname of the user, which is displayed to everybody

Rooms:
- Session IDs
- Admins
- Presenters