# Full-Stack Integration Plan

This plan details how we will establish a secure connection between your newly created React frontend and your original Flask backend.

## Problem Statement

Currently, the React frontend is using a mock service delay to simulate analysis, while the Flask backend uses traditional HTML form-based authentication and is not configured to accept cross-origin requests from a separate React dev server. 

To bridge them, we need to adapt the Flask app into a modern RESTful API with Cross-Origin Resource Sharing (CORS) enabled, while instructing the React frontend to drop its mock layer and communicate with Flask.

## Proposed Changes

### Flask Backend (`c:\Users\snk32\OneDrive\Desktop\AI Code Review Assistant`)

#### [MODIFY] `requirements.txt`
- Add `Flask-CORS` to the dependencies to allow the React app (`localhost:5173`) to talk to Flask (`localhost:5000`).

#### [MODIFY] `app/__init__.py`
- Initialize `CORS(app, supports_credentials=True)` globally. This allows cookies (and thereby session states) to pass seamlessly between the frontend and backend.

#### [MODIFY] `app/routes.py`
We will add parallel REST API endpoints for authentication without destroying your existing HTML routes.
- **[NEW]** `/api/login`: Accepts JSON `{email, password}` and returns a JSON success state after using `login_user(user)`.
- **[NEW]** `/api/signup`: Accepts JSON parameters, creates the user, and returns a JSON success response.
- **[NEW]** `/api/session`: Checks if `current_user.is_authenticated` and returns user data to hydrate the React store.

*(Note: The `/api/analyze` endpoint already exists within `routes.py`, which is perfectly built to connect with the frontend!)*

---

### React Frontend (`c:\Users\snk32\OneDrive\Desktop\frontend for the code review assitant`)

#### [MODIFY] `src/services/api.js`
- Set `const USE_MOCK = false;` to route traffic to your Flask server.
- Configure `api.defaults.withCredentials = true;` to ensure session cookies are passed along.
- Point the POST targets to `/api/login`, `/api/signup`, and `/api/analyze`. 

#### [MODIFY] `src/App.jsx`
- Introduce a check on initial load to check `/api/session`. This way, if a user closes their tab and reopens it, React fetches their session state from Flask and keeps them logged in.

## Open Questions

> [!IMPORTANT]  
> Are there any other specific models or integrations from your backend (e.g., Anthropic API keys in config) that you want to enable right now, or should we stick to just connecting the existing authentication and analysis pipeline? 

## Verification Plan

### Automated Tests
- I will run `npm install flask-cors` directly in the backend repository and ensure the server runs.

### Manual Verification
- We will boot up both the Flask backend and the Vite frontend simultaneously.
- A user will be created through the React dashboard, testing the `/api/signup` route, and an actual code snippet will be submitted to the Flask backend's logic engine.
