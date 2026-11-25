"""Panel de sectores del S&P 500 (Streamlit).

Precios: yfinance (ETFs sectoriales SPDR + SPY + VIX).
Macro: FRED (tipos, curva, inflación). Es opcional: sin clave, solo se muestra el VIX.
Herramienta de seguimiento y aprendizaje, no asesoramiento financiero.
"""
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Sectores S&P 500", page_icon="📊", layout="centered")

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
.block-container{max-width:560px;padding-top:2rem}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.tile{border-radius:10px;padding:8px 10px}
.tile .n{font-size:.85rem;font-weight:600;line-height:1.25}
.tile .d{font-size:.7rem;opacity:.7;margin:1px 0 6px;line-height:1.25}
.tile .v{font-size:1rem;font-weight:600;text-align:right}
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
[class*="st-key-hdr_"]{margin:1.3rem 0 .4rem}
[class*="st-key-hdr_"] [data-testid="stHorizontalBlock"]{flex-direction:row!important;flex-wrap:nowrap!important;align-items:center;gap:.5rem}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]){min-width:0!important;width:auto!important}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]):first-child{flex:1 1 0!important}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]):last-child{flex:0 0 auto!important}
[class*="st-key-hdr_"] button{padding:0 .6rem;min-height:1.8rem}
.legend{display:flex;flex-wrap:wrap;align-items:center;gap:5px;font-size:.7rem;opacity:.7;margin-top:8px}
.legend i{display:block;width:20px;height:10px;border-radius:2px}
.banner{margin-top:8px;font-size:.85rem;padding:8px 10px;border-radius:10px}
.ph{border:1px solid rgba(128,128,128,.3);border-radius:10px;padding:10px}
.ph .t{font-size:.85rem;font-weight:600}
.ph .s{font-size:.7rem;opacity:.7;margin:1px 0 6px}
.ph p{font-size:.78rem;margin:2px 0;line-height:1.3}
.note{font-size:.72rem;opacity:.6;margin-top:6px}
</style>
"""


# ---------------------------------------------------------------- datos
@st.cache_data(ttl=240, show_spinner="Descargando precios…")
def load_prices() -> pd.DataFrame:
    tickers = TICKERS + [BENCH, "^VIX"]
    df = yf.download(tickers, period="3y", auto_adjust=True, progress=False)["Close"]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.dropna(how="all").ffill()


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


def ref_date(last: pd.Timestamp, period: str) -> pd.Timestamp:
    return {
        "1S": last - pd.Timedelta(days=7),
        "1M": last - pd.DateOffset(months=1),
        "3M": last - pd.DateOffset(months=3),
        "6M": last - pd.DateOffset(months=6),
        "1A": last - pd.DateOffset(years=1),
        "YTD": pd.Timestamp(year=last.year - 1, month=12, day=31),
    }[period]


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
        ("md", "Cada casilla es un sector del S&P 500 con lo que ha subido o bajado en el periodo elegido. Cada sector se sigue con un ETF de SPDR, un fondo que replica ese sector."),
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


def grid(items: list[str]) -> str:
    return "<div class='grid'>" + "".join(items) + "</div>"


# ---------------------------------------------------------------- panel
@st.fragment(run_every=300)  # se refresca solo cada 5 minutos
def dashboard():
    period = st.segmented_control(
        "Periodo", PERIODS, default="3M", label_visibility="collapsed", key="periodo"
    ) or "3M"

    try:
        prices = load_prices()
    except Exception as e:
        st.error(f"No se pudieron descargar los precios: {e}")
        return
    if prices.empty or BENCH not in prices:
        st.error("No hay datos de precios disponibles ahora mismo.")
        return

    last = prices.index[-1]
    ref = ref_date(last, period)
    ret = (prices.iloc[-1] / prices.asof(ref) - 1) * 100
    spy = ret[BENCH]
    sat = SATURATION[period]
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    st.caption(
        f"Último dato de mercado: {last:%d/%m/%Y} · consultado a las {now:%H:%M}. "
        "Precios con posible retraso de unos 15 min."
    )

    # --- contexto macro
    sec("Contexto macro", "cambio en el periodo", "macro")
    vix = prices["^VIX"].dropna()
    cards = [card("VIX (miedo)", fmt(vix.iloc[-1], 1, False),
                  f"{fmt(vix.iloc[-1] - vix.asof(ref))} pts")]
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
    st.markdown(grid(cards), unsafe_allow_html=True)

    # --- mapa de calor
    sec("Mapa de calor por sector", "", "mapa")
    order = sorted(TICKERS, key=lambda t: ret[t], reverse=True)
    info = {s[0]: s for s in SECTORS}
    tiles = [
        f"<div class='tile' style='background:{tile_color(ret[t], sat)}'>"
        f"<div class='n'>{info[t][1]}</div><div class='d'>{info[t][2]}</div>"
        f"<div class='v'>{fmt(ret[t])}%</div></div>"
        for t in order
    ]
    st.markdown(grid(tiles), unsafe_allow_html=True)
    swatches = "".join(
        f"<i style='background:{tile_color(v, sat)}'></i>"
        for v in (-sat, -sat / 2, 0, sat / 2, sat)
    )
    st.markdown(
        f"<div class='legend'><span>-{sat}%</span>{swatches}<span>+{sat}%</span>"
        f"<span style='width:100%'>Color máximo a partir de ±{sat}% en este periodo</span></div>",
        unsafe_allow_html=True,
    )

    # --- fuerza relativa
    sec("Fuerza relativa frente al S&amp;P 500", f"S&amp;P 500: {fmt(spy)}%", "fuerza")
    rel = {t: ret[t] - spy for t in TICKERS}
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

    # --- vista de ciclo
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

    # --- estado de cada sector en el ciclo
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


st.markdown(CSS, unsafe_allow_html=True)
st.markdown("### Sectores del S&P 500")
dashboard()
