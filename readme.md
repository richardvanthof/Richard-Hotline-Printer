## Requirements
- Docker
- Python 3.12 or higher

## Start development server
1. activate virtual env `source printer_env/bin/activate`
2. Run `docker-compose up --build`
3. Open [localhost:80](localhost:80) in your browser

## Build & serve site
1. Build new docker container: `docker run --rm  -p 8000:80 --name printer-container hotline-print-server`
2. Run: `docker run --rm  -p 80:8000 --name printer-container hotline-print-server`