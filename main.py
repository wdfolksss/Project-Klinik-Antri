from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)
def get_db():
    conn = sqlite3.connect("klinik_antri.db")
    conn.row_factory = sqlite3.Row
    return conn

#database nya
def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pasien (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nik TEXT NOT NULL,nama TEXT NOT NULL,
            umur INTEGER NOT NULL, jenis_kelamin TEXT NOT NULL, no_hp TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS antrean (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_pasien INTEGER NOT NULL, no_antrean TEXT NOT NULL,
            poli TEXT NOT NULL, status TEXT NOT NULL, waktu_daftar TEXT NOT NULL,
            FOREIGN KEY (id_pasien) REFERENCES pasien(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS rekam_medis (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_pasien INTEGER NOT NULL, keluhan TEXT NOT NULL,
            diagnosa TEXT NOT NULL, resep TEXT NOT NULL, tanggal_periksa TEXT NOT NULL,
            FOREIGN KEY (id_pasien) REFERENCES pasien(id)
        )
    """)

    conn.commit()
    conn.close()

#estimasi waktu
def hitung_estimasi(conn, poli, id_antrean, status):
    if status == "MENUNGGU":
        posisi = conn.execute("""
            SELECT COUNT(*)
            FROM antrean
            WHERE poli = ?
            AND status = 'MENUNGGU'
            AND id <= ?
        """, (poli, id_antrean)).fetchone()[0]

        return posisi * 15
    
    return 0

#pasien
@app.route("/")
def home():
    return render_template("pasien/registrasi.html")

#registrasi
@app.route("/registrasi", methods=["GET", "POST"])
def registrasi():
    if request.method == "POST":
        nik = request.form["nik"]
        nama = request.form["nama"]

        try:
            umur = int(request.form["umur"])
        except:
            return "ERROR: Data tidak valid"

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

        return redirect("/ambil-antrean")
    
    return render_template("pasien/registrasi.html")

#ambil antrean
@app.route("/ambil-antrean", methods=["GET", "POST"])
def ambil_antrean():
    if request.method == "POST":
        poli = request.form["poli"]

        kode_poli = {
            "Poli Umum": "PU",
            "Poli Gigi": "PG",
            "Poli Anak": "PA"
        }

        kode = kode_poli[poli]
        conn = get_db()

        terakhir = conn.execute("""
            SELECT no_antrean
            FROM antrean
            WHERE poli = ?
            ORDER BY id DESC
            LIMIT 1
        """, (poli,)).fetchone()

        if terakhir:
            nomor = int(terakhir["no_antrean"][2:]) + 1
        else:
            nomor = 1

        no_antrean = f"{kode}{nomor:03d}"

        pasien = conn.execute("""
            SELECT id
            FROM pasien
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        cursor = conn.execute("""
            INSERT INTO antrean
            (id_pasien, no_antrean, poli, status, waktu_daftar)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (
            pasien["id"],
            no_antrean,
            poli,
            "MENUNGGU"
        ))

        id_antrean = cursor.lastrowid
        conn.commit()
        conn.close()

        return redirect(f"/status-antrean/{id_antrean}")
    
    return render_template("pasien/ambil_antrean.html")

#status antrean
@app.route("/status-antrean/<int:id_antrean>")
def status_antrean(id_antrean):
    conn = get_db()

    antrean = conn.execute("""
        SELECT antrean.*, pasien.nama
        FROM antrean
        JOIN pasien ON antrean.id_pasien = pasien.id
        WHERE antrean.id = ?
    """, (id_antrean,)).fetchone()

    if antrean:
        estimasi = hitung_estimasi(
            conn,
            antrean["poli"],
            antrean["id"],
            antrean["status"]
        )
    else:
        estimasi = 0

    conn.close()

    return render_template(
        "pasien/status_antrean.html",
        antrean=antrean,
        estimasi=estimasi
    )

#lihat antrean
@app.route("/lihat-antrean")
def lihat_antrean_saya():
    conn = get_db()

    antrean = conn.execute("""
        SELECT antrean.*, pasien.nama
        FROM antrean
        JOIN pasien ON antrean.id_pasien = pasien.id
        ORDER BY antrean.id DESC
        LIMIT 1
    """).fetchone()

    if antrean:
        estimasi = hitung_estimasi(
            conn,
            antrean["poli"],
            antrean["id"],
            antrean["status"]
        )
        id_antrean = antrean["id"]
    else:
        estimasi = 0
        id_antrean = 0

    conn.close()

    if id_antrean == 0:
        return render_template(
            "pasien/status_antrean.html",
            antrean=None,
            estimasi=estimasi
        )

    return redirect(f"/status-antrean/{id_antrean}")

#dokter
@app.route("/dokter")
def dashboard_dokter():
    return render_template("dokter/dashboard.html")

#antrean (dokter)
@app.route("/dokter/antrean")
def lihat_antrean_dokter():
    conn = get_db()

    antrean = conn.execute("""
        SELECT antrean.*, pasien.nama
        FROM antrean
        JOIN pasien ON antrean.id_pasien = pasien.id
        ORDER BY antrean.id ASC
    """).fetchall()

    conn.close()

    return render_template("dokter/panggil.html", antrean=antrean)

#sistem panggilan (dokter)
@app.route("/dokter/panggil")
def panggil_antrean():
    conn = get_db()

    pasien = conn.execute("""
        SELECT *
        FROM antrean
        WHERE status = 'MENUNGGU'
        ORDER BY id ASC
        LIMIT 1
    """).fetchone()

    if pasien:
        conn.execute("""
            UPDATE antrean
            SET status = 'DIPERIKSA'
            WHERE id = ?
        """, (pasien["id"],))

    conn.commit()
    conn.close()

    return redirect("/dokter/antrean")

#rekam medis (dokter)
@app.route("/dokter/rekam-medis/<int:id_pasien>", methods=["GET", "POST"])
def input_rekam_medis(id_pasien):
    if request.method == "POST":
        keluhan = request.form["keluhan"]
        diagnosa = request.form["diagnosa"]
        resep = request.form["resep"]

        conn = get_db()

        conn.execute("""
            INSERT INTO rekam_medis
            (id_pasien, keluhan, diagnosa, resep, tanggal_periksa)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (id_pasien, keluhan, diagnosa, resep))

        conn.execute("""
            UPDATE antrean
            SET status = 'SELESAI'
            WHERE id_pasien = ?
            AND status = 'DIPERIKSA'
        """, (id_pasien,))

        conn.commit()
        conn.close()

        return redirect("/dokter/antrean")
    
    return render_template("dokter/rekam_medis.html", id_pasien=id_pasien)

#menyelesaikan pemeriksaan 
@app.route("/dokter/selesai/<int:id>")
def selesai_pemeriksaan(id):
    conn = get_db()

    conn.execute("""
        UPDATE antrean
        SET status = 'SELESAI'
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/dokter/antrean")

#riwayat medis (dokter)
@app.route("/dokter/riwayat_medis")
def riwayat_rekam_medis():

    conn = get_db()

    riwayat = conn.execute("""
        SELECT rekam_medis.*, pasien.nama
        FROM rekam_medis
        JOIN pasien
        ON rekam_medis.id_pasien = pasien.id
        ORDER BY rekam_medis.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "dokter/riwayat_medis.html",
        riwayat=riwayat
    )

#laporan admin
@app.route("/laporan")
def laporan_klinik():
    keyword = request.args.get("keyword", "")

    conn = get_db()

    total_pasien = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE date(waktu_daftar) = date('now')
    """).fetchone()[0]

    poli_umum = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE poli = 'Poli Umum'
    """).fetchone()[0]

    poli_gigi = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE poli = 'Poli Gigi'
    """).fetchone()[0]

    poli_anak = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE poli = 'Poli Anak'
    """).fetchone()[0]

    menunggu = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE status = 'MENUNGGU'
    """).fetchone()[0]

    diperiksa = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE status = 'DIPERIKSA'
    """).fetchone()[0]

    selesai = conn.execute("""
        SELECT COUNT(*) FROM antrean
        WHERE status = 'SELESAI'
    """).fetchone()[0]

    riwayat = conn.execute("""
        SELECT rekam_medis.*, pasien.nama
        FROM rekam_medis
        JOIN pasien
        ON rekam_medis.id_pasien = pasien.id
        WHERE pasien.nama LIKE ?
        ORDER BY rekam_medis.id DESC
    """, (f"%{keyword}%",)).fetchall()

    pasien = conn.execute("""
        SELECT *
        FROM pasien
        ORDER BY id DESC
    """).fetchall()

    antrean = conn.execute("""
        SELECT antrean.*, pasien.nama
        FROM antrean
        JOIN pasien ON antrean.id_pasien = pasien.id
        ORDER BY antrean.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin/laporan.html",
        total_pasien=total_pasien,
        pasien=pasien,
        antrean=antrean,
        poli_umum=poli_umum,
        poli_gigi=poli_gigi,
        poli_anak=poli_anak,
        menunggu=menunggu,
        diperiksa=diperiksa,
        selesai=selesai,
        riwayat=riwayat,
        keyword =keyword
    )
    
if __name__ == "__main__":
    init_db()
    app.run(debug=True)