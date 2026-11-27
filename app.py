"""Panel de sectores del S&P 500 (Streamlit).

Precios: yfinance (ETFs sectoriales SPDR + SPY + VIX).
Macro: FRED (tipos, curva, inflación). Es opcional: sin clave, solo se muestra el VIX.
Herramienta de seguimiento y aprendizaje, no asesoramiento financiero.
"""
import os
from datetime import date, datetime, timedelta
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
EN = {  # nombres en inglés (clasificación GICS), para reconocerlos en otras webs y apps
    "XLK": "Information Technology", "XLC": "Communication Services", "XLY": "Consumer Discretionary",
    "XLF": "Financials", "XLI": "Industrials", "XLB": "Materials", "XLRE": "Real Estate",
    "XLV": "Health Care", "XLP": "Consumer Staples", "XLU": "Utilities", "XLE": "Energy",
}
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
.tile .en{font-size:.7rem;opacity:.75;font-style:italic;line-height:1.2;margin-top:1px}
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
.af{font-size:.72rem;opacity:.85;text-align:right;margin-top:2px}
.chg{width:100%;border-collapse:collapse;font-size:.78rem;margin-top:6px}
.chg th{font-weight:600;text-align:left;opacity:.7;padding:4px 6px}
.chg td{padding:4px 6px;border-top:1px solid rgba(128,128,128,.2)}

@media (min-width:700px){
  .grid.tiles{grid-template-columns:repeat(3,minmax(0,1fr))}
  .grid.cards{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
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

/* selector de fecha + botón Hoy en la misma fila (también en móvil) */
[class*="st-key-daterow_"] [data-testid="stHorizontalBlock"]{flex-direction:row!important;flex-wrap:nowrap!important;align-items:flex-end;gap:.5rem}
[class*="st-key-daterow_"] :is([data-testid="stColumn"],[data-testid="column"]){min-width:0!important;width:auto!important}
[class*="st-key-daterow_"] :is([data-testid="stColumn"],[data-testid="column"]):first-child{flex:1 1 0!important}
[class*="st-key-daterow_"] :is([data-testid="stColumn"],[data-testid="column"]):last-child{flex:0 0 auto!important}

/* título de bloque + botón ⓘ en la misma línea (también en móvil) */
[class*="st-key-hdr_"]{margin:1.3rem 0 .4rem}
[class*="st-key-hdr_"] [data-testid="stHorizontalBlock"]{flex-direction:row!important;flex-wrap:nowrap!important;align-items:center;justify-content:flex-start;gap:.5rem}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]){min-width:0!important;width:auto!important}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]):first-child{flex:0 1 auto!important}
[class*="st-key-hdr_"] :is([data-testid="stColumn"],[data-testid="column"]):last-child{flex:0 0 auto!important}
[class*="st-key-hdr_"] button{padding:0 .6rem;min-height:1.8rem}

/* ventana de ayuda: fórmulas y tablas no se salen de la pantalla (scroll horizontal si hace falta) */
[data-testid="stPopoverBody"]{max-width:calc(100vw - 1.5rem)!important}
.katex{font-size:1.05em}
.katex-display{overflow-x:auto;overflow-y:hidden;max-width:100%;padding:.2rem 0;margin:.5em 0}
[data-testid="stPopoverBody"] table{display:block;overflow-x:auto;max-width:100%}
@media (max-width:640px){.katex{font-size:.9em}}
</style>
"""


# ---------------------------------------------------------------- datos
@st.cache_data(ttl=1500, show_spinner="Descargando precios…")
def load_prices() -> pd.DataFrame:
    tickers = TICKERS + [BENCH, "^VIX"]
    df = yf.download(tickers, period="6y", auto_adjust=True, progress=False)["Close"]
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
    start = (datetime.today() - timedelta(days=7 * 365)).strftime("%Y-%m-%d")
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


HORIZONS = {
    "+1M": pd.DateOffset(months=1),
    "+3M": pd.DateOffset(months=3),
    "+6M": pd.DateOffset(months=6),
    "+1A": pd.DateOffset(years=1),
}


def after_end(base, choice, last_avail):
    """Fecha hasta la que se muestra lo ocurrido después de `base` (None si está oculto)."""
    if choice == "Oculto":
        return None
    if choice == "Hasta hoy":
        return last_avail
    return min(base + HORIZONS[choice], last_avail)


def horizon_picker(base, last_avail, key: str) -> str:
    """Selector de horizonte: solo ofrece los que ya han ocurrido a partir de `base`."""
    opts = ["Oculto"] + [h for h, off in HORIZONS.items() if base + off <= last_avail] + ["Hasta hoy"]
    if st.session_state.get(key) not in opts:  # la selección anterior ya no es válida con esta fecha
        st.session_state[key] = "Oculto"
    return st.segmented_control("Ver qué pasó después de esa fecha", opts, key=key) or "Oculto"


def _go_today(key: str):
    st.session_state[key] = datetime.now(ZoneInfo("Europe/Madrid")).date()
    if "d" in st.query_params:
        del st.query_params["d"]


def parse_date(txt):
    try:
        return datetime.strptime(txt, "%Y-%m-%d").date()
    except Exception:
        return None


def pick_date(label: str, min_d: date, max_d: date, key: str) -> date:
    """Selector de fecha; por defecto, hoy (o la fecha que venga en la URL)."""
    qd = parse_date(st.query_params.get("d") or "")
    default = min(max(qd, min_d), max_d) if qd else max_d
    with st.container(key=f"daterow_{key}"):
        col_d, col_b = st.columns([3, 1])
        with col_d:
            picked = st.date_input(label, value=default, min_value=min_d, max_value=max_d,
                                   key=key, format="DD/MM/YYYY")
        if isinstance(picked, (list, tuple)):
            picked = picked[0] if picked else default
        picked = picked or default
        with col_b:
            st.button("Hoy", key=f"hoy_{key}", on_click=_go_today, args=(key,), disabled=picked >= max_d)
    return picked


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
    "fecha": [
        ("md", "Por defecto el panel muestra la situación actual. Si eliges una **fecha pasada**, todo se calcula como si estuvieras en ese día: solo se usan datos de esa fecha y anteriores, y los periodos (1S, 1M, 3M…) se miden hacia atrás desde ella. Sirve para estudiar cómo estaba el mercado en un momento concreto.\n\n- Si la fecha cae en fin de semana o festivo, se usa el último cierre anterior.\n- **Ver qué pasó después** te deja elegir el horizonte (+1M, +3M, +6M, +1A o hasta hoy; empieza en Oculto). En el mapa de calor añade el rendimiento posterior de cada sector hasta ese punto; en el gráfico de velas, las velas posteriores más tenues y una línea en la fecha elegida. Solo se ofrecen los horizontes que ya han ocurrido: con una fecha de hace dos semanas, por ejemplo, no hay +1M.\n- El botón **Hoy** vuelve a la situación actual.\n- La inflación solo usa datos publicados al menos unos 45 días antes de la fecha, que es aproximadamente lo que tarda en publicarse el IPC.\n- Es una herramienta de estudio, no una simulación de operaciones, y el pasado no garantiza el futuro."),
    ],
    "macro": [
        ("md", "Datos de la economía que influyen en cómo se comportan los sectores. Bajo cada cifra aparece su **cambio en el periodo** elegido. Las escalas de abajo son orientativas y simplificadas: no existe un umbral oficial de alto o bajo."),
        ("tex", r"\text{Cambio} = \text{valor actual} - \text{valor inicial}"),
        ("md", "**VIX (miedo):** mide la volatilidad que el mercado espera para el S&P 500 en los próximos 30 días. Lo calcula la CBOE a partir de los precios de sus opciones; aquí es un dato ya calculado. Su cambio se mide en puntos.\n\n| VIX | Lectura |\n|---|---|\n| Menos de 15 | Calma total |\n| 15 – 20 | Calma |\n| 20 – 30 | Nerviosismo |\n| Más de 30 | Tensión fuerte |"),
        ("md", "**Bono 10 años:** rentabilidad anual que paga el bono del Tesoro de EE. UU. a 10 años (dato directo de FRED). Su cambio se mide en puntos porcentuales (pp). ¿Está alto o bajo? Depende de con qué lo compares.\n\n**1. Frente a su historia reciente:**\n\n| Rentabilidad | Lectura |\n|---|---|\n| Menos de 2% | Muy baja (típica de 2020–2021) |\n| 2% – 3% | Baja |\n| 3% – 4% | Media |\n| 4% – 5% | Alta |\n| Más de 5% | Muy alta (máximos desde 2007) |\n\nReferencias: el máximo histórico semanal fue 15,68% (octubre de 1981) y el mínimo, 0,55% (agosto de 2020). La media anual fue 0,89% en 2020, 1,45% en 2021, 2,95% en 2022, 3,96% en 2023 y 4,19% en 2024. A finales de octubre de 2026 rondaba el 5% (dato fechado: puede haber cambiado)."),
        ("md", "**2. Frente a la inflación** (rentabilidad real aproximada): un bono que rinde un 4% con una inflación del 3,5% da muy poco en términos reales."),
        ("tex", r"\text{Rentab. real} \approx \text{bono 10 años} - \text{inflación anual}"),
        ("md", "| Rentabilidad real | Lectura |\n|---|---|\n| Negativa | Muy baja: no compensa la inflación |\n| 0% – 1% | Baja |\n| 1% – 2% | Media |\n| Más de 2% | Alta |"),
        ("md", "**Qué implica que el bono a 10 años suba o baje**\n\nIdea clave: el precio de un bono y su rentabilidad van en sentido contrario. Si los inversores venden bonos, su precio baja y su rentabilidad sube; si los compran, ocurre lo contrario. Esa rentabilidad es la referencia de lo que cuesta el dinero a largo plazo: hipotecas, créditos a empresas y la valoración de casi cualquier activo se miden contra ella.\n\n**Si está alta o sube:**\n- El crédito es más caro (hipotecas, deuda de empresas).\n- Los bonos compiten mejor con las acciones, y los beneficios futuros valen menos hoy.\n- Suelen sufrir más: inmobiliario, servicios públicos, empresas muy endeudadas y de crecimiento, como buena parte de tecnología.\n- Suelen aguantar mejor: bancos y aseguradoras, hasta cierto punto.\n\n**Si está baja o baja:**\n- El crédito es más barato y las acciones resultan más atractivas frente a los bonos.\n- Suelen beneficiarse: inmobiliario, servicios públicos y crecimiento.\n- Suelen notarlo los bancos, por un margen de intereses más estrecho."),
        ("md", "**Por qué se mueve:** sube cuando el mercado espera más crecimiento, más inflación o tipos más altos de los bancos centrales; baja cuando espera una economía más débil, menos inflación o recortes de tipos, y también cuando los inversores buscan refugio. Por eso **el mismo nivel puede significar cosas distintas**: una subida porque la economía va fuerte suele sentar bien a la bolsa; una subida por miedo a la inflación, mal. Los movimientos bruscos suelen importar más que el nivel. Conviene mirarlo junto con la inflación (rentabilidad real) y con la curva 10a-2a. Son tendencias generales, no reglas."),
        ("md", "**Curva 10a-2a:** diferencia entre la rentabilidad del bono a 10 años y la del bono a 2 años."),
        ("tex", r"\begin{aligned}\text{Curva} &= \text{rentab. bono 10 años}\\ &\quad - \text{rentab. bono 2 años}\end{aligned}"),
        ("md", "| Curva (pp) | Lectura |\n|---|---|\n| Más de +1 | Pronunciada |\n| 0 a +1 | Normal o plana |\n| Negativa | Invertida: históricamente ha precedido a recesiones, aunque a veces da falsas alarmas |"),
        ("md", "**Inflación anual:** cuánto han subido los precios (IPC de EE. UU.) respecto al mismo mes del año anterior. Se publica una vez al mes y con retraso. El objetivo de la Reserva Federal es un 2%; por encima de un 3% se considera alta."),
        ("tex", r"\text{Inflación} = \left(\frac{IPC_t}{IPC_{t-12}} - 1\right) \times 100"),
        ("md", "Aquí *t* es el mes actual y *t−12*, el mismo mes del año anterior."),
        ("md", "**Discrecional / básico:** compara el precio del ETF de consumo discrecional (coches, ropa, ocio) con el de consumo básico (alimentación, higiene). Si sube, los inversores prefieren lo que depende de que la gente gaste con confianza; si baja, prefieren lo que se consume siempre. Es una pista del apetito por el riesgo del mercado, no una señal."),
        ("tex", r"\text{Ratio} = \frac{P_{\text{discrecional}}}{P_{\text{básico}}}"),
        ("md", "El valor del ratio en sí no importa (depende de los precios de los dos ETFs); lo que importa es su **cambio en el periodo**, que aparece bajo la cifra. A veces gira antes que el mercado, pero no siempre acierta."),
    ],
    "mapa": [
        ("md", "Cada casilla es un sector del S&P 500 con lo que ha subido o bajado en el periodo elegido. Cada sector se sigue con un ETF de SPDR, un fondo que replica ese sector. **Toca una casilla para abrir el gráfico de velas de ese sector.**"),
        ("tex", r"\text{Rendimiento} = \left(\frac{P_{\text{final}}}{P_{\text{inicio}}} - 1\right) \times 100"),
        ("md", "- **P final:** último precio disponible.\n- **P inicio:** último cierre en la fecha de inicio del periodo (hace 7 días, 1, 3, 6 o 12 meses; en YTD, el último cierre del año anterior).\n- Los precios están ajustados por dividendos, así que el resultado incluye lo que reparten.\n\n**Color:** el gris es 0%. Cuanto más se aleja de 0, más intenso es el verde (sube) o el rojo (baja), hasta llegar al color máximo en un umbral que depende del periodo."),
        ("tex", r"\text{intensidad} = \min\left(\frac{|\text{rendimiento}|}{\text{umbral}}, 1\right)"),
        ("md", "Umbrales: 1S ±4%, 1M ±8%, 3M ±15%, 6M ±20%, YTD ±25%, 1A ±35%.\n\n**Nombre de cada sector en español, en inglés y su ETF:**\n\n| Español | English | ETF |\n|---|---|---|\n| Tecnología | Information Technology | XLK |\n| Comunicaciones | Communication Services | XLC |\n| Consumo discrecional | Consumer Discretionary | XLY |\n| Finanzas | Financials | XLF |\n| Industria | Industrials | XLI |\n| Materiales | Materials | XLB |\n| Inmobiliario | Real Estate | XLRE |\n| Salud | Health Care | XLV |\n| Consumo básico | Consumer Staples | XLP |\n| Servicios públicos | Utilities | XLU |\n| Energía | Energy | XLE |"),
    ],
    "fuerza": [
        ("md", "Compara cada sector con el mercado (el S&P 500, que se sigue con el ETF SPY). Responde a: ¿va mejor o peor que el conjunto?"),
        ("tex", r"\begin{aligned}\text{Fuerza relativa} &= \text{rendim. del sector}\\ &\quad - \text{rendim. del S\&P 500}\end{aligned}"),
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
        ("tex", r"\begin{aligned}\text{Momentum} &= r^{k}_{\text{sector}} - r^{k}_{\text{S\&P 500}}\\ r^{k} &= \frac{P_t}{P_{t-k}} - 1\end{aligned}"),
        ("md", "Aquí *n* es el número de sesiones del periodo y *k* las del tramo reciente.\n\n- **Liderando:** fuerza relativa ≥ 0 y momentum ≥ 0.\n- **Debilitándose:** fuerza relativa ≥ 0 y momentum < 0.\n- **Mejorando:** fuerza relativa < 0 y momentum ≥ 0.\n- **Rezagados:** fuerza relativa < 0 y momentum < 0.\n\nEs una versión sencilla de los gráficos de rotación sectorial. Describe lo que ha pasado, no predice lo que pasará.\n\nCon **Ver qué pasó después** se añade una tabla que compara el estado de cada sector en la fecha de análisis con su estado al final del horizonte elegido, calculado igual y con el mismo periodo. ▲ indica que ha mejorado (por ejemplo, de Rezagados a Mejorando), ▼ que ha empeorado y = que no ha cambiado."),
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


STATE_RANK = {"Rezagados": 0, "Mejorando": 1, "Debilitándose": 2, "Liderando": 3}


def sector_states(px: pd.DataFrame, period: str) -> dict:
    """Estado de cada sector como si se mirara el panel en el último día de `px`.

    Fuerza relativa del periodo (>= 0: mejor que el S&P 500) y momentum: si el sector ha ido
    mejor que el S&P 500 en el último cuarto del periodo (mín. 5 sesiones).
    """
    last = px.index[-1]
    ref = ref_date(last, period)
    r = (px.iloc[-1] / value_at(px, ref) - 1) * 100
    k = max(5, len(px.loc[ref:]) // 4)
    w = px[TICKERS + [BENCH]].iloc[-(k + 1):]
    rec = (w.iloc[-1] / w.iloc[0] - 1) * 100
    out = {}
    for t in TICKERS:
        gaining = rec[t] - rec[BENCH] >= 0
        if r[t] - r[BENCH] >= 0:
            out[t] = "Liderando" if gaining else "Debilitándose"
        else:
            out[t] = "Mejorando" if gaining else "Rezagados"
    return out


# ---------------------------------------------------------------- panel
@st.fragment(run_every=1800)  # se refresca solo cada 30 minutos
def dashboard():
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    today = now.date()
    try:
        full = load_prices()
    except Exception as e:
        st.error(f"No se pudieron descargar los precios: {e}")
        return

    qp_period = st.query_params.get("p")
    sec("Periodo y fecha de análisis", "por defecto, hoy", "fecha")
    c1, c2 = st.columns([3, 2])
    with c1:
        period = st.segmented_control(
            "Periodo", PERIODS, default=qp_period if qp_period in PERIODS else "3M", key="periodo"
        ) or "3M"
    with c2:
        asof = pick_date("Fecha de análisis", full.index[0].date() + timedelta(days=366), today, "fecha")
    # todo el panel se calcula solo con datos hasta la fecha elegida
    prices = full.loc[:pd.Timestamp(asof)]
    live = prices.index[-1] == full.index[-1]
    last = prices.index[-1]
    horizon = "Oculto"
    if not live:
        horizon = horizon_picker(last, full.index[-1], "horizonte")
    fut_end = after_end(last, horizon, full.index[-1])
    after = fut_end is not None
    ref = ref_date(last, period)
    ret = (prices.iloc[-1] / value_at(prices, ref) - 1) * 100
    if ret[TICKERS + [BENCH]].isna().any():
        st.error("Faltan datos de precios para este periodo. Inténtalo de nuevo en unos minutos.")
        return
    spy = ret[BENCH]
    sat = SATURATION[period]
    if live:
        st.caption(
            f"Último dato de mercado: {last:%d/%m/%Y} · consultado a las {now:%H:%M}. "
            "Precios con posible retraso de unos 15 min."
        )
    else:
        extra = ""
        if after:
            fut_spy = (value_at(full, fut_end)[BENCH] / prices[BENCH].iloc[-1] - 1) * 100
            extra = f" Hasta el {fut_end:%d/%m/%Y}, el S&P 500 ha hecho {fmt(fut_spy)}%."
        st.info(f"Estás viendo el panel tal como estaba el {last:%d/%m/%Y} "
                f"(último cierre disponible hasta la fecha elegida), no la situación actual.{extra}")

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
            y10 = fred("DGS10", key).loc[:last]
            curve = fred("T10Y2Y", key).loc[:last]
            cpi = fred("CPIAUCSL", key).loc[:last - pd.Timedelta(days=45)]  # retraso de publicación del IPC
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
    if "XLY" in prices and "XLP" in prices:
        px_ref = value_at(prices, ref)
        r_now = prices["XLY"].iloc[-1] / prices["XLP"].iloc[-1]
        r_ref = px_ref["XLY"] / px_ref["XLP"]
        cards.append(card("Discrecional / básico", fmt(r_now, 2, False), f"{fmt((r_now / r_ref - 1) * 100)}%"))
    st.markdown(grid(cards, "cards"), unsafe_allow_html=True)

    # --- mapa de calor (cada casilla enlaza al gráfico del sector)
    sec("Mapa de calor por sector", "toca un sector para ver su gráfico", "mapa")
    order = sorted(TICKERS, key=lambda t: ret[t], reverse=True)
    info = {s[0]: s for s in SECTORS}
    dpar = "" if live else f"&amp;d={asof.isoformat()}"
    fut = (value_at(full, fut_end) / prices.iloc[-1] - 1) * 100 if after else None
    after_lbl = "hasta hoy" if horizon == "Hasta hoy" else horizon
    tiles = [
        f"<a class='tile' href='?sector={t}&amp;p={period}{dpar}' target='_self' "
        f"style='background:{tile_color(ret[t], sat)}'>"
        f"<div class='n'>{info[t][1]}</div><div class='en'>{EN[t]}</div><div class='d'>{info[t][2]}</div>"
        f"<div class='v'>{fmt(ret[t])}%</div>"
        + (f"<div class='af'>Después ({after_lbl}): {fmt(fut[t])}%</div>" if after else "")
        + "</a>"
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
        st_now = sector_states(prices, period)
        states = {"Liderando": [], "Debilitándose": [], "Mejorando": [], "Rezagados": []}
        for t in sorted(TICKERS, key=rel.get, reverse=True):
            states[st_now[t]].append(NAME[t])
        desc = {"Liderando": "Fuertes y acelerando", "Debilitándose": "Fuertes, pero frenan",
                "Mejorando": "Flojos, pero recuperan", "Rezagados": "Débiles y sin impulso"}
        boxes = [
            f"<div class='ph'><div class='t'>{s}</div><div class='s'>{desc[s]}</div>"
            + ("".join(f"<p>{x}</p>" for x in names) or "<p style='opacity:.5'>Ninguno</p>")
            + "</div>"
            for s, names in states.items()
        ]
        st.markdown(grid(boxes), unsafe_allow_html=True)
        if after:
            # mismo cálculo, pero como si se mirara el panel al final del horizonte elegido
            st_after = sector_states(full.loc[:fut_end], period)
            body = ""
            for t in sorted(TICKERS, key=rel.get, reverse=True):
                a, b = STATE_RANK[st_now[t]], STATE_RANK[st_after[t]]
                if b > a:
                    mark = f"<span style='color:{GREEN_HEX}'>▲</span>"
                elif b < a:
                    mark = f"<span style='color:{RED_HEX}'>▼</span>"
                else:
                    mark = "<span style='opacity:.5'>=</span>"
                body += f"<tr><td>{NAME[t]}</td><td>{st_now[t]}</td><td>{st_after[t]} {mark}</td></tr>"
            st.markdown(
                "<div class='note' style='font-size:.8rem;opacity:.85;margin-top:10px'>Cómo cambió el estado: "
                f"en la fecha de análisis y el {fut_end:%d/%m/%Y} ({after_lbl}), con el mismo periodo.</div>"
                f"<table class='chg'><tr><th>Sector</th><th>En la fecha</th><th>Después ({after_lbl})</th></tr>"
                f"{body}</table>",
                unsafe_allow_html=True,
            )
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
    # 10 años: permite estudiar fechas pasadas y calentar la media de 200 sesiones
    df = yf.download(ticker, period="10y", auto_adjust=True, progress=False)
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
    today = datetime.now(ZoneInfo("Europe/Madrid")).date()
    if st.button("← Volver al panel"):
        back_period = st.query_params.get("p")
        chosen = st.session_state.get("fecha_g")
        st.query_params.clear()
        if back_period in PERIODS:
            st.query_params["p"] = back_period
        if isinstance(chosen, date) and chosen < today:
            st.query_params["d"] = chosen.isoformat()
        st.rerun()

    st.markdown(f"### {name}")
    st.caption(f"{EN[ticker]} · ETF {ticker} · {desc} · {GROUP_TXT[group]}")
    try:
        full = load_ohlc(ticker)
    except Exception as e:
        st.error(f"No se pudo descargar el gráfico: {e}")
        return

    default_candles = "Semanales" if mobile else "Diarias"  # menos velas = más legible en pantalla estrecha
    c1, c2 = st.columns(2)
    window = c1.segmented_control("Ventana de tiempo", list(WINDOWS), default="1A", key="ventana") or "1A"
    candles = c2.segmented_control("Tipo de vela", ["Diarias", "Semanales"], default=default_candles,
                                   key="velas") or default_candles
    sec("Fecha de análisis", "por defecto, hoy", "fecha")
    c3, c4 = st.columns(2)
    with c3:
        asof = pick_date("Fecha de análisis", full.index[0].date() + timedelta(days=366), today, "fecha_g")
    end = full.loc[:pd.Timestamp(asof)].index[-1]  # último cierre disponible hasta esa fecha
    live = end == full.index[-1]
    horizon = "Oculto"
    with c4:
        if not live:
            horizon = horizon_picker(end, full.index[-1], "horizonte_g")
    fut_end = after_end(end, horizon, full.index[-1])
    after = fut_end is not None
    if not live:
        st.info(f"Estás viendo el gráfico hasta el {end:%d/%m/%Y}, no la situación actual.")
    touch = True
    if mobile:
        touch = st.toggle(
            "Ver precios al tocar el gráfico", value=False, key="tocar",
            help="Desactivado, el gráfico no bloquea el scroll de la página. Si lo activas, tocar una vela "
                 "muestra sus precios, pero en algunos móviles puede impedir hacer scroll sobre el gráfico.",
        )

    # las medias solo usan datos anteriores a cada punto, así que calcularlas sobre todo el histórico
    # da el mismo valor que tendrían en esa fecha
    close = full["Close"]
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    start = end - WINDOWS[window]
    last_vis = fut_end if after else end

    before = full.loc[start:end]
    post = full.iloc[0:0]
    if after:
        boundary = end
        if candles == "Semanales" and end.weekday() != 4:
            boundary = end + pd.offsets.Week(weekday=4)  # las velas semanales se cierran el viernes
        post = full.loc[boundary + pd.Timedelta(days=1):fut_end]
    ma50v, ma200v = ma50.loc[start:last_vis], ma200.loc[start:last_vis]
    if candles == "Semanales":
        agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
        before = before.resample("W-FRI").agg(agg).dropna()
        if len(post):
            post = post.resample("W-FRI").agg(agg).dropna()
        ma50v, ma200v = ma50v.resample("W-FRI").last(), ma200v.resample("W-FRI").last()
    idx = before.index.append(post.index)
    ma50v, ma200v = ma50v.reindex(idx), ma200v.reindex(idx)

    # cruces de medias (en datos diarios)
    diff = ma50 - ma200
    prev = diff.shift()
    up = diff[(diff > 0) & (prev <= 0)].loc[start:last_vis].index
    down = diff[(diff < 0) & (prev >= 0)].loc[start:last_vis].index

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=before.index, open=before["Open"], high=before["High"], low=before["Low"], close=before["Close"],
        name="Precio", increasing_line_color=GREEN_HEX, increasing_fillcolor=GREEN_HEX,
        decreasing_line_color=RED_HEX, decreasing_fillcolor=RED_HEX,
    ))
    if len(post):
        fig.add_trace(go.Candlestick(
            x=post.index, open=post["Open"], high=post["High"], low=post["Low"], close=post["Close"],
            name="Después", opacity=0.45, increasing_line_color=GREEN_HEX, increasing_fillcolor=GREEN_HEX,
            decreasing_line_color=RED_HEX, decreasing_fillcolor=RED_HEX,
        ))
        x_cut = before.index[-1]
        fig.add_shape(type="line", x0=x_cut, x1=x_cut, xref="x", y0=0, y1=1, yref="paper",
                      line=dict(color="rgba(128,128,128,.8)", width=1, dash="dash"))
    fig.add_trace(go.Scatter(x=idx, y=ma50v, mode="lines", name="Media 50",
                             line=dict(color="#EF9F27", width=1.6)))
    fig.add_trace(go.Scatter(x=idx, y=ma200v, mode="lines", name="Media 200",
                             line=dict(color="#378ADD", width=1.6)))
    for xs, label, symbol, color in ((up, "Cruce dorado", "triangle-up", GREEN_HEX),
                                     (down, "Cruce de la muerte", "triangle-down", RED_HEX)):
        if len(xs):
            fig.add_trace(go.Scatter(
                x=xs, y=ma50.loc[xs], mode="markers", name=label,
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
    extra_lg = ("<span>┆ Fecha de análisis</span><span style='opacity:.7'>Velas tenues: lo que pasó después</span>"
                if len(post) else "")
    st.markdown(
        "<div class='lg2'>"
        "<span><i style='background:#EF9F27'></i>Media 50</span>"
        "<span><i style='background:#378ADD'></i>Media 200</span>"
        f"<span style='color:{GREEN_HEX}'>▲ Cruce dorado</span>"
        f"<span style='color:{RED_HEX}'>▼ Cruce de la muerte</span>{extra_lg}</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(fig, config=config)

    # datos bajo el gráfico (en la fecha de análisis)
    price, m50, m200 = close.loc[end], ma50.loc[end], ma200.loc[end]
    ok = pd.notna(m50) and pd.notna(m200)
    usd = lambda v: f"{fmt(v, 2, False)} USD" if pd.notna(v) else "—"  # noqa: E731
    dist = lambda m: f"{fmt((price / m - 1) * 100)}%" if pd.notna(m) else "—"  # noqa: E731
    sec("Dónde está el precio")
    st.markdown(grid([
        card("Cierre", usd(price), f"{end:%d/%m/%Y}"),
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
    if after:
        fut = (close.loc[:fut_end].iloc[-1] / price - 1) * 100
        st.markdown(
            f"<div class='note' style='font-size:.8rem;opacity:.85'>Después: desde el {end:%d/%m/%Y} "
            f"hasta el {fut_end:%d/%m/%Y}, {name} ha hecho {fmt(fut)}%.</div>",
            unsafe_allow_html=True,
        )

    st.link_button(f"Ver {ticker} en Investing.com ↗",
                   INVESTING.get(ticker, f"https://es.investing.com/search/?q={ticker}"))
    st.caption("Abre la ficha del ETF de EE. UU. en Investing.com; en el móvil, en su app si la tienes instalada. "
               "Para el ETF europeo que compres, busca su nombre o su ISIN.")
    st.markdown(
        "<div class='note' style='text-align:center;margin-top:18px'>"
        "Herramienta de seguimiento y aprendizaje. No es asesoramiento financiero.</div>",
        unsafe_allow_html=True,
    )


def resources():
    with st.expander("Recursos y para aprender más"):
        st.markdown("**Lecturas**")
        st.markdown(
            "- [StockCharts ChartSchool: Sector Rotation Analysis](https://chartschool.stockcharts.com/table-of-contents/market-analysis/sector-rotation-analysis) (inglés): cómo se relaciona la rotación de sectores con el ciclo económico.\n"
            "- [Clasificación sectorial de la Bolsa española (BME)](https://www.bolsasymercados.es/dam/descargas/exchange/renta-variable/clasificacion-sectorial-bme-renta-variable-es.pdf): los siete sectores de la bolsa española.\n"
            "- [STOXX: clasificación ICB](https://stoxx.com/stoxx-indices-incorporate-new-icb-framework/) (inglés): los supersectores del STOXX Europe 600.\n"
            "- FRED, fuente de los datos macro: [bono 10 años](https://fred.stlouisfed.org/series/DGS10), "
            "[curva 10a-2a](https://fred.stlouisfed.org/series/T10Y2Y), [IPC](https://fred.stlouisfed.org/series/CPIAUCSL)."
        )
        st.markdown("**Fichas de cada sector en Investing.com**")
        st.markdown("\n".join(f"- [{NAME[t]} ({EN[t]})]({INVESTING[t]})" for t in TICKERS))
        st.markdown("**Conceptos**")
        st.markdown(
            "- **Rendimiento acumulado** (en StockCharts, *PerfChart*): un gráfico con una línea por sector, todas "
            "empezando en 0 % el mismo día, que muestra cuánto ha subido o bajado cada una desde entonces. El mapa de "
            "calor es una foto del periodo; este gráfico enseña cuándo un sector adelanta a otro.\n"
            "- **Ratio discrecional / básico:** ya está en el contexto macro; su botón ⓘ lo explica.\n"
            "- **Fases del ciclo y sectores:** modelo teórico que relaciona qué sectores suelen liderar en cada fase "
            "de la economía. Es una guía histórica, no una regla; la página de StockCharts lo explica con detalle."
        )
        st.markdown("**Ideas para más adelante**")
        st.markdown(
            "- Gráfico de rendimiento acumulado por sector desde una fecha.\n"
            "- Tabla de sectores y fases del ciclo, con la fase que mejor encaja con el liderazgo actual.\n"
            "- Revisar qué sectores cuentan como cíclicos (hoy tecnología y energía quedan fuera).\n"
            "- Materias primas (petróleo, cobre, oro) junto a los bonos en el contexto macro.\n"
            "- Versión europea del panel (STOXX 600 o MSCI Europe).\n"
            "- Etiqueta alto/bajo directamente en la tarjeta del bono."
        )


# ---------------------------------------------------------------- enrutado
st.markdown(CSS, unsafe_allow_html=True)
_sector = st.query_params.get("sector")
if _sector in TICKERS:
    detail(_sector)
else:
    st.markdown("### Sectores del S&P 500")
    dashboard()
    resources()
