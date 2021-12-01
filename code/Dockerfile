FROM python:3.8-slim-buster

ENV VERSION="0.2.0"

# install dependencies
COPY requirements.txt /code/requirements.txt
RUN python -m pip install --upgrade --no-cache-dir pip==21.1.* setuptools==57.0.0 gunicorn==20.1.* && \
    python -m pip install --no-cache-dir -r /code/requirements.txt

# copy the source code into the container
COPY . /code
RUN cd /code/query-engine && mkdir -p Config
WORKDIR /code/query-engine

# start the Flask app
ENTRYPOINT ["gunicorn", "-c", "/code/gunicorn.conf.py", "flaskr:app"]
