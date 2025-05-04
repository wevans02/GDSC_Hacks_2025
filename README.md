# 🧑‍⚖️ Paralegal AI – Toronto Bylaw Assistant

This project provides a web interface to query and understand Toronto Municipal Code bylaws. It uses a **Flutter frontend**, a **Flask (Python) backend**, **MongoDB Atlas** for data storage and vector search, and the **Google Gemini API** for generating answers based on retrieved bylaw context.

---

## ✨ Features

- **Natural Language Queries**  
  Ask questions about Toronto bylaws in plain English.

- **Retrieval-Augmented Generation (RAG)**  
  Finds relevant bylaw sections using MongoDB Atlas Vector Search before generating an answer.

- **AI-Powered Answers**  
  Uses the Google Gemini API to synthesize information from retrieved bylaws and answer user questions.

- **Source Linking**  
  Provides links to the original PDF source documents for the relevant bylaw chapters.

- **Web Interface**  
  Clean and responsive UI built with Flutter.

---

## 🧰 Technology Stack

- **Frontend**: Flutter (Dart)  
- **Backend**: Flask (Python)  
- **Database**: MongoDB Atlas (Vector Search)  
- **AI Model**: Google Gemini API

### Core Python Libraries
`pymongo`, `google-generativeai`, `Flask`, `python-dotenv`, `sentence-transformers`, `PyMuPDF (fitz)`, `beautifulsoup4`

### Core Flutter Libraries
`http`, `flutter_markdown`, `url_launcher`, `google_fonts`, `flutter_animate`, `loading_animation_widget`

---

## 📁 Project Structure

GDSC_Hacks_2025/
├── flask_api/ # Backend Flask application
│ ├── templates/ # (If any Flask templates exist)
│ ├── static/ # (If any static files exist)
│ ├── venv/ # Python virtual environment
│ ├── .env # Environment variables (DO NOT COMMIT)
│ ├── requirements.txt # Python dependencies
│ ├── app.py # Main Flask app
│ ├── create_database.py
│ ├── embed_vectors.py
│ ├── parse_html.py
│ ├── query_database.py
│ ├── python_to_gemini.py
│ ├── chunk_text.py
│ ├── lawmcode.htm # Source HTML file (manual download)
│ └── ...
│
├── flutter_frontend/ # Frontend Flutter app
│ ├── lib/
│ │ └── main.dart
│ ├── assets/
│ ├── web/
│ ├── pubspec.yaml
│ └── ...
│
└── README.md # This file


## ⚙️ Setup Instructions

### ✅ Prerequisites

- Git
- Python 3.8+ and pip
- Flutter SDK
- A MongoDB Atlas Account (Free M0 Tier)
- A Google Gemini API Key (get it from Google AI Studio)

---

### 🐍 1. Backend Setup (`flask_api`)

```bash
cd flask_api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
🧾 Download Bylaw Source HTML
Go to: https://www.toronto.ca/legdocs/municode/toronto-code-chapters.shtml

Save the HTML content as lawmcode.htm in the flask_api folder.

🔐 Create a .env file

DATABASE_LOGIN=username:password
GEMINI_API_KEY=your_gemini_api_key
🏗 Populate the Database

python create_database.py
⚠️ This script downloads many PDFs, embeds content, and uploads to MongoDB. It may take some time.

💻 2. Frontend Setup (flutter_frontend)

cd ../flutter_frontend
flutter pub get
🔧 Configure Backend URL
Edit lib/main.dart:


final uri = Uri.parse('http://127.0.0.1:5000/api/query'); // For local dev
For deployment, change this to your hosted backend URL.

🔑 Environment Variables
Set these for the backend via .env (locally) or platform secrets (in production):

DATABASE_LOGIN: MongoDB Atlas login (username:password)

GEMINI_API_KEY: Google Gemini API key

▶️ Running Locally
Start the Flask Backend

cd flask_api
source venv/bin/activate  # if not already activated
flask run --host=0.0.0.0  # Runs on port 5000
Start the Flutter Frontend

cd ../flutter_frontend
flutter run -d chrome
Ensure the API URL in main.dart points to your local backend.

🚀 Deployment
Frontend (Flutter Web)

flutter build web --release
Host build/web on:

Firebase Hosting

GitHub Pages

Netlify

Vercel

Render

Backend (Flask)
Deploy flask_api to:

Render

PythonAnywhere

Fly.io

Google Cloud Run

AWS (free tier)

Use Gunicorn (included in requirements.txt) and set debug=False.

🔒 Deployment Security Tips
CORS: Only allow frontend domain.

Secrets: Use environment variables. Never commit .env.

DB Access: Restrict MongoDB Atlas to your backend IPs.

HTTPS: Always enable HTTPS in production.

🤝 Contributing
(Add guidelines if you'd like others to contribute)

📝 License
(Add your license here, e.g., MIT License)