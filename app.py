import sqlite3
from flask import Flask, render_template, request, redirect
from pathlib import Path
from datetime import date
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

app = Flask(__name__)

# path within mounted folder
DB_FOLDER = Path("app/data")
DB_FOLDER.mkdir(parents=True, exist_ok=True)
DB = DB_FOLDER / "fahrten.db"



# initialize db if there isn't any
def init_db():
    con = sqlite3.connect(str(DB))
    con.execute("""
    CREATE TABLE IF NOT EXISTS tankvorgaenge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datum DATE NOT NULL,
        kilometer INTEGER NOT NULL,
        liter REAL NOT NULL,
        preis_pro_liter REAL NOT NULL,
        kommentar TEXT
    )
    """)
    con.commit()
    con.close()


def get_db():
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    return con


@app.route("/")
def index():
    con = get_db()
    rows = con.execute("SELECT * FROM tankvorgaenge ORDER BY datum DESC").fetchall()

    # read last km value as preset if there is any
    last_km_row = con.execute("SELECT kilometer FROM tankvorgaenge ORDER BY datum DESC LIMIT 1").fetchone()

    # load data to plot and generate plot
    rows_plot = con.execute("SELECT datum, liter, preis_pro_liter, kommentar FROM tankvorgaenge ORDER BY datum").fetchall()
    plot_html = grafik(rows_plot)

    con.close()

    return render_template(
        "index.html",
        today=date.today().isoformat(),
        tankvorgaenge=rows,
        last_km=last_km_row["kilometer"] if last_km_row else "",
        plot_html=plot_html
    )


def grafik(rows_plot):
    if rows_plot:
        df = pd.DataFrame([dict(r) for r in rows_plot])

        # convert date to datetime object
        df["datum"] = pd.to_datetime(df["datum"])
        df["kosten"] = df["liter"] * df["preis_pro_liter"]
        df["kumuliert"] = df["kosten"].cumsum()

        df["kommentar"] = df.get("kommentar", pd.Series(["–"] * len(df)))
        df["kommentar"] = df["kommentar"].fillna("–")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # plot cost per tank
        fig.add_trace(
            go.Scatter(
                x=df["datum"],
                y=df["kosten"],
                name="Kosten pro Tank",
                mode="lines+markers",
                line=dict(shape="linear", color="#1f77b4", width=3),
                marker=dict(size=6, opacity=0.8),
                hovertemplate="%{y}€"
            ),
            secondary_y=False
        )

        fig.add_trace(
            go.Scatter(
                x=df["datum"],
                y=df["kumuliert"],
                name="Kumuliert",
                mode="lines+markers",
                line=dict(shape="linear", color="#ff7f0e", width=3),
                marker=dict(size=6, opacity=0.8),
                text=df["kommentar"],  # falls du Hover hier auch willst
                hovertemplate="%{y}€<br>Kommentar: %{text}"
            ),
            secondary_y=True
        )

        fig.update_yaxes(title_text="Kosten pro Tank (€)", secondary_y=False)
        fig.update_yaxes(title_text="Kumulative Kosten (€)", secondary_y=True)
        fig.update_xaxes(title_text="Datum")
        fig.update_layout(title="Tankkosten Übersicht", template="plotly_dark", hovermode="x unified")
        plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})

    else:
        plot_html = "<p>Keine Daten vorhanden.</p>"

    return plot_html


@app.route("/neu", methods=["POST"])
def neu():
    data = (
        request.form["datum"],
        request.form["kilometer"],
        request.form["liter"],
        request.form["preis_pro_liter"],
        request.form["kommentar"]
    )
    con = get_db()
    con.execute(
        "INSERT INTO tankvorgaenge (datum, kilometer, liter, preis_pro_liter, kommentar) VALUES (?, ?, ?, ?, ?)",
        data
    )
    con.commit()
    con.close()
    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    con = get_db()
    con.execute("DELETE FROM tankvorgaenge WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect("/")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

