FROM python:2.7

COPY . /opt/djsonb
WORKDIR /opt/djsonb

RUN pip install -e .
CMD python run_tests.py
