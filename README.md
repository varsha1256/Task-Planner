# Time Management App (Flask + HTML/CSS/JS)

A hands-on DevOps-friendly project where you can:
- Add daily tasks with title and message
- Schedule tasks with date/time
- Mark tasks done using checkbox
- Delete tasks
- Run locally and in Docker

## Tech stack
- Python 3.12+
- Flask
- SQLite (file-based DB)
- HTML, CSS, Vanilla JavaScript
- Docker

## Project structure

```text
.
|-- app.py
|-- requirements.txt
|-- Dockerfile
|-- .dockerignore
|-- templates/
|   `-- index.html
`-- static/
    |-- styles.css
    `-- app.js
```

## Run locally

1. Open terminal in project folder.
2. Create virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Start app:

```powershell
python app.py
```

5. Open browser:

```text
http://localhost:5000
```

## Build and run with Docker

1. Build image:

```powershell
docker build -t time-management-app .
```

2. Run container:

```powershell
docker run -d -p 5000:5000 --name time-management-app time-management-app
```

3. Open app:

```text
http://localhost:5000
```

4. Stop container:

```powershell
docker stop time-management-app
```

5. Remove container:

```powershell
docker rm time-management-app
```

## DevOps practice ideas
- Add `docker-compose.yml` and mount persistent volume for database
- Add GitHub Actions for lint/test/build Docker image
- Add Nginx reverse proxy container
- Push image to Docker Hub
- Deploy to cloud VM (Azure/AWS/GCP)
