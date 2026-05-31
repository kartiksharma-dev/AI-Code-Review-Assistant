# 🧠 AI Code Review Assistant
Welcome to the **AI Code Review Assistant**! This is a powerful, full-stack application designed to analyze your code, detect complex patterns, calculate Big-O complexity, and provide intelligent, actionable suggestions to improve your code quality.
---
## ✨ Features
- **Advanced Code Parsing**: Utilizes an AST (Abstract Syntax Tree) parser to dissect your code (functions, classes, imports, and variables) down to its core components.
- **Deep Static Analysis**: Includes an engine with 13 custom rules that check for issues like deep nesting, magic numbers, duplicate code, unused variables, and infinite loops.
- **Complexity Detection**: Automatically calculates **McCabe Cyclomatic Complexity** and uses innovative heuristics to detect **Big-O Time and Space Complexity** (e.g., detecting `O(n!)`, `O(2^n)`, etc.).
- **Intelligent Suggestions**: Provides AI-driven code improvement recommendations. Supports a fallback advanced rule-based engine when LLM API keys (like Anthropic Claude) are not provided.
- **Secure Authentication**: Built-in authentication system with JWT, Flask-Login, and secure OTP email verification (via Gmail/Resend API fallback).
- **Modern UI**: A snappy, responsive React Single-Page Application (SPA) built with Vite and TailwindCSS.
---
## 🏗️ Architecture & Tech Stack
This project follows a clean, layered architecture separating the React frontend from the Flask REST API backend.
**Frontend:**
- React 18
- Vite (Fast HMR)
- TailwindCSS
- Zustand (State Management)
- React Router v6
**Backend:**
- Python / Flask
- SQLite & SQLAlchemy (ORM)
- Flask-Login, Flask-JWT-Extended
- Werkzeug (Security)
---
## 🚀 Getting Started
Follow these steps to run the project locally on your machine.
### Prerequisites
- [Node.js](https://nodejs.org/) (v16 or higher)
- [Python 3.8+](https://www.python.org/)
### 1. Clone the repository
```bash
git clone https://github.com/kartiksharma-dev/AI-Code-Review-Assistant.git
cd AI-Code-Review-Assistant
```
### 2. Backend Setup
Navigate to the root directory and set up the Python environment:
```bash
# Create and activate a virtual environment
python -m venv venv
# On Windows: venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate
# Install dependencies
pip install -r requirements.txt
```
**Environment Variables:**
Create a `.env` file in the root directory (alongside `run.py`) and configure the following:
```env
FLASK_ENV=development
PORT=5000
SECRET_KEY=your_secret_key
JWT_SECRET_KEY=your_jwt_secret_key
# Database
DATABASE_URL=sqlite:///code_review.db
# Email settings for OTP Verification
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```
Start the Flask development server:
```bash
python run.py
```
The backend will run on `http://localhost:5000`.
### 3. Frontend Setup
Open a new terminal window and navigate to the frontend directory:
```bash
cd frontend
# Install Node dependencies
npm install
# Start the Vite development server
npm run dev
```
The frontend will run on `http://localhost:5173`. Open this URL in your browser to start using the application!
---
## 📚 Technical Documentation
For a deep dive into the algorithms, analysis pipeline, and database schema, please refer to the detailed technical documentation included in the repository:
- `project_technical_details.md`
- `Project_Documentation.txt`
---
## 🤝 Contributing
Contributions, issues, and feature requests are welcome! 
Feel free to check [issues page](https://github.com/kartiksharma-dev/AI-Code-Review-Assistant/issues) if you want to contribute.
## 📝 License
This project is licensed under the MIT License.
