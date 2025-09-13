from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd


def fuel_price(data):
    """
    Plot price for fuel

    First y-axis is cost per tank
    Second y-axis is cumulative fuel cost
    """


    if not data:
        return "<p>Keine Daten vorhanden.</p>"

    df = pd.DataFrame([dict(r) for r in data])

    # convert date to datetime object
    df["datum"] = pd.to_datetime(df["datum"])
    df["kosten"] = df["liter"] * df["preis_pro_liter"]
    df["kumuliert"] = df["kosten"].cumsum()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # plot cost per tank
    fig.add_trace(
        go.Scatter(
            x=df["datum"],
            y=df["kosten"],
            name="pro Tank",
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
            name="kumuliert",
            mode="lines+markers",
            line=dict(shape="linear", color="#ff7f0e", width=3),
            marker=dict(size=6, opacity=0.8)
        ),
        secondary_y=True
    )

    fig.update_yaxes(title_text="Kosten pro Tank (€)", secondary_y=False)
    fig.update_yaxes(title_text="Kumulative Kosten (€)", secondary_y=True)
    fig.update_xaxes(title_text="Datum")
    fig.update_layout(template="plotly_dark", hovermode="x unified")
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})


def efficiency(data):
    """
    Plot efficiency of car in terms of fuel consumption per 100km
    """

    if not data:
        return "<p>Keine Daten vorhanden.</p>"

    df = pd.DataFrame([dict(r) for r in data])

    # Nur Tank-Daten nehmen
    df = df[df["event"] == "Tanken"].copy()

    # Datum in datetime
    df["datum"] = pd.to_datetime(df["datum"])

    # Verbrauch pro 100 km berechnen
    df = df.sort_values("datum")

    # to numeric value
    df["kilometer"] = pd.to_numeric(df["kilometer"], errors="coerce")
    df["liter"] = pd.to_numeric(df["liter"], errors="coerce")

    df["km_diff"] = df["kilometer"].diff()  # Differenz zum vorherigen Eintrag
    df["verbrauch_100km"] = df["liter"] / df["km_diff"] * 100
    df = df.dropna(subset=["verbrauch_100km"])  # ersten Eintrag hat keinen diff

    # Monat extrahieren
    df["monat"] = df["datum"].dt.to_period("M")

    # Durchschnittlicher Verbrauch pro Monat
    monthly = df.groupby("monat")["verbrauch_100km"].mean().reset_index()

    # Plot
    fig = go.Figure(
        go.Bar(
            x=monthly["monat"].astype(str),
            y=monthly["verbrauch_100km"],
            text=monthly["verbrauch_100km"].round(2),
            textposition="auto",
            marker_color="#1f77b4"
        )
    )

    fig.update_layout(
        title="Durchschnittlicher Verbrauch pro 100 km pro Monat",
        xaxis_title="Monat",
        yaxis_title="Verbrauch (l/100 km)",
        template="plotly_dark"
    )

    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})


def cost_overview(data):
    """
    Plot overview of total costs as pie chart
    """
    
    if not data:
        return "<p>Keine Daten vorhanden.</p>"

    df = pd.DataFrame([dict(r) for r in data])

    # Sicherstellen, dass die Spalte "kosten" existiert
    if "kosten" not in df.columns:
        # Falls nur Tankdaten vorhanden sind: kosten = liter * preis_pro_liter
        df["kosten"] = df["liter"] * df["preis_pro_liter"]

    # Gruppieren nach Event, Summen bilden
    grouped = df.groupby("event")["kosten"].sum().reset_index()

    # Pie-Chart erstellen
    fig = go.Figure(
        data=[go.Pie(labels=grouped["event"], values=grouped["kosten"], hole=0.3)]
    )
    fig.update_layout(template="plotly_dark")

    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'responsive': True})
