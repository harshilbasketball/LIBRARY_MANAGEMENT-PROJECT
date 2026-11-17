import configparser
import tkinter as tk
from tkinter import ttk, messagebox
import os
from datetime import date
import mysql.connector
from mysql.connector import Error

CONFIG_FILE = "config.ini"
MAX_BORROW = 3

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        messagebox.showerror(
            "Configuration missing",
            "config.ini was not found. Copy config.example.ini to config.ini "
            "and enter your MySQL password."
        )
        raise SystemExit(1)
    config.read(CONFIG_FILE)
    return {
        "host": config.get("mysql", "host", fallback="localhost"),
        "port": config.getint("mysql", "port", fallback=3306),
        "database": config.get("mysql", "database", fallback="library_system"),
        "user": config.get("mysql", "user", fallback="root"),
        "password": config.get("mysql", "password", fallback="")
    }

class LibraryDB:
    def __init__(self):
        self.settings = load_config()

    def connect(self):
        return mysql.connector.connect(**self.settings)

    def find_student(self, student_id):
        with self.connect() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT student_id, name, department FROM students WHERE student_id=%s",
                (student_id,)
            )
            row = cur.fetchone()
            cur.close()
            return row

    def get_books(self, keyword=""):
        with self.connect() as conn:
            cur = conn.cursor(dictionary=True)
            if keyword:
                pattern = f"%{keyword}%"
                cur.execute(
                    """SELECT isbn, title, author, available FROM books
                       WHERE title LIKE %s OR author LIKE %s OR isbn LIKE %s
                       ORDER BY title""",
                    (pattern, pattern, pattern)
                )
            else:
                cur.execute("SELECT isbn, title, author, available FROM books ORDER BY title")
            rows = cur.fetchall()
            cur.close()
            return rows

    def get_records(self, student_id):
        with self.connect() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT r.isbn, b.title, r.borrow_date, r.return_date
                   FROM borrow_records r
                   JOIN books b ON r.isbn=b.isbn
                   WHERE r.student_id=%s ORDER BY r.record_id DESC""",
                (student_id,)
            )
            rows = cur.fetchall()
            cur.close()
            return rows

    def borrow_book(self, student_id, isbn):
        conn = self.connect()
        try:
            conn.start_transaction()
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM borrow_records WHERE student_id=%s AND return_date IS NULL",
                (student_id,)
            )
            active_count = cur.fetchone()[0]
            if active_count >= MAX_BORROW:
                conn.rollback()
                return f"You can borrow at most {MAX_BORROW} books at a time."
            cur.execute(
                "UPDATE books SET available=FALSE WHERE isbn=%s AND available=TRUE",
                (isbn,)
            )
            if cur.rowcount == 0:
                conn.rollback()
                return "This book is not available right now."
            cur.execute(
                """INSERT INTO borrow_records (student_id, isbn, borrow_date)
                   VALUES (%s, %s, %s)""",
                (student_id, isbn, date.today())
            )
            conn.commit()
            return None
        except Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def return_book(self, student_id, isbn):
        conn = self.connect()
        try:
            conn.start_transaction()
            cur = conn.cursor()
            cur.execute(
                """UPDATE borrow_records SET return_date=%s
                   WHERE student_id=%s AND isbn=%s AND return_date IS NULL""",
                (date.today(), student_id, isbn)
            )
            if cur.rowcount == 0:
                conn.rollback()
                return "No active borrow found for this book."
            cur.execute("UPDATE books SET available=TRUE WHERE isbn=%s", (isbn,))
            conn.commit()
            return None
        except Error:
            conn.rollback()
            raise
        finally:
            conn.close()

class LibraryApp:
    BG = "#f3f6fb"
    NAVY = "#214378"
    def __init__(self, root):
        self.root = root
        self.root.title("Library Management System")
        self.root.geometry("980x650")
        self.root.minsize(820, 540)
        self.root.configure(bg=self.BG)
        self.db = LibraryDB()
        self.student = None
        self.setup_style()
        self.show_login()

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=self.BG)
        style.configure("TLabel", background=self.BG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.NAVY, foreground="white",
                        font=("Segoe UI", 19, "bold"))
        style.configure("Sub.TLabel", background=self.NAVY, foreground="#c8d7f0",
                        font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"),
                        padding=(12, 7))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def header(self, title, subtitle):
        head = tk.Frame(self.root, bg=self.NAVY, padx=22, pady=18)
        head.pack(fill="x")
        tk.Label(head, text=title, bg=self.NAVY, fg="white",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(head, text=subtitle, bg=self.NAVY, fg="#c8d7f0",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))

    def show_login(self):
        self.clear()
        self.root.geometry("560x330")
        self.header("Library Management System", "Student Portal")
        card = tk.Frame(self.root, bg="white", padx=35, pady=28,
                        highlightthickness=1, highlightbackground="#dce3ed")
        card.pack(padx=45, pady=30, fill="x")
        tk.Label(card, text="Sign in with your Student ID", bg="white",
                 fg="#26364d", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.student_id_entry = ttk.Entry(card, font=("Segoe UI", 11))
        self.student_id_entry.pack(fill="x", pady=(15, 12), ipady=5)
        self.student_id_entry.bind("<Return>", lambda _e: self.login())
        ttk.Button(card, text="Login", style="Primary.TButton",
                   command=self.login).pack(fill="x")
        tk.Label(self.root, text="Sample IDs: S101, S102, S103",
                 bg=self.BG, fg="#68778c", font=("Segoe UI", 9)).pack()
        self.student_id_entry.focus_set()

    def login(self):
        student_id = self.student_id_entry.get().strip()
        if not student_id:
            messagebox.showwarning("Login", "Enter your Student ID.")
            return
        try:
            student = self.db.find_student(student_id)
            if not student:
                messagebox.showerror("Login Failed", f"No student found with ID {student_id}.")
                return
            self.student = student
            self.show_dashboard()
        except Error as exc:
            messagebox.showerror("Database Error", f"Could not connect to MySQL:\n{exc}")

    def show_dashboard(self):
        self.clear()
        self.root.geometry("1050x700")
        top = tk.Frame(self.root, bg=self.NAVY, padx=20, pady=14)
        top.pack(fill="x")
        left = tk.Frame(top, bg=self.NAVY)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=f"Welcome, {self.student['name']}", bg=self.NAVY,
                 fg="white", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(left, text=f"Student ID: {self.student['student_id']}   |   "
                 f"Department: {self.student['department']}", bg=self.NAVY,
                 fg="#c8d7f0", font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 0))
        ttk.Button(top, text="Logout", command=self.logout).pack(side="right", padx=4)

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=14)
        browse = ttk.Frame(self.tabs, padding=12)
        mine = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(browse, text="Browse Books")
        self.tabs.add(mine, text="My Borrowed Books")

        searchbar = ttk.Frame(browse)
        searchbar.pack(fill="x", pady=(0, 10))
        ttk.Label(searchbar, text="Search by title, author or ISBN:").pack(side="left")
        self.search_entry = ttk.Entry(searchbar, width=30)
        self.search_entry.pack(side="left", padx=8)
        self.search_entry.bind("<Return>", lambda _e: self.search_books())
        ttk.Button(searchbar, text="Search", command=self.search_books).pack(side="left", padx=3)
        ttk.Button(searchbar, text="Show All", command=lambda: self.load_books()).pack(side="left", padx=3)

        self.books_tree = self.make_tree(
            browse, ("isbn", "title", "author", "status"),
            ("ISBN", "Title", "Author", "Status"),
            (150, 300, 230, 110)
        )
        actions = ttk.Frame(browse)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Borrow Selected Book", style="Primary.TButton",
                   command=self.borrow_selected).pack(side="right")

        self.records_tree = self.make_tree(
            mine, ("isbn", "title", "borrowed", "returned", "status"),
            ("ISBN", "Title", "Borrowed On", "Returned On", "Status"),
            (140, 270, 150, 150, 110)
        )
        record_actions = ttk.Frame(mine)
        record_actions.pack(fill="x", pady=10)
        ttk.Button(record_actions, text="Refresh", command=self.load_records).pack(side="right", padx=4)
        ttk.Button(record_actions, text="Return Selected Book", style="Primary.TButton",
                   command=self.return_selected).pack(side="right", padx=4)
        self.load_books()
        self.load_records()

    def make_tree(self, parent, keys, headings, widths):
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrapper, columns=keys, show="headings", selectmode="browse")
        for key, heading, width in zip(keys, headings, widths):
            tree.heading(key, text=heading)
            tree.column(key, width=width, minwidth=70, anchor="w")
        yscroll = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(wrapper, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)
        return tree

    def load_books(self, keyword=""):
        try:
            for item in self.books_tree.get_children():
                self.books_tree.delete(item)
            for book in self.db.get_books(keyword):
                status = "Available" if book["available"] else "Issued"
                self.books_tree.insert("", "end", values=(
                    book["isbn"], book["title"], book["author"], status
                ))
        except Error as exc:
            messagebox.showerror("Database Error", str(exc))

    def search_books(self):
        self.load_books(self.search_entry.get().strip())

    def load_records(self):
        try:
            for item in self.records_tree.get_children():
                self.records_tree.delete(item)
            for record in self.db.get_records(self.student["student_id"]):
                active = record["return_date"] is None
                self.records_tree.insert("", "end", values=(
                    record["isbn"], record["title"], str(record["borrow_date"]),
                    "-" if active else str(record["return_date"]),
                    "Borrowed" if active else "Returned"
                ))
        except Error as exc:
            messagebox.showerror("Database Error", str(exc))

    def selected_values(self, tree):
        selected = tree.selection()
        if not selected:
            return None
        return tree.item(selected[0], "values")

    def borrow_selected(self):
        values = self.selected_values(self.books_tree)
        if not values:
            messagebox.showwarning("Borrow", "Select a book first.")
            return
        try:
            error = self.db.borrow_book(self.student["student_id"], values[0])
            if error:
                messagebox.showwarning("Borrow", error)
            else:
                messagebox.showinfo("Borrow", "Book borrowed successfully.")
                self.load_books(self.search_entry.get().strip())
                self.load_records()
        except Error as exc:
            messagebox.showerror("Database Error", str(exc))

    def return_selected(self):
        values = self.selected_values(self.records_tree)
        if not values:
            messagebox.showwarning("Return", "Select a borrowed book first.")
            return
        if values[4] != "Borrowed":
            messagebox.showinfo("Return", "This book has already been returned.")
            return
        try:
            error = self.db.return_book(self.student["student_id"], values[0])
            if error:
                messagebox.showwarning("Return", error)
            else:
                messagebox.showinfo("Return", "Book returned successfully.")
                self.load_books(self.search_entry.get().strip())
                self.load_records()
        except Error as exc:
            messagebox.showerror("Database Error", str(exc))

    def logout(self):
        self.student = None
        self.show_login()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = LibraryApp(root)
    except SystemExit:
        root.destroy()
        raise
    root.mainloop()
