FROM python:3.6-alpine
RUN echo "test"
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN chmod 755 app.py
CMD python3 ./app.py
