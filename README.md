This a PoC of a RAG chatbot using Gemini.

Please add your Gemini API key, weaviate API key, Postgres host, user, db_name and password, Mongo use, password and cluster name, and Milvis URL, User and password in the .env file in the backend folder.

To run the frontend:
```
cd frontend
npm install
npm run dev
```

To run backend:
```
cd ../backend
python -m venv venv
source venv/bin/activate (On windows, use: venv\scripts\activate)
pip install -r requirements.txt
python app.py
```
Here are some of the screenshots of the outcome.

Old Attachments:
<br />

<img width="1465" alt="Screenshot 2025-04-04 at 5 45 52 AM" src="https://github.com/user-attachments/assets/0a1a7dac-bc3f-4211-a94e-9ece6b08616e" />
<img width="1465" alt="Screenshot 2025-04-04 at 5 13 43 AM" src="https://github.com/user-attachments/assets/d4bfd93b-ed6a-4fbc-a24d-b1683ff6d851" />
<img width="206" alt="Screenshot 2025-04-04 at 5 11 50 AM" src="https://github.com/user-attachments/assets/663c7c77-1f1e-4bd2-9008-dc454ccfcd1a" />
<img width="206" alt="Screenshot 2025-04-04 at 5 11 38 AM" src="https://github.com/user-attachments/assets/579010f0-526e-4301-9e31-3b7b73e0dc59" />

<br />
<br />
<br />
<br />
<br />
New Attachments with RPC Implementation:
<br />

<img width="1465" alt="Screenshot 2025-04-04 at 8 17 17 PM" src="https://github.com/user-attachments/assets/3e4b8117-f821-4a74-b6ee-3e8b56b9b5b5" />
<img width="1465" alt="Screenshot 2025-04-04 at 8 11 40 PM" src="https://github.com/user-attachments/assets/67bdb712-98d4-4d37-9611-4acdb66d4ef0" />






