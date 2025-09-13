import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from pathlib import Path
from datetime import date
import plots

app = Flask(__name__)

DATA_DIR = Path("vehicles")
DATA_DIR.mkdir(exist_ok=True)


# Hilfsfunktionen
def get_db_path(fahrzeug):
    db_file = DATA_DIR / f"{fahrzeug}.db"
  
    return db_file

def init_db(fahrzeug):
    db_file = get_db_path(fahrzeug)
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eintraege (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum DATE NOT NULL,
            kilometer INTEGER,
            liter REAL,
            preis_pro_liter REAL,
            kosten REAL,
            kommentar TEXT,
            event TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_db(fahrzeug):
    db_file = get_db_path(fahrzeug)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def list_vehicles():
    return [f.stem for f in DATA_DIR.glob("*.db")]


@app.route("/", methods=["GET"])
def index():
    fahrzeuge = list_vehicles()
    if not fahrzeuge:
        # if there is no DB available, create one on this landing page
        return render_template("no_vehicle.html")
    
    selected_fahrzeug = request.args.get("fahrzeug") or (fahrzeuge[0] if fahrzeuge else None)
    rows = []
    last_km = ""

    if selected_fahrzeug:
        init_db(selected_fahrzeug)  # Tabelle ggf. anlegen
        con = get_db(selected_fahrzeug)  # SQLite Verbindung
        rows = con.execute("SELECT * FROM eintraege ORDER BY datum DESC").fetchall()

        # Letzter KM Stand
        last_km_row = con.execute("SELECT kilometer FROM eintraege ORDER BY datum DESC LIMIT 1").fetchone()
        last_km = last_km_row["kilometer"] if last_km_row else ""

        con.close()

    return render_template(
        "index.html",
        fahrzeuge=fahrzeuge,
        selected_fahrzeug=selected_fahrzeug,
        rows=rows,
        last_km=last_km,
        today=date.today().isoformat()
    )


def get_last_km(fahrzeug):
    con = get_db(fahrzeug)
    row = con.execute("SELECT kilometer FROM eintraege ORDER BY datum DESC LIMIT 1").fetchone()
    con.close()
    return row["kilometer"] if row else 0


def get_all_entries(fahrzeug):
    con = get_db(fahrzeug)
    rows = con.execute("SELECT * FROM eintraege ORDER BY datum DESC").fetchall()
    con.close()
    return rows


@app.route("/edit/<fahrzeug>/<int:id>", methods=["GET", "POST"])
def edit(fahrzeug, id):
    con = get_db(fahrzeug)

    if request.method == "POST":
        event = request.form["event"]
        datum = request.form["datum"]
        kommentar = request.form.get("kommentar", "")

        if event == "Tanken":
            kilometer = request.form.get("kilometer")
            liter = request.form.get("liter")
            preis_pro_liter = request.form.get("preis_pro_liter")

            kilometer = int(kilometer) if kilometer else None
            liter = float(liter) if liter else None
            preis_pro_liter = float(preis_pro_liter) if preis_pro_liter else None
            kosten = liter * preis_pro_liter if (liter and preis_pro_liter) else None

            con.execute(
                """UPDATE eintraege
                   SET event=?, datum=?, kilometer=?, liter=?, preis_pro_liter=?, kosten=?, kommentar=?
                   WHERE id=?""",
                (event, datum, kilometer, liter, preis_pro_liter, kosten, kommentar, id),
            )

        elif event == "Wartung":
            kilometer = request.form.get("kilometer")
            kosten = request.form.get("kosten")

            kilometer = int(kilometer) if kilometer else None
            kosten = float(kosten) if kosten else None

            con.execute(
                """UPDATE eintraege
                   SET event=?, datum=?, kilometer=?, kosten=?, kommentar=?
                   WHERE id=?""",
                (event, datum, kilometer, kosten, kommentar, id),
            )

        else:  # Anderes
            kosten = request.form.get("kosten")
            kosten = float(kosten) if kosten else None

            con.execute(
                """UPDATE eintraege
                   SET event=?, datum=?, kosten=?, kommentar=?
                   WHERE id=?""",
                (event, datum, kosten, kommentar, id),
            )

        con.commit()
        con.close()
        return redirect(url_for("index", fahrzeug=fahrzeug))

    else:  # GET → bestehenden Eintrag abrufen und index.html erneut rendern
        row = con.execute("SELECT * FROM eintraege WHERE id=?", (id,)).fetchone()
        rows = con.execute("SELECT * FROM eintraege ORDER BY datum DESC").fetchall()
        con.close()

        return render_template(
            "index.html",
            fahrzeuge=list_vehicles(),
            selected_fahrzeug=fahrzeug,
            rows=rows,
            today=date.today().isoformat(),
            last_km=row["kilometer"] if row and row["kilometer"] else None,
            edit_row=row,  # wichtig: für das Befüllen des Formulars
        )


@app.route("/update/<fahrzeug>/<int:id>", methods=["POST"])
def update(fahrzeug, id):
    event = request.form["event"]
    datum = request.form["datum"]
    kilometer = int(request.form["kilometer"])
    kommentar = request.form.get("kommentar", "")

    con = get_db(fahrzeug)
    
    if event == "Tanken":
        liter = float(request.form["liter"])
        preis_pro_liter = float(request.form["preis_pro_liter"])
        kosten = liter * preis_pro_liter
        con.execute("""
            UPDATE eintraege 
            SET event=?, datum=?, kilometer=?, liter=?, preis_pro_liter=?, kosten=?, kommentar=?
            WHERE id=?
        """, (event, datum, kilometer, liter, preis_pro_liter, kosten, kommentar, id))
    else:
        kosten = float(request.form["kosten"])
        con.execute("""
            UPDATE eintraege 
            SET event=?, datum=?, kilometer=?, liter=NULL, preis_pro_liter=NULL, kosten=?, kommentar=?
            WHERE id=?
        """, (event, datum, kilometer, kosten, kommentar, id))

    con.commit()
    con.close()
    return redirect(f"/?fahrzeug={fahrzeug}")


@app.route("/delete/<fahrzeug>/<int:id>", methods=["POST"])
def delete(fahrzeug, id):
    con = get_db(fahrzeug)
    con.execute("DELETE FROM eintraege WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect(f"/?fahrzeug={fahrzeug}")


@app.route("/neu/<fahrzeug>", methods=["POST"])
def neu(fahrzeug):
    con = get_db(fahrzeug)
    event = request.form["event"]
    datum = request.form["datum"]
    kommentar = request.form.get("kommentar", "")

    if event == "Tanken":
        kilometer = request.form.get("kilometer", None)
        liter = request.form.get("liter", None)
        preis_pro_liter = request.form.get("preis_pro_liter", None)

        kilometer = int(kilometer) if kilometer else None
        liter = float(liter) if liter else None
        preis_pro_liter = float(preis_pro_liter) if preis_pro_liter else None

        kosten = (liter * preis_pro_liter) if liter and preis_pro_liter else None

        con.execute(
            """
            INSERT INTO eintraege (event, datum, kilometer, liter, preis_pro_liter, kosten, kommentar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event, datum, kilometer, liter, preis_pro_liter, kosten, kommentar),
        )

    elif event == "Wartung":
        kilometer = request.form.get("kilometer", None)
        kosten = request.form.get("kosten", None)

        kilometer = int(kilometer) if kilometer else None
        kosten = float(kosten) if kosten else None

        con.execute(
            """
            INSERT INTO eintraege (event, datum, kilometer, kosten, kommentar)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event, datum, kilometer, kosten, kommentar),
        )

    elif event == "Anderes":
        kilometer = request.form.get("kilometer", None)
        kosten = request.form.get("kosten", None)

        kilometer = int(kilometer) if kilometer else None
        kosten = float(kosten) if kosten else None

        con.execute(
            """
            INSERT INTO eintraege (event, datum, kilometer, kosten, kommentar)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event, datum, kilometer, kosten, kommentar),
        )

    con.commit()
    con.close()
    return redirect(url_for("index", fahrzeug=fahrzeug))


@app.route("/fahrzeug_neu", methods=["POST"])
def fahrzeug_neu():
    name = request.form["fahrzeug_name"]
    db_file = get_db_path(name)
    if not db_file.exists():
        init_db(name)
    return redirect(url_for("index", fahrzeug=name))


@app.route("/plot_fuelcost/<fahrzeug>")
def plot_fuelcost(fahrzeug):
    con = get_db(fahrzeug)
    data = con.execute("SELECT datum, liter, preis_pro_liter, kommentar FROM eintraege ORDER BY datum").fetchall()
    
    return render_template(
        "plot_fuelcost.html",
        plot_html=plots.fuel_price(data),
        fahrzeuge=list_vehicles(),
        selected_fahrzeug=fahrzeug
    )


@app.route("/plot_uebersicht/<fahrzeug>")
def plot_overview(fahrzeug):
    con = get_db(fahrzeug)
    data = con.execute("SELECT event, kosten FROM eintraege").fetchall()
    
    return render_template(
        "plot_overview.html",
        plot_html=plots.cost_overview(data),
        fahrzeuge=list_vehicles(),
        selected_fahrzeug=fahrzeug
    )


@app.route("/plot_efficiency/<fahrzeug>")
def plot_efficiency(fahrzeug):
    con = get_db(fahrzeug)
    data = con.execute("SELECT event, datum, kilometer, liter FROM eintraege ORDER BY datum").fetchall()

    return render_template(
        "plot_overview.html",
        plot_html=plots.efficiency(data),
        fahrzeuge=list_vehicles(),
        selected_fahrzeug=fahrzeug
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
