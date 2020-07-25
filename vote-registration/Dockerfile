FROM python:alpine3.7
COPY requirements.txt /
RUN apk add --no-cache libxml2-dev xmlsec-dev \
 && apk add --no-cache --virtual .build-deps gcc musl-dev libffi-dev openssl-dev \
 && pip install -r /requirements.txt \
 && pip install gunicorn \
 && apk del .build-deps
COPY . /app
WORKDIR /app
EXPOSE 80
CMD gunicorn -w1 --bind=0.0.0.0:80 app:app --worker-class eventlet
