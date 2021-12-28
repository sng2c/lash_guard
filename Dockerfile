FROM jazzdd/alpine-flask:python3
COPY ./app/requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY ./nginx_custom.conf /etc/nginx/nginx.conf
COPY ./app /app

