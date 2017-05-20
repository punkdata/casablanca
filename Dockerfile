# docker build --rm=true -t casablanca .

FROM python:2-alpine
MAINTAINER "Angel Rivera"

RUN mkdir -p /opt/casablanca
COPY stream.py config.json requirements.txt /opt/casablanca/
RUN pip install -r /opt/casablanca/requirements.txt
CMD ["python","/opt/casablanca/stream.py"]
