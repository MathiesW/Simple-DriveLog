FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# create folder for DB
RUN mkdir -p /app/data

EXPOSE 5000

CMD ["python", "app.py"]
