# Vehicle Parking Management System

A Flask-based web application for managing vehicle parking lots with user and admin roles.

## Features

### 👤 User
- Register/Login
- View and search nearby parking lots by pin code
- Book and release parking spots
- View recent parking history

### 🛠 Admin
- Dashboard to view all lots and occupancy
- Add, edit, delete parking lots
- View all users
- Search lots by pin code or user ID

## Technologies Used
- **Flask** (Backend)
- **SQLite** (Database)
- **HTML + Jinja2 + Bootstrap** (Frontend)
- **Flask-CORS** (For cross-origin requests)
- **Session-based auth** (Flask session)

## Setup Instructions

```bash
# Clone the repository
git clone https://github.com/yourusername/vehicle-parking-app.git
cd vehicle-parking-app

# (Optional) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

## Project Structure

```
/backend/
  └── models/
      └── db.py
/templates/
  └── *.html
app.py
```

## License
This project is for educational use. Modify it as needed.
