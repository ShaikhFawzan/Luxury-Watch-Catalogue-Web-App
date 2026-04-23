# Luxury Watch Catalogue Web App

## Overview

A full-stack web application built with **Python Flask** for browsing, managing, and discovering luxury watches. Users can search a curated catalogue, manage personal wishlists, and receive recommendations, while administrators can manage catalogue inventory through role-based controls.

## Live Demo
[Launch Application](https://luxury-watch-catalogue-web-app.onrender.com)   

## Key Highlights

- Full-stack web development using **Python, Flask, HTML, CSS, Jinja2**
- Role-based authentication system (**Admin / User**)
- Search, filtering, and sorting across catalogue data
- Wishlist system with full CRUD functionality
- Watch comparison feature with focus on clean, intuitive layout
- Recommendation engine for similar watches
- Admin dashboard for managing catalogue entries
- Team-based software engineering project with UML design planning

---

## Features

### User Features
- Signup, login, and logout
     - Optional guest functionality
- Browse complete watch catalogue with over 600 watches
- Search by brand, model, and keywords
- Sort by price, brand, and model
- Add / remove watches from wishlist
- Receive similar watch recommendations

### Admin Features
- Add new watches to catalogue
- Edit existing watch entries
- Remove watches from catalogue
- Maintain structured product data

### Technical Features
- Flask session-based authentication
- Jinja2 template rendering
- CSV-based data persistence
- Error handling and input validation
- Responsive and clean UI design

---

## Tech Stack

| Category | Technologies |
|--------|-------------|
| Backend | Python, Flask |
| Frontend | HTML, CSS, Jinja2 |
| Data Storage | CSV Files |
| Authentication | Flask Sessions |
| Tools | Git, GitHub, Render |

---

## Project Structure

```
Luxury-Watch-Catalogue-Web-App/

├── Diagrams/                      # UML and design diagrams
│   └── UML_Diagram.pdf
├── data/                          # CSV data files
│   ├── reviews.csv
│   ├── testdata.csv
│   ├── users.csv
│   └── watches.csv
├── scripts/                       # Build and deployment scripts
│   ├── build.bat
│   └── build.sh
├── static/                        # Static assets
│   └── images/                    # Images and media files
│       ├── adminEdit.png
│       ├── catalogue.png
│       ├── login.png
│       ├── tools/
│       │   └── image_mapper.py
│       └── watches/
├── templates/                     # Jinja2 HTML templates
│   ├── catalogue.html
│   └── login.html
├── .gitignore                     # Git ignore file
├── LICENSE                        # Project license
├── Procfile                       # Deployment file
├── README.md                      # Project documentation
├── app.py                         # Main Flask application
├── backend.py                     # Backend logic and utilities
└── requirements.txt               # Python dependencies
```

## My Contributions

As part of a 5-person university development team, my personal contributions included:

### Full-Stack Development
- Built backend Flask logic and integrated frontend templates
- Connected dynamic catalogue data to rendered pages
- Integrated backend and frontend modules and contributed to system-wide debugging and feature coordination

### Core Features Implemented
- Developed advanced sorting functionality for catalogue browsing
- Built wishlist system with add/remove/update behavior
- Created recommendation system for similar watches

### Software Design & Collaboration
- Designed UML diagrams including class and sequence diagrams
- Worked in a collaborative Agile-style team environment
- Participated in debugging, feature refinement, and system integration. 

---

## What I Learned

- Building and deploying full-stack Flask applications
- Designing maintainable backend systems
- Working in a multi-person collaborative codebase
- Debugging and integrating shared components
- Translating software designs into working features

---

## Screenshots

### Login Page
![Login](static/images/login.png)

### Watch Catalogue
![Catalogue](static/images/catalogue.png)

### Admin Panel (Edit Watch)
![Admin](static/images/adminEdit.png)


## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/ShaikhFawzan/Luxury-Watch-Catalogue-Web-App.git
   cd Luxury-Watch-Catalogue-Web-App
   ```

2. **Create Virtual Environment** (Recommended)
   ```bash
   python -m venv venv

   # On Linux/macOS
   source venv/bin/activate
   
   # On Windows (Command Prompt):
    venv\Scripts\activate

   # On Windows (PowerShell)
   venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies** 
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   # On Windows
   .\scripts\build.bat
   
   # On Linux/Mac
   ./scripts/build.sh

   # Run directly:
   python app.py
   ```

5. **Access the Application**
   Open your browser and navigate to `http://localhost:5000`

 ## Image Notice
Watch images were AI-generated placeholder assets created for this project. 

These images are not official manufacturer photos and are not intended to represent exact real-world models. Brand names and product data in the catalogue are used as sample inventory metadata.

## Data Persistence Notice
Since this was originally a project done for university, User-generated data such as wishlists and reviews is currently stored in CSV files to satisfy the assignment requirements. Updates are not guaranteed to persist after server restarts, redeployments, or environment resets. As a result, some changes made in the live version may not be retained permanently. 

A database-backed storage system (using Supabase) is planned as the next major improvement to provide reliable long-term persistence, better scalability, and more consistent data handling across sessions


## Future Improvements  - currently working on migrating to a Database 

- **Database Migration**: Transition from CSV to a database system (PostgreSQL/MySQL)
- **Enhanced Security**: Implement JWT-based authentication and improved password hashing
- **API Development**: Create RESTful APIs for mobile app integration
- **Advanced Analytics**: Add user behavior tracking and recommendation algorithm refinements
- **UI/UX Enhancements**: Implement modern frontend framework (React/Vue.js) for improved interactivity

---
