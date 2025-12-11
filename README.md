# Cashflow-FP  
#### Video Demo: <URL HERE>  
#### Author: Franco (francot77)

## Description

Cashflow-FP is a lightweight personal cash-flow management web application built with Python and Flask. It allows authenticated users to record incomes and expenses, browse their transaction history, and manage essential financial data with clarity and simplicity. The goal of this project is to demonstrate solid backend fundamentals, clean code organization, and practical full-stack design appropriate for the CS50 Final Project.

The project began as an extension of ideas from CS50’s Finance problem set, but it quickly became necessary to restructure the app to avoid concentrating all logic in a single large `app.py` file. To maintain readability and modularity, the application is split into smaller, dedicated modules such as `auth.py`, `views.py`, and `api.py`. These modules communicate through Flask’s routing and database helpers, keeping responsibilities separated and the codebase far easier to maintain.

During development, ChatGPT was used to help refine architectural structure and naming conventions, specifically to keep the code modular and avoid bloated files. All implementation and logic were written and verified manually. This assistance is cited here per CS50’s academic honesty guidelines.

---

## Features

**User authentication**  
Users can register, log in, and log out securely. Passwords are hashed, and Flask sessions handle authentication status. These routes and logic live in `auth.py`.

**Transaction management (CRUD)**  
Users can add, edit, delete, and view individual transactions. Each item stores amount, date, type (income or expense), category, and optional notes. The core logic for these operations resides in `views.py`.

**API endpoints**  
A dedicated `api.py` exposes lightweight JSON endpoints, enabling the backend to be consumed by external clients—particularly a mobile version of the app.

**SQLite persistence**  
The app uses a local SQLite database (`cashflow.db`). Schema definitions live in `schema.sql`, and `init_db.py` initializes the database. All connection helpers and query shortcuts are contained in `db.py`.

**HTML templates (Jinja)**  
The UI uses server-rendered templates placed in the `templates/` directory, with basic styling in `static/css/`. The interface is intentionally simple to keep the focus on backend logic and correctness.

---

## Project Structure
```

cashflow-fp/
│
├── app.py # Application entry point, Flask setup, blueprint registration
├── auth.py # User authentication and session logic
├── views.py # Web routes for pages and transaction CRUD
├── api.py # JSON API endpoints for external/mobile consumption
├── db.py # Database utilities and connection helpers
├── init_db.py # Script to initialize SQLite database
├── schema.sql # Database schema definition
│
├── templates/ # Jinja2 HTML templates
│ ├── add.html
│ ├── categories.html
│ ├── edit.html
│ ├── index.html
│ ├── layout.html
│ ├── login.html
│ ├── register.html
│ └── summary.html
│
├── static/
│ └── css/
│ └── styles.css
│
└── cashflow.db # Example SQLite database file (can be regenerated)




This layout keeps responsibilities separated and prevents any one file from becoming unmanageably large.
```
---

## How to Run the Project

1. **Clone the repository**
git clone https://github.com/francot77/cashflow-fp
cd cashflow-fp

2. **Set up a virtual environment**
python -m venv venv
source venv/bin/activate

(On Windows: `venv\Scripts\activate`)

3. **Install dependencies**
pip install -r requirements.txt

4. **Initialize the database** (if needed)
python init_db.py

5. **Start the development server**
export FLASK_APP=app.py
flask run

Then visit:  
**http://127.0.0.1:5000**

---

## Mobile App (Bonus Work)

As an additional component of this project, a mobile application was created using **Expo (React Native)**. The mobile client consumes the same Flask backend through the JSON API. It supports:

- Logging in  
- Viewing transactions  
- Adding new transactions  

This demonstrates how the backend can serve multiple platforms and how the API routes enable cross-client compatibility. The mobile version is not required for CS50, but it showcases further development potential.

---

## Design Decisions and Rationale

- **Modular architecture**: The project avoids a monolithic `app.py` by splitting features across multiple modules. This improves maintainability and clarity.  
- **SQLite**: Chosen for simplicity and full compatibility with CS50’s environment.  
- **Server-rendered templates**: Keeps the project aligned with CS50 expectations and avoids excessive complexity unrelated to the goals of the course.  
- **API layer**: Added to support the mobile bonus project and to demonstrate separation between backend logic and presentation.  
- **Minimalist UI**: The frontend remains intentionally simple, letting the backend logic and data-flow design stand out.

---

## Future Improvements

- Charts, graphs, and financial summaries  
- CSV/PDF export  
- Category analytics  
- Migration to a cloud-hosted SQL database  
- JWT authentication for external/mobile clients  
- Unit tests and integration tests

---

## Academic Honesty Statement

This project was designed and implemented by me. I used ChatGPT (OpenAI) only for structural guidance and organizational clarity when modularizing the Flask application. All logic, routes, queries, templates, and code were manually written and verified.
