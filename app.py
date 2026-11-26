"""Panel de sectores del S&P 500 (Streamlit).

Precios: yfinance (ETFs sectoriales SPDR + SPY + VIX).
Macro: FRED (tipos, curva, inflación). Es opcional: sin clave, solo se muestra el VIX.
Herramienta de seguimiento y aprendizaje, no asesoramiento financiero.
"""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Sectores S&P 500", page_icon="📊", layout="wide")

# ---------------------------------------------------------------- configuración
# ticker, nombre, qué incluye, grupo del ciclo
SECTORS = [
    ("XLK", "Tecnología", "Software, chips", "otro"),
    ("XLC", "Comunicaciones", "Telecom, redes, medios", "otro"),
    ("XLY", "Consumo discrecional", "Coches, ropa, ocio", "ciclico"),
    ("XLF", "Finanzas", "Bancos, seguros", "ciclico"),
    ("XLI", "Industria", "Maquinaria, transporte", "ciclico"),
    ("XLB", "Materiales", "Química, minería", "ciclico"),
    ("XLRE", "Inmobiliario", "Alquiler, oficinas", "otro"),
    ("XLV", "Salud", "Farma, hospitales", "defensivo"),
    ("XLP", "Consumo básico", "Alimentación, higiene", "defensivo"),
    ("XLU", "Servicios públicos", "Luz, agua, gas", "defensivo"),
    ("XLE", "Energía", "Petróleo, gas", "otro"),
]
TICKERS = [s[0] for s in SECTORS]
NAME = {s[0]: s[1] for s in SECTORS}
BENCH = "SPY"
PERIODS = ["1S", "1M", "3M", "6M", "YTD", "1A"]
# A partir de este % (en valor absoluto) el color del mapa de calor llega al máximo
SATURATION = {"1S": 4, "1M": 8, "3M": 15, "6M": 20, "YTD": 25, "1A": 35}

GREEN, RED, GREY = (99, 153, 34), (226, 75, 74), (128, 128, 128)
GREEN_HEX, RED_HEX = "#639922", "#E24B4A"

CSS = """
<style>
.block-container{max-width:1180px;padding-top:2rem}
@media (max-width:640px){.block-container{padding-left:.8rem;padding-right:.8rem}}

/* rejillas: 2 columnas en móvil, más en pantallas grandes */
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.tile{border-radius:10px;padding:8px 10px}
.tile .n{font-size:.85rem;font-weight:600;line-height:1.25}
.tile .d{font-size:.7rem;opacity:.7;margin:1px 0 6px;line-height:1.25}
.tile .v{font-size:1rem;font-weight:600;text-align:right}
a.tile{display:block;text-decoration:none!important;color:inherit!important}
a.tile:hover{filter:brightness(1.1)}
.card{background:rgba(128,128,128,.12);border-radius:10px;padding:10px 12px}
.card .l{font-size:.75rem;opacity:.7}
.card .v{font-size:1.25rem;font-weight:600}
.card .c{font-size:.72rem;opacity:.7;margin-top:2px;line-height:1.25}
.row{display:flex;align-items:center;gap:8px;font-size:.78rem;margin:6px 0}
.row .n{width:108px;opacity:.8;line-height:1.25}
.row .val{width:58px;text-align:right;font-weight:600}
.track{flex:1;display:flex;height:12px}
.half{width:50%;display:flex}
.half.l{justify-content:flex-end;border-right:1px solid rgba(128,128,128,.5)}
.bar{height:12px}
.sec{font-size:.85rem;opacity:.7;display:flex;align-items:baseline;gap:8px}
.sec span{font-size:.72rem;opacity:.8}
.legend{display:flex;flex-wrap:wrap;align-items:center;gap:5px;font-size:.7rem;opacity:.7;margin-top:8px}
.legend i{display:block;width:20px;height:10px;border-radius:2px}
.lg2{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.75rem;margin:2px 0 4px;opacity:.9}
.lg2 i{display:inline-block;width:14px;height:3px;margin-right:5px;vertical-align:middle;border-radius:2px}
.banner{margin-top:8px;font-size:.85rem;padding:8px 10px;border-radius:10px}
.ph{border:1px solid rgba(128,128,128,.3);border-radius:10px;padding:10px}
.ph .t{font-size:.85rem;font-weight:600}
.ph .s{font-size:.7rem;opacity:.7;margin:1px 0 6px}
.ph p{font-size:.78rem;margin:2px 0;line-height:1.3}
.note{font-size:.72rem;opacity:.6;margin-top:6px}

@media (min-width:700px){
  .grid.tiles{grid-template-columns:repeat(3,minmax(0,1fr))}
  .grid.cards{grid-template-columns:repeat(4,minmax(0,1fr))}
  .tile{padding:12px 14px}
  .tile .n{font-size:.95rem}
  .tile .d{font-size:.75rem}
  .tile .v{font-size:1.15rem}
  .card .v{font-size:1.4rem}
  .card .l,.card .c{font-size:.8rem}
  .row{font-size:.85rem}
  .row .n{width:150px}
}
@media (min-width:1000px){.grid.tiles{grid-template-columns:repeat(4,minmax(0,1fr))}}

/* título de bloque + botón ⓘ en la misma línea (también en móvil) */
[class*="st-key-hdr_"]{margin:1.3rem 0 .4rem}
[class*="st-key-hdr_"] [data-testid="stHorizontalBlock"]{flex-direction:row!important;flex-wrap:nowrap!important;align-items:center;justify-content:flex-start;gap:.5rem}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]){min-width:0!important;width:auto!important}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]):first-child{flex:0 1 auto!important}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]):last-child{flex:0 0 auto!important}
[class*="st-key-hdr_"] button{padding:0 .6rem;min-height:1.8rem}
</style>
"""


# ---------------------------------------------------------------- datos
@st.cache_data(ttl=1500, show_spinner="Descargando precios…")
def load_prices() -> pd.DataFrame:
    tickers = TICKERS + [BENCH, "^VIX"]
    df = yf.download(tickers, period="3y", auto_adjust=True, progress=False)["Close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna(axis=1, how="all").dropna(how="all").ffill()
    missing = [t for t in TICKERS + [BENCH] if t not in df.columns]
    if missing:  # al lanzar un error, esta respuesta no se guarda en caché
        raise ValueError(
            "Yahoo Finance no devolvió datos de: " + ", ".join(missing)
            + ". Inténtalo de nuevo en unos minutos."
        )
    return df


@st.cache_data(ttl=3600)
def fred(series_id: str, key: str) -> pd.Series:
    start = (datetime.today() - timedelta(days=3 * 365)).strftime("%Y-%m-%d")
    r = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={"series_id": series_id, "api_key": key, "file_type": "json",
                "observation_start": start},
        timeout=15,
    )
    r.raise_for_status()
    s = pd.Series(
        {pd.Timestamp(o["date"]): pd.to_numeric(o["value"], errors="coerce")
         for o in r.json()["observations"]}
    )
    return s.dropna().sort_index()


def fred_key():
    try:
        key = st.secrets.get("FRED_API_KEY")
    except Exception:
        key = None
    return key or os.environ.get("FRED_API_KEY")


def is_mobile() -> bool:
    """Detección aproximada por el User-Agent; solo ajusta valores por defecto del gráfico."""
    try:
        ua = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return any(k in ua for k in ("Mobi", "Android", "iPhone", "iPad"))


def ref_date(last: pd.Timestamp, period: str) -> pd.Timestamp:
    return {
        "1S": last - pd.Timedelta(days=7),
        "1M": last - pd.DateOffset(months=1),
        "3M": last - pd.DateOffset(months=3),
        "6M": last - pd.DateOffset(months=6),
        "1A": last - pd.DateOffset(years=1),
        "YTD": pd.Timestamp(year=last.year - 1, month=12, day=31),
    }[period]


def value_at(df: pd.DataFrame, ref: pd.Timestamp) -> pd.Series:
    """Último valor de cada columna en la fecha ref o antes (por columna)."""
    sub = df.loc[:ref]
    return sub.iloc[-1] if len(sub) else df.iloc[0]


# ---------------------------------------------------------------- formato
def fmt(x: float, d: int = 1, sign: bool = True) -> str:
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace(".", ",")


def tile_color(x: float, sat: float) -> str:
    """Gris neutro en 0; se intensifica hasta el color máximo en ±sat."""
    p = min(abs(x) / sat, 1)
    target = GREEN if x >= 0 else RED
    r, g, b = (round(c0 + (c1 - c0) * p) for c0, c1 in zip(GREY, target))
    return f"rgba({r},{g},{b},{0.18 + 0.62 * p:.2f})"


# Explicaciones de cada bloque: ("md", texto) o ("tex", fórmula)
INFO = {
    "macro": [
        ("md", "Datos de la economía que influyen en cómo se comportan los sectores. Bajo cada cifra aparece su **cambio en el periodo** elegido."),
        ("tex", r"\text{Cambio} = \text{valor actual} - \text{valor al inicio del periodo}"),
        ("md", "- **VIX (miedo):** mide la volatilidad que el mercado espera para el S&P 500 en los próximos 30 días. Lo calcula la CBOE a partir de los precios de las opciones del S&P 500; aquí es un dato ya calculado. Como orientación, por debajo de 20 suele indicar calma y por encima de 30, tensión fuerte. Su cambio se mide en puntos.\n- **Bono 10 años:** rentabilidad anual del bono del Tesoro de EE. UU. a 10 años. Es un dato directo de FRED. Si sube, el dinero se vuelve más caro. Su cambio se mide en puntos porcentuales (pp).\n- **Curva 10a-2a:** diferencia entre la rentabilidad del bono a 10 años y la del bono a 2 años. Si es negativa (curva invertida), históricamente ha precedido a recesiones, aunque no es una garantía."),
        ("tex", r"\text{Curva} = \text{rentab. bono 10 años} - \text{rentab. bono 2 años}"),
        ("md", "- **Inflación anual:** cuánto han subido los precios (IPC de EE. UU.) respecto al mismo mes del año anterior. Se publica una vez al mes y con retraso."),
        ("tex", r"\text{Inflación} = \left(\frac{IPC_{\text{mes actual}}}{IPC_{\text{hace 12 meses}}} - 1\right) \times 100"),
    ],
    "mapa": [
        ("md", "Cada casilla es un sector del S&P 500 con lo que ha subido o bajado en el periodo elegido. Cada sector se sigue con un ETF de SPDR, un fondo que replica ese sector. **Toca una casilla para abrir el gráfico de velas de ese sector.**"),
        ("tex", r"\text{Rendimiento} = \left(\frac{P_{\text{final}}}{P_{\text{inicio}}} - 1\right) \times 100"),
        ("md", "- **P final:** último precio disponible.\n- **P inicio:** último cierre en la fecha de inicio del periodo (hace 7 días, 1, 3, 6 o 12 meses; en YTD, el último cierre del año anterior).\n- Los precios están ajustados por dividendos, así que el resultado incluye lo que reparten.\n\n**Color:** el gris es 0%. Cuanto más se aleja de 0, más intenso es el verde (sube) o el rojo (baja), hasta llegar al color máximo en un umbral que depende del periodo."),
        ("tex", r"\text{intensidad} = \min\left(\frac{|\text{rendimiento}|}{\text{umbral}}, 1\right)"),
        ("md", "Umbrales: 1S ±4%, 1M ±8%, 3M ±15%, 6M ±20%, YTD ±25%, 1A ±35%.\n\n**ETF de cada sector:** Tecnología XLK, Comunicaciones XLC, Consumo discrecional XLY, Finanzas XLF, Industria XLI, Materiales XLB, Inmobiliario XLRE, Salud XLV, Consumo básico XLP, Servicios públicos XLU, Energía XLE."),
    ],
    "fuerza": [
        ("md", "Compara cada sector con el mercado (el S&P 500, que se sigue con el ETF SPY). Responde a: ¿va mejor o peor que el conjunto?"),
        ("tex", r"\text{Fuerza relativa} = \text{rendimiento del sector} - \text{rendimiento del S\&P 500}"),
        ("md", "Se expresa en **puntos porcentuales (pp)**, no en %. Ejemplo: si el sector sube un 5% y el S&P 500 un 3%, su fuerza relativa es +2 pp.\n\nPositivo (verde): va mejor que el mercado. Negativo (rojo): va peor. Un sector puede subir y aun así salir en rojo si sube menos que el mercado. La longitud de las barras se escala respecto al valor más grande."),
    ],
    "ciclo": [
        ("md", "Agrupa sectores según su sensibilidad a la economía y compara el rendimiento medio de cada grupo.\n\n- **Cíclicos** (rinden mejor cuando la economía va bien): consumo discrecional, finanzas, industria y materiales.\n- **Defensivos** (aguantan mejor en las crisis): consumo básico, salud y servicios públicos."),
        ("tex", r"\overline{r}_{\text{cíclicos}} = \frac{r_{XLY} + r_{XLF} + r_{XLI} + r_{XLB}}{4}"),
        ("tex", r"\overline{r}_{\text{defensivos}} = \frac{r_{XLP} + r_{XLV} + r_{XLU}}{3}"),
        ("md", "Es una media simple: todos los sectores pesan lo mismo. Si la de los cíclicos es mayor o igual, aparece **modo confianza**; si es menor, **modo cautela**. Tecnología, comunicaciones, inmobiliario y energía no entran en ninguno de los dos grupos. Es una simplificación: orienta, no predice."),
    ],
    "grafico": [
        ("md", "Cada **vela** resume un periodo (un día o una semana) con cuatro precios: apertura, máximo, mínimo y cierre. Si cierra por encima de donde abrió, es verde; si cierra por debajo, es roja. El cuerpo va de la apertura al cierre y las mechas llegan hasta el máximo y el mínimo."),
        ("md", "Las **medias móviles** suavizan el precio para ver la tendencia. Son medias simples de los últimos *n* cierres diarios, con n = 50 y n = 200 sesiones:"),
        ("tex", r"\text{MM}_n(t) = \frac{1}{n}\sum_{i=0}^{n-1} P_{t-i}"),
        ("md", "Con velas semanales las medias se siguen calculando sobre cierres diarios y se muestra su valor al final de cada semana. La de 200 necesita 200 sesiones de histórico, por eso se descarga más historia de la que se ve.\n\n**Cruces:** cuando la media de 50 cruza por encima de la de 200 se llama *cruce dorado* (triángulo verde); cuando cruza por debajo, *cruce de la muerte* (triángulo rojo). Como las medias usan datos pasados, los cruces llegan **tarde**: confirman una tendencia que ya ha empezado, no la anticipan, y a menudo dan falsas alarmas.\n\n**Distancia a la media:** cuánto se aleja el precio de cada media."),
        ("tex", r"\text{Distancia} = \left(\frac{P}{\text{MM}_n} - 1\right) \times 100"),
        ("md", "Positivo: el precio está por encima de la media. Es una referencia descriptiva, no una señal de compra o venta."),
    ],
    "estado": [
        ("md", "Clasifica cada sector con dos preguntas:\n\n1. **¿Va mejor que el S&P 500 en el periodo?** (fuerza relativa mayor o igual que 0)\n2. **¿Gana fuerza?** Es su *momentum*: si ha ido mejor que el S&P 500 en el último cuarto del periodo (mínimo 5 sesiones)."),
        ("tex", r"k = \max\left(5, \frac{n}{4}\right)"),
        ("tex", r"\text{Momentum} = \left(\frac{P_t}{P_{t-k}} - 1\right)_{\text{sector}} - \left(\frac{P_t}{P_{t-k}} - 1\right)_{\text{S\&P 500}}"),
        ("md", "Aquí *n* es el número de sesiones del periodo y *k* las del tramo reciente.\n\n- **Liderando:** fuerza relativa ≥ 0 y momentum ≥ 0.\n- **Debilitándose:** fuerza relativa ≥ 0 y momentum < 0.\n- **Mejorando:** fuerza relativa < 0 y momentum ≥ 0.\n- **Rezagados:** fuerza relativa < 0 y momentum < 0.\n\nEs una versión sencilla de los gráficos de rotación sectorial. Describe lo que ha pasado, no predice lo que pasará."),
    ],
}


def sec(title: str, right: str = "", info_key: str = "plain"):
    """Título de bloque con un botón ⓘ que abre la explicación."""
    with st.container(key=f"hdr_{info_key}"):
        left, btn = st.columns([6, 1])
        left.markdown(f"<div class='sec'>{title}<span>{right}</span></div>", unsafe_allow_html=True)
        if info_key in INFO:
            with btn.popover("ⓘ"):
                for kind, text in INFO[info_key]:
                    (st.latex if kind == "tex" else st.markdown)(text)


def card(label: str, value: str, change: str) -> str:
    return (f"<div class='card'><div class='l'>{label}</div>"
            f"<div class='v'>{value}</div><div class='c'>{change}</div></div>")


def grid(items: list[str], cls: str = "") -> str:
    return f"<div class='grid {cls}'>" + "".join(items) + "</div>"


# ---------------------------------------------------------------- panel
@st.fragment(run_every=1800)  # se refresca solo cada 30 minutos
def dashboard():
    qp_period = st.query_params.get("p")
    period = st.segmented_control(
        "Periodo", PERIODS, default=qp_period if qp_period in PERIODS else "3M",
        label_visibility="collapsed", key="periodo"
    ) or "3M"

    try:
        prices = load_prices()
    except Exception as e:
        st.error(f"No se pudieron descargar los precios: {e}")
        return

    last = prices.index[-1]
    ref = ref_date(last, period)
    ret = (prices.iloc[-1] / value_at(prices, ref) - 1) * 100
    if ret[TICKERS + [BENCH]].isna().any():
        st.error("Faltan datos de precios para este periodo. Inténtalo de nuevo en unos minutos.")
        return
    spy = ret[BENCH]
    sat = SATURATION[period]
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    st.caption(
        f"Último dato de mercado: {last:%d/%m/%Y} · consultado a las {now:%H:%M}. "
        "Precios con posible retraso de unos 15 min."
    )

    # --- contexto macro
    sec("Contexto macro", "cambio en el periodo", "macro")
    cards = []
    if "^VIX" in prices:
        vix = prices["^VIX"].dropna()
        cards.append(card("VIX (miedo)", fmt(vix.iloc[-1], 1, False),
                          f"{fmt(vix.iloc[-1] - vix.asof(ref))} pts"))
    key = fred_key()
    if key:
        try:
            y10, curve = fred("DGS10", key), fred("T10Y2Y", key)
            cpi = fred("CPIAUCSL", key)
            yoy = ((cpi / cpi.shift(12) - 1) * 100).dropna()
            cards += [
                card("Bono 10 años", f"{fmt(y10.iloc[-1], 2, False)}%",
                     f"{fmt(y10.iloc[-1] - y10.asof(ref), 2)} pp"),
                card("Curva 10a-2a", fmt(curve.iloc[-1], 2),
                     f"{fmt(curve.iloc[-1] - curve.asof(ref), 2)} pp"),
                card("Inflación anual", f"{fmt(yoy.iloc[-1], 1, False)}%",
                     f"{fmt(yoy.iloc[-1] - yoy.asof(ref), 1)} pp"),
            ]
        except Exception as e:
            st.warning(f"No se pudieron cargar los datos de FRED: {e}")
    else:
        st.info("Añade tu clave FRED_API_KEY para ver tipos, curva e inflación.")
    st.markdown(grid(cards, "cards"), unsafe_allow_html=True)

    # --- mapa de calor (cada casilla enlaza al gráfico del sector)
    sec("Mapa de calor por sector", "toca un sector para ver su gráfico", "mapa")
    order = sorted(TICKERS, key=lambda t: ret[t], reverse=True)
    info = {s[0]: s for s in SECTORS}
    tiles = [
        f"<a class='tile' href='?sector={t}&amp;p={period}' target='_self' "
        f"style='background:{tile_color(ret[t], sat)}'>"
        f"<div class='n'>{info[t][1]}</div><div class='d'>{info[t][2]}</div>"
        f"<div class='v'>{fmt(ret[t])}%</div></a>"
        for t in order
    ]
    st.markdown(grid(tiles, "tiles"), unsafe_allow_html=True)
    swatches = "".join(
        f"<i style='background:{tile_color(v, sat)}'></i>"
        for v in (-sat, -sat / 2, 0, sat / 2, sat)
    )
    st.markdown(
        f"<div class='legend'><span>-{sat}%</span>{swatches}<span>+{sat}%</span>"
        f"<span style='width:100%'>Color máximo a partir de ±{sat}% en este periodo</span></div>",
        unsafe_allow_html=True,
    )

    rel = {t: ret[t] - spy for t in TICKERS}
    # en pantallas grandes: fuerza relativa a la izquierda, ciclo y estados a la derecha;
    # en el móvil Streamlit apila las dos columnas
    left, right = st.columns([3, 2], gap="large")

    with left:
        sec("Fuerza relativa frente al S&amp;P 500", f"S&amp;P 500: {fmt(spy)}%", "fuerza")
        mx = max(abs(v) for v in rel.values()) or 1
        rows = ""
        for t in sorted(TICKERS, key=rel.get, reverse=True):
            v = rel[t]
            c = GREEN_HEX if v >= 0 else RED_HEX
            bar = f"<div class='bar' style='width:{abs(v) / mx * 100:.0f}%;background:{c}'></div>"
            rows += (
                f"<div class='row'><div class='n'>{NAME[t]}</div><div class='track'>"
                f"<div class='half l'>{bar if v < 0 else ''}</div>"
                f"<div class='half'>{bar if v >= 0 else ''}</div></div>"
                f"<div class='val' style='color:{c}'>{fmt(v)} pp</div></div>"
            )
        st.markdown(rows + "<div class='note'>Diferencia con el S&amp;P 500 en puntos porcentuales (pp)</div>",
                    unsafe_allow_html=True)

    with right:
        sec("Vista de ciclo", "", "ciclo")
        ci = ret[[s[0] for s in SECTORS if s[3] == "ciclico"]].mean()
        de = ret[[s[0] for s in SECTORS if s[3] == "defensivo"]].mean()
        col = lambda v: GREEN_HEX if v >= 0 else RED_HEX  # noqa: E731
        st.markdown(grid([
            f"<div class='card'><div class='l'>Cíclicos</div><div class='v' style='color:{col(ci)}'>{fmt(ci)}%</div>"
            "<div class='c'>Discrecional, finanzas, industria, materiales</div></div>",
            f"<div class='card'><div class='l'>Defensivos</div><div class='v' style='color:{col(de)}'>{fmt(de)}%</div>"
            "<div class='c'>Básico, salud, servicios públicos</div></div>",
        ]), unsafe_allow_html=True)
        if ci >= de:
            bg, fg, txt = "rgba(99,153,34,.2)", GREEN_HEX, "Modo confianza: los cíclicos van por delante"
        else:
            bg, fg, txt = "rgba(226,75,74,.2)", RED_HEX, "Modo cautela: los defensivos van por delante"
        st.markdown(f"<div class='banner' style='background:{bg};color:{fg}'>{txt}</div>",
                    unsafe_allow_html=True)

        # Fuerza relativa del periodo (>= 0: mejor que el S&P 500) y momentum: si el sector
        # ha ido mejor que el S&P 500 en el último cuarto del periodo (mín. 5 sesiones).
        sec("Estado de cada sector en el ciclo", "", "estado")
        n = len(prices.loc[ref:])
        k = max(5, n // 4)
        window = prices[TICKERS + [BENCH]].iloc[-(k + 1):]
        rec = (window.iloc[-1] / window.iloc[0] - 1) * 100
        states = {"Liderando": [], "Debilitándose": [], "Mejorando": [], "Rezagados": []}
        for t in sorted(TICKERS, key=rel.get, reverse=True):
            gaining = rec[t] - rec[BENCH] >= 0
            if rel[t] >= 0:
                states["Liderando" if gaining else "Debilitándose"].append(NAME[t])
            else:
                states["Mejorando" if gaining else "Rezagados"].append(NAME[t])
        desc = {"Liderando": "Fuertes y acelerando", "Debilitándose": "Fuertes, pero frenan",
                "Mejorando": "Flojos, pero recuperan", "Rezagados": "Débiles y sin impulso"}
        boxes = [
            f"<div class='ph'><div class='t'>{s}</div><div class='s'>{desc[s]}</div>"
            + ("".join(f"<p>{x}</p>" for x in names) or "<p style='opacity:.5'>Ninguno</p>")
            + "</div>"
            for s, names in states.items()
        ]
        st.markdown(grid(boxes), unsafe_allow_html=True)
        lectura = ("los cíclicos van por delante de los defensivos, algo típico de una fase de expansión."
                   if ci >= de else
                   "los defensivos van por delante de los cíclicos, algo típico de una fase de cautela.")
        st.markdown(f"<div class='note' style='font-size:.8rem;opacity:.8'>Lectura: {lectura}</div>",
                    unsafe_allow_html=True)

    st.markdown(
        "<div class='note' style='text-align:center;margin-top:18px'>"
        "Herramienta de seguimiento y aprendizaje. No es asesoramiento financiero.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- detalle de un sector
WINDOWS = {
    "6M": pd.DateOffset(months=6),
    "1A": pd.DateOffset(years=1),
    "2A": pd.DateOffset(years=2),
    "3A": pd.DateOffset(years=3),
}
GROUP_TXT = {"ciclico": "Cíclico", "defensivo": "Defensivo", "otro": "Fuera de cíclicos y defensivos"}

# Fichas de cada ETF en Investing.com (en el móvil abren la app si está instalada)
INVESTING = {
    "XLK": "https://es.investing.com/etfs/spdr-select-sector---technology",
    "XLC": "https://es.investing.com/etfs/communication-services-select-spdr",
    "XLY": "https://es.investing.com/etfs/spdr-consumer-discr.-select-sector",
    "XLF": "https://es.investing.com/etfs/financial-select-sector-spdr-fund",
    "XLI": "https://es.investing.com/etfs/industrial-sector-spdr-trust",
    "XLB": "https://es.investing.com/etfs/spdr-materials-select-sector-etf",
    "XLRE": "https://es.investing.com/etfs/real-estate-select-sector-spdr",
    "XLV": "https://es.investing.com/etfs/spdr---health-care",
    "XLP": "https://es.investing.com/etfs/spdr---consumer-staples",
    "XLU": "https://es.investing.com/etfs/spdr-select-sector---utilities",
    "XLE": "https://es.investing.com/etfs/spdr-energy-select-sector-fund",
}


@st.cache_data(ttl=1800, show_spinner="Descargando el histórico…")
def load_ohlc(ticker: str) -> pd.DataFrame:
    # 5 años: la media de 200 sesiones necesita calentamiento antes de la ventana visible
    df = yf.download(ticker, period="5y", auto_adjust=True, progress=False)
    if df is None or df.empty:
        raise ValueError(f"Yahoo Finance no devolvió datos de {ticker}. Inténtalo de nuevo en unos minutos.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def detail(ticker: str):
    _, name, desc, group = next(s for s in SECTORS if s[0] == ticker)
    mobile = is_mobile()
    if st.button("← Volver al panel"):
        back_period = st.query_params.get("p")
        st.query_params.clear()
        if back_period in PERIODS:
            st.query_params["p"] = back_period
        st.rerun()

    st.markdown(f"### {name}")
    st.caption(f"ETF {ticker} · {desc} · {GROUP_TXT[group]}")
    default_candles = "Semanales" if mobile else "Diarias"  # menos velas = más legible en pantalla estrecha
    c1, c2 = st.columns(2)
    window = c1.segmented_control("Ventana de tiempo", list(WINDOWS), default="1A", key="ventana") or "1A"
    candles = c2.segmented_control("Tipo de vela", ["Diarias", "Semanales"], default=default_candles,
                                   key="velas") or default_candles
    touch = True
    if mobile:
        touch = st.toggle(
            "Ver precios al tocar el gráfico", value=False, key="tocar",
            help="Desactivado, el gráfico no bloquea el scroll de la página. Si lo activas, tocar una vela "
                 "muestra sus precios, pero en algunos móviles puede impedir hacer scroll sobre el gráfico.",
        )

    try:
        df = load_ohlc(ticker)
    except Exception as e:
        st.error(f"No se pudo descargar el gráfico: {e}")
        return

    # medias sobre TODO el histórico diario; después se recorta a la ventana visible
    close = df["Close"]
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    start = df.index[-1] - WINDOWS[window]
    view, ma50v, ma200v = df.loc[start:], ma50.loc[start:], ma200.loc[start:]

    # cruces de medias (en datos diarios)
    diff = ma50 - ma200
    prev = diff.shift()
    up = diff[(diff > 0) & (prev <= 0)].loc[start:].index
    down = diff[(diff < 0) & (prev >= 0)].loc[start:].index

    if candles == "Semanales":
        view = view.resample("W-FRI").agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
        ).dropna()
        ma50v = ma50v.resample("W-FRI").last().reindex(view.index)
        ma200v = ma200v.resample("W-FRI").last().reindex(view.index)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=view.index, open=view["Open"], high=view["High"], low=view["Low"], close=view["Close"],
        name="Precio", increasing_line_color=GREEN_HEX, increasing_fillcolor=GREEN_HEX,
        decreasing_line_color=RED_HEX, decreasing_fillcolor=RED_HEX,
    ))
    fig.add_trace(go.Scatter(x=ma50v.index, y=ma50v, mode="lines", name="Media 50",
                             line=dict(color="#EF9F27", width=1.6)))
    fig.add_trace(go.Scatter(x=ma200v.index, y=ma200v, mode="lines", name="Media 200",
                             line=dict(color="#378ADD", width=1.6)))
    for idx, label, symbol, color in ((up, "Cruce dorado", "triangle-up", GREEN_HEX),
                                      (down, "Cruce de la muerte", "triangle-down", RED_HEX)):
        if len(idx):
            fig.add_trace(go.Scatter(
                x=idx, y=ma50.loc[idx], mode="markers", name=label,
                marker=dict(symbol=symbol, size=11, color=color, line=dict(width=1, color="white")),
            ))
    # leyenda propia en HTML (la de Plotly ocupa 2-3 filas en pantallas estrechas)
    fig.update_layout(
        height=560 if mobile else 640, margin=dict(l=6, r=6, t=8, b=6), showlegend=False,
        hovermode="x unified", xaxis_rangeslider_visible=False,
        dragmode=False if mobile else "pan",
    )
    fig.update_xaxes(automargin=True, fixedrange=mobile)
    fig.update_yaxes(automargin=True, side="right", fixedrange=True)  # eje de precios a la derecha
    if candles == "Diarias":
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # sin huecos de fin de semana

    if mobile and not touch:
        config = {"staticPlot": True}  # sin interacción: el dedo siempre hace scroll de la página
    elif mobile:
        config = {"displayModeBar": False, "scrollZoom": False}
    else:
        config = {"displayModeBar": "hover", "scrollZoom": False,
                  "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toImage"]}

    sec("Gráfico de velas", "", "grafico")
    st.markdown(
        "<div class='lg2'>"
        "<span><i style='background:#EF9F27'></i>Media 50</span>"
        "<span><i style='background:#378ADD'></i>Media 200</span>"
        f"<span style='color:{GREEN_HEX}'>▲ Cruce dorado</span>"
        f"<span style='color:{RED_HEX}'>▼ Cruce de la muerte</span></div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, config=config)

    # datos bajo el gráfico
    price, m50, m200 = close.iloc[-1], ma50.iloc[-1], ma200.iloc[-1]
    ok = pd.notna(m50) and pd.notna(m200)
    usd = lambda v: f"{fmt(v, 2, False)} USD" if pd.notna(v) else "—"  # noqa: E731
    dist = lambda m: f"{fmt((price / m - 1) * 100)}%" if pd.notna(m) else "—"  # noqa: E731
    sec("Dónde está el precio")
    st.markdown(grid([
        card("Último cierre", usd(price), f"{df.index[-1]:%d/%m/%Y}"),
        card("Media 50", usd(m50), f"Precio {dist(m50)} respecto a ella"),
        card("Media 200", usd(m200), f"Precio {dist(m200)} respecto a ella"),
        card("Media 50 vs 200", f"{fmt((m50 / m200 - 1) * 100)}%" if ok else "—",
             "Diferencia entre las dos medias"),
    ], "cards"), unsafe_allow_html=True)
    if ok:
        if price > m50 > m200:
            lectura = "el precio está sobre ambas medias y la de 50 sobre la de 200: tendencia alcista."
        elif price < m50 < m200:
            lectura = "el precio está bajo ambas medias y la de 50 bajo la de 200: tendencia bajista."
        else:
            lectura = "señales mixtas: el precio y las medias no están alineados."
        st.markdown(f"<div class='note' style='font-size:.8rem;opacity:.8'>Lectura: {lectura}</div>",
                    unsafe_allow_html=True)

    st.link_button(f"Ver {ticker} en Investing.com ↗",
                   INVESTING.get(ticker, f"https://es.investing.com/search/?q={ticker}"))
    st.caption("Abre la ficha del ETF de EE. UU. en Investing.com; en el móvil, en su app si la tienes instalada. "
               "Para el ETF europeo que compres, busca su nombre o su ISIN.")
    st.markdown(
        "<div class='note' style='text-align:center;margin-top:18px'>"
        "Herramienta de seguimiento y aprendizaje. No es asesoramiento financiero.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- enrutado
st.markdown(CSS, unsafe_allow_html=True)
_sector = st.query_params.get("sector")
if _sector in TICKERS:
    detail(_sector)
else:
    st.markdown("### Sectores del S&P 500")
    dashboard()
