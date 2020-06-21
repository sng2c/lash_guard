#FROM tiangolo/meinheld-gunicorn-flask:python3.8
FROM tiangolo/uwsgi-nginx-flask:python3.8

COPY ./app/requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

COPY ./app /app

