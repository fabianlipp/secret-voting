#!/bin/bash

wget https://github.com/twbs/bootstrap/releases/download/v4.5.0/bootstrap-4.5.0-dist.zip
unzip bootstrap-4.5.0-dist.zip

cp bootstrap-4.5.0-dist/css/bootstrap.min.css ballot-box/static/
cp bootstrap-4.5.0-dist/js/bootstrap.bundle.min.js ballot-box/static/

cp bootstrap-4.5.0-dist/css/bootstrap.min.css vote-registration/static/
cp bootstrap-4.5.0-dist/js/bootstrap.bundle.min.js vote-registration/static/

rm bootstrap-4.5.0-dist.zip
rm -r bootstrap-4.5.0-dist
