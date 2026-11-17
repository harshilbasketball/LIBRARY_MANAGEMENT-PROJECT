# Library Management System — Tkinter Edition

A Python desktop conversion of the supplied Java Swing student library portal. The interface uses Tkinter/ttk and MySQL remains the database.

## Features
- Student login using Student ID
- Browse all books and search by title, author, or ISBN
- Borrow available books
- Limit of 3 active borrowed books per student
- View personal borrowing history
- Return currently borrowed books
- Refresh borrowing history and logout

## Requirements
- Python 3.10+
- MySQL Server 8.x
- Existing `library_system` database created from `database/schema.sql`

## Setup
1. Keep MySQL Server running.
2. Open the project folder in VS Code.
3. Install the Python dependency:
   ```bash
   py -m pip install -r requirements.txt
   ```
4. Copy `config.example.ini` to `config.ini`.
5. Edit `config.ini` and enter your MySQL root password.
6. If you have not created the database yet, execute `database/schema.sql` in MySQL Workbench. **Warning:** the supplied SQL script drops and recreates the three tables, so do not rerun it if you need to preserve existing records.
7. Run:
   ```bash
   py app.py
   ```
   Or double-click `run.bat`.

## Sample student IDs
- `S101` — Arun
- `S102` — Priya
- `S103` — Ravi

## Database
The app uses the same tables and columns as the supplied Java project: `students`, `books`, and `borrow_records`.
