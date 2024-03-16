FROM python:3.12-slim

WORKDIR /opt/streamlit

COPY requirements.txt .

RUN pip install -r requirements.txt

ENTRYPOINT [ "streamlit" ]
CMD [ "run", "app.py" ]
