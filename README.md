This a simple PoC of a chatbot using Gemini.

Please add your Gemini API key and weaviate API key in the .env file in the backend folder.

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