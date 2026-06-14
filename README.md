# 🍰 Digital Recipe Sharing System

**DBMS Lab Project** — A web-based recipe sharing platform built with Flask and MySQL.

## 🚀 Features
- User registration & login with role-based access (User/Admin)
- Upload recipes with images, categories, and ingredients
- Ingredient calculator (auto-scales based on servings)
- Star ratings & written reviews
- Category-based browsing (10 categories)
- YouTube video embedding
- Admin panel with full management
- Database triggers for automatic activity logging
- SQL Views for average ratings

## 🛠️ Tech Stack
- **Backend:** Python Flask
- **Database:** MySQL (XAMPP)
- **Frontend:** HTML5, CSS3
- **Server:** XAMPP Apache

## 📂 Database Concepts Used
- **Joins** — Multi-table data retrieval
- **Views** — Pre-computed recipe ratings
- **Triggers** — Auto activity logging on INSERT/DELETE
- **Foreign Keys** — Referential integrity
- **Normalization** — 3NF applied

## ⚙️ Setup Instructions
1. Install XAMPP and start Apache + MySQL
2. Import `database/schema.sql` in phpMyAdmin
3. Install dependencies: `pip install flask mysql-connector-python`
4. Run: `python app.py`
5. Open: `http://127.0.0.1:5000`

## 🔑 Default Admin Login
- Username: `admin`
- Password: `admin123`

## 📄 License
This project is for educational purposes.
