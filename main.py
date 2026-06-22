from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect("klinik_antri.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pasien (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nik TEXT NOT NULL,
            nama TEXT NOT NULL,
            umur INTEGER NOT NULL,
            jenis_kelamin TEXT NOT NULL,
            no_hp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()    

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/registrasi", methods=["GET", "POST"])
def registrasi():
    if request.method == "POST":
        nik = request.form["nik"]
        nama = request.form["nama"]
        umur = int(request.form["umur"])
        jenis_kelamin = request.form["jenis_kelamin"]
        no_hp = request.form["no_hp"]

        if umur <= 0 or len(no_hp) < 10:
            return "ERROR: Data tidak valid"

        conn = get_db()
        conn.execute("""
            INSERT INTO pasien (nik, nama, umur, jenis_kelamin, no_hp)
            VALUES (?, ?, ?, ?, ?)
        """, (nik, nama, umur, jenis_kelamin, no_hp))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("registrasi.html")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)