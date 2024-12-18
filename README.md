# Introduction
Scrape Mianshi Interview.

# Install
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
# Run
```bash
uvicorn main:app --reload
```
## Run in release
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
