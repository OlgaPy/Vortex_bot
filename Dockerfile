FROM python:3.11-slim-buster

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

ADD src /app/src

WORKDIR /app/src

CMD ["python", "app.py"]