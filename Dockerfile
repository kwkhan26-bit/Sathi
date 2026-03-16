FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Then create `requirements.txt` in the same folder:
```
google-genai==1.67.0
fastapi==0.135.1
uvicorn==0.42.0
python-dotenv==1.2.2
websockets==16.0