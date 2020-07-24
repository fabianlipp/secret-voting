#!/bin/bash

mkdir .deps

## Bootstrap

wget https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/css/bootstrap.min.css -O .deps/bootstrap.min.css
wget https://stackpath.bootstrapcdn.com/bootstrap/4.5.0/js/bootstrap.bundle.min.js -O .deps/bootstrap.bundle.min.js

cp .deps/bootstrap.min.css ballot-box/static/
cp .deps/bootstrap.bundle.min.js ballot-box/static/

cp .deps/bootstrap.min.css vote-registration/static/
cp .deps/bootstrap.bundle.min.js vote-registration/static/

## JQuery

wget https://code.jquery.com/jquery-1.12.4.min.js -O .deps/jquery-1.12.4.min.js

cp .deps/jquery-1.12.4.min.js ballot-box/static/
cp .deps/jquery-1.12.4.min.js vote-registration/static/

## Socket.io

wget https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.2.0/socket.io.js -O .deps/socket.io.js

cp .deps/socket.io.js vote-registration/static/

# Clear

rm -r .deps
