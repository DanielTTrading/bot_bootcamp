import os
import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from typing import Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.constants import ChatAction
from telegram.error import TimedOut, NetworkError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# =========================
# CONFIGURACIÓN Y DATOS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # En Railway lo pondrás como variable
USE_WEBHOOK = os.getenv("USE_WEBHOOK", "true").lower() == "true"
PORT = int(os.getenv("PORT", "8080"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")  # p.ej. https://tuapp.up.railway.app
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}" if BOT_TOKEN else "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""

# --- PRE-LANZAMIENTO ---
LAUNCH_DATE_STR = os.getenv("LAUNCH_DATE", "")         # 'YYYY-MM-DD'
PRELAUNCH_DAYS = int(os.getenv("PRELAUNCH_DAYS", "2"))
PRELAUNCH_MESSAGE = os.getenv(
    "PRELAUNCH_MESSAGE",
    "✨ El bot estará disponible 🔥 el día del evento."
    "⏳ Vuelve pronto y usa /start para comenzar. 🙌"
)

# --- WIFI (para el botón Conectarme a la red) ---
WIFI_SSID = os.getenv("WIFI_SSID", "NombreDeRed")
WIFI_PASS = os.getenv("WIFI_PASS", "Contrasena123")

def parse_fecha(date_str: str):
    try:
        y, m, d = map(int, date_str.split("-"))
        return datetime(y, m, d, tzinfo=timezone.utc)
    except Exception:
        return None

def hoy_utc() -> datetime:
    return datetime.now(timezone.utc)

def esta_en_prelanzamiento() -> tuple[bool, str]:
    """
    True + mensaje si aún no se habilita el bot completo.
    Habilita desde (LAUNCH_DATE - PRELAUNCH_DAYS).
    Si LAUNCH_DATE no está, no hay pre-lanzamiento.
    """
    launch_dt = parse_fecha(LAUNCH_DATE_STR)
    if not launch_dt:
        return (False, "")  # habilitado

    habilita_dt = launch_dt - timedelta(days=PRELAUNCH_DAYS)
    now = hoy_utc()
    if now < habilita_dt:
        dias = (habilita_dt.date() - now.date()).days
        msg = (
            f"✨ El bot estará disponible 🔥 el día del evento.\n\n"
            f"⏳ Faltan {dias} días, vuelve pronto. 🙌\n\n"
            f"{PRELAUNCH_MESSAGE}"
        )
        return (True, msg)
    return (False, "")

# Mensajes base
NOMBRE_EVENTO = "Bootcamp 2025 - 2 de JP Tactical Trading"

BIENVENIDA = (
    f"🎉 ¡Bienvenido/a al {NOMBRE_EVENTO}! 🎉\n\n"
    "Has sido validado correctamente.\n"
    "Usa el menú para navegar."
)

ALERTA_CONEXION = (
    "⚠️ **Aviso importante**:\n"
    "Si durante la conexión se detecta una persona **no registrada**, será **expulsada**.\n"
    "Por favor, no compartas estos accesos."
)

USUARIOS_AUTORIZADOS: Dict[str, str] = {
    "75106729": "Daniel Mejia sanchez",
    "furolol@gmail.com": "Daniel Mejia sanchez",
    "1020457973": "Camilo medina",
    "camilo.mp@outlook.com": "Camilo medina",
    "1030552115": "Elver Camilo Jimenez",
    "elvercjb@gmail.com": "Elver Camilo Jimenez",
    "42129600": "Paula Brito",
    "pandreaco10@gmail.com": "Paula Brito",
    "71268184": "Ariel Martinez Gomez",
    "aristidesariel@gmail.com": "Ariel Martinez Gomez",
    "1097305559": "Jairo Alexander Shanchez Barajas",
    "jaalsa95@gmail.com": "Jairo Alexander Shanchez Barajas",
    "1037655024": "Maria Alejandra Sanchez",
    "masb.25@hotmail.com": "Maria Alejandra Sanchez",
    "1039472598": "Daniel Mora Gomez",
    "danielmoragomez01@gmail.com": "Daniel Mora Gomez",
    "mesamaria455@gmail.com": "Maria Jose Mesa Giraldo",
    "jcmesa@capitalbrokersusa.com": "JC Mesa",
    "juanitapuertapaz@gmail.com": "Juanita Puerta",
    "j_uli345@hotmail.com": "Julian Agudelo Rodriguez",
    "52691946": "Juliana Rojas Lopez",
    "julianarojaslopez@hotmail.com": "Juliana Rojas Lopez",
    "80739456": "Arley Giovanny Rojas Guerrero",
    "arley4@hotmail.com": "Arley Giovanny Rojas Guerrero",
    "1137045027": "Sandra Milena Cardenas",
    "neva2101@gmail.com": "Sandra Milena Cardenas",
    "1017130257": "Esteban Maya Restrepo",
    "emayares1@gmail.com": "Esteban Maya Restrepo",
    "1024602544": "Jhon Alexander Melo Ramos",
    "jhonalexandermeloramos99@gmail.com": "Jhon Alexander Melo Ramos",
    "1034989739": "Juan Sebastian Rodriguez Tobon",
    "juansert0707@gmail.com": "Juan Sebastian Rodriguez Tobon",
    "1144029342": "Stepany Rodriguez Arevalo",
    "totdenimjeans1@gmail.com": "Stepany Rodriguez Arevalo",
    "42895010": "Monica",
    "monasaldarriaga@gmail.com": "Monica",
    "1000603972": "Hernan David Buenaventura Mora",
    "hernan.buenaventura@gmail.com": "Hernan David Buenaventura Mora",
    "16771533": "Luis Alberto Vergara",
    "luchovergara@yahoo.com": "Luis Alberto Vergara",
    "43277879": "Isabel Cristina Vieira Jaramillo",
    "cristyvieira@hotmail.com": "Isabel Cristina Vieira Jaramillo",
    "1007005133": "Nicolas Torres",
    "nicolas.torres.caicedo@gmail.com": "Nicolas Torres",
    "1005220317": "Julian Alexander Muñoz Lozada",
    "julmunozlo@unal.edu.co": "Julian Alexander Muñoz Lozada",
    "1011512032": "Luisa Tobon Bustamante",
    "1000888528": "Andres Ruiz Velasquez",
    "andreruiz122@gmail.com": "Andres Ruiz Velasquez",
    "1144203808": "Zaid Oquendo",
    "zaidoquendomanjarres31@gmail.com": "Zaid Oquendo",
    "1098809467": "Andres Duran Leon",
    "ed.andresdl@gmail.com": "Andres Duran Leon",
    "1000236231": "Cristian Camilo Carvajal",
    "ccarvajalm.arq@gmail.com": "Cristian Camilo Carvajal",
    "43975708": "Lina Patricia Zuluaga Lopez",
    "linazuluaga06@hotmail.com": "Lina Patricia Zuluaga Lopez",
    "1115183424": "Cesar Hernan Hurtado Ospina",
    "chho139@hotmail.com": "Cesar Hernan Hurtado Ospina",
    "1023878380": "Fernando Jose Diaz Maldonado",
    "fndo.diaz@gmail.com": "Fernando Jose Diaz Maldonado",
    "91488364": "Jaime Gonzalez",
    "jaime.gonzalezjr@hotmail.com": "Jaime Gonzalez",
    "35426141": "Nalieth Karina Ruiz",
    "nali.ruiz@gmail.com": "Nalieth Karina Ruiz",
    "79519766": "Daniel La Rotta",
    "dlarotta@gmail.com": "Daniel La Rotta",
    "1039455401": "Juan Esteban Restrepo",
    "juan.e.restrepo.re@gmail.com": "Juan Esteban Restrepo",
    "10135356": "Jorge Edison Marin Lopez",
    "jemplop69@hotmail.com": "Jorge Edison Marin Lopez",
    "79951742": "Juclher Hernando Moreno Higuera",
    "hernando.moreno@juclher.com": "Juclher Hernando Moreno Higuera",
    "1000944038": "Pablo Guarin Yepes",
    "pabloguarinyepes@gmail.com": "Pablo Guarin Yepes",
    "43738828": "Alexandra Yepes",
    "1001699989": "Oscar Lopez",
    "oscarlopez@gmail.com": "Oscar Lopez",
    "987654321": "Carlos Perez",
    "carlosperez@hotmail.com": "Carlos Perez",
    "1234567890": "Alejandro Bedoya",
    "alejandro.bedoya@gmail.com": "Alejandro Bedoya",
    "999888777": "Daniel Vasquez",
    "daniel.vasquez@gmail.com": "Daniel Vasquez"
}

DATA_DIR = Path(__file__).parent / "data"
AGENDA_PDF = DATA_DIR / "agenda.pdf"   # Si no existe, se enviará texto
VIDEOS_DIR = DATA_DIR / "videos"
DOCS_DIR = DATA_DIR / "docs"

# =========================
# PRESENTADORES
# =========================
# IDs cortos para callback_data
PRESENTADORES = [
    ("p1", "Juan Pablo Vieira"),
    ("p2", "Juan José Puerta"),
    ("p3", "Carlos Andrés Pérez"),
    ("p4", "Jorge Mario Rubio"),
    ("p5", "Jair Viana"),
]

# ==== Materiales por presentador (archivos locales) ====
MATERIALES: Dict[str, Dict[str, Dict[str, Path]]] = {
    "p1": {"videos": {}, "docs": {}},
    "p2": {"videos": {}, "docs": {}},
    "p3": {"videos": {}, "docs": {}},
    "p4": {"videos": {}, "docs": {}},
    "p5": {"videos": {}, "docs": {}},
}
# Ejemplo futuro (archivos):
MATERIALES["p2"]["docs"]["VALORACIÓN RAPIDA JP TACTICAL"] = DOCS_DIR / "VALORACIÓN RAPIDA JP TACTICAL.xlsx"
MATERIALES["p2"]["docs"]["VALORACIÓN RAPIDA JP TACTICAL DIDACTICA"] = DOCS_DIR / "VALORACIÓN RAPIDA- DIDACTICA-2.xlsx"
# MATERIALES["p2"]["videos"]["Intro a la estrategia"] = VIDEOS_DIR / "intro.mp4"

# ==== Videos como ENLACES (Drive) por presentador ====
VIDEO_LINKS: Dict[str, Dict[str, str]] = {
    "p1": {
        "Crear Cuenta en Interactive Brokers": "https://drive.google.com/file/d/1thOot6PZdxLgutH3c3JuCrIwXwRGcxeb/view?usp=sharing",
        "Crear Cuenta en TRII": "https://drive.google.com/file/d/1thOot6PZdxLgutH3c3JuCrIwXwRGcxeb/view?usp=sharing",
    },
    "p2": {
        "DATOS DE EMPRESAS Y MACRO": "https://drive.google.com/file/d/1S-LncN3dd3eYBBCO_YgYuv5n6d2DSGAM/view?usp=sharing",
        "DATOS DE EMPRESAS": "https://drive.google.com/file/d/1Yo1CxNipafXdbcoXK6ahpGgaHdJqdbzj/view?usp=sharing",
        "FRED": "https://drive.google.com/file/d/12SRmvSbdhrS0qeM4dFE1EMSkScH4hKcL/view?usp=sharing",
        "HERRAMIENTA D.O.O.R": "https://drive.google.com/file/d/1zwejfDpdC7Z0CVsCb4t0UqQD0yqdPBBe/view?usp=sharing",
        "MORNINGSTAR": "https://drive.google.com/file/d/1POiz8YG7xYZpjxaBZ7YiZqmI7RpCQgLa/view?usp=sharing",
        "MOVIMIENTOS DE SENADORES USA": "https://drive.google.com/file/d/1zGIZWRRs3EiMAv-i9DDe5N57XxYWkqx5/view?usp=sharing",
        "PAGINA MORDOR INTELLIGENCE": "https://drive.google.com/file/d/17HMRzdBHknyxLeoB7JA0V9h-gtQrgZX4/view?usp=sharing",
        "PORTAFOLIO GRANDES INVERSORES": "https://drive.google.com/file/d/1-qcP4LNAlCaqajgepQYcREC8fdzwpgY-/view?usp=sharing",
        "SCREENER, MAPS Y DATOS": "https://drive.google.com/file/d/1Mn_SmvqXEijzAOPoNtsnoW3mWksqPdTl/view?usp=sharing",
        "SEC": "https://drive.google.com/file/d/1OwIZ_Bk94RHjQZf0zmxtlH38frrxzb70/view?usp=sharing",
        "VALORACIÓN COMPAÑIA": "https://drive.google.com/file/d/1mqG03xZB8urE7_VA1a8YcRO4nalxnSWD/view?usp=sharing",

    },
    "p3": {},
    "p4": {},
    "p5": {},
}

# ==== Enlaces de interés por presentador ====
ENLACES_POR_PRESENTADOR: Dict[str, Dict[str, str]] = {
    "p1": {
        "Web": "https://ttrading.co",
        "YouTube": "https://www.youtube.com/@JPTacticalTrading",
    },
    "p2": {
        "FRED": "https://fred.stlouisfed.org/",
        "MACRO TRENDS": "https://www.macrotrends.net/",
        "MORNINGSTART": "https://www.morningstar.com/",
        "Web": "https://ttrading.co",
        "YouTube": "https://www.youtube.com/@JPTacticalTrading",
    },
    "p3": {
        "Web": "https://ttrading.co",
        "YouTube": "https://www.youtube.com/@JPTacticalTrading",
    },
    "p4": {
        "Contactanos": "wa.me/message/KMRACEVS2P6GJ1",
        "Instagram Ps. Jorge Mario Rubio": "https://www.instagram.com/tupsicologoencasa?igsh=eThhdW9lamNxMmIy",
    },
    "p5": {
        "Instagram Libertank": "https://www.instagram.com/libertank?igsh=MTV2aXVtd3JydGxuZA==",
        "Instagram Jair Viana": "https://www.instagram.com/jair.viana/",
        "Web": "https://www.instagram.com/libertank?igsh=MTV2aXVtd3JydGxuZA==",
        
    },
}

# ==== Enlaces de conexión (generales) ====
ENLACES_CONEXION: Dict[str, str] = {
    "Bootcamp 23 Agosto Dia 1": "https://us06web.zoom.us/j/81355040883?pwd=3SH8zPwRFLZjAGXtttg0DM1i8ahdyT.1",
    "Bootcamp 24 Agosto Dia 2": "https://us06web.zoom.us/j/81664314444?pwd=NuJTzeaQGI0kKFuP5mh4OuTJoWQLaY.1",
}

# Enlaces de interés (generales)
ENLACES_INTERES: Dict[str, str] = {
    "Página JP Tactical Trading": "https://ttrading.co",
    "Canal YouTube": "https://www.youtube.com/@JPTacticalTrading",
}

UBICACION_URL = "https://maps.app.goo.gl/zZfR7kPo9ZR1AUtu9"

# ==== Exness (nuevo) ====
EXNESS_ACCOUNT_URL = "https://one.exnesstrack.org/a/s3wj0b5qry"
EXNESS_COPY_URL = "https://social-trading.exness.com/strategy/227834645/a/s3wj0b5qry?sharer=trader"

# =========================
# MENÚS
# =========================

def principal_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Agenda", callback_data="menu_agenda")],
        [InlineKeyboardButton("📚 Material de apoyo", callback_data="menu_material")],
        [InlineKeyboardButton("🔗 Enlaces y Conexión", callback_data="menu_enlaces")],
        [InlineKeyboardButton("📍 Ubicación", callback_data="menu_ubicacion")],
        [InlineKeyboardButton("💳 Exness & Copy", callback_data="menu_exness")],
        [InlineKeyboardButton("📶 Conectarme a la red", callback_data="menu_wifi")],  # NUEVO
    ])

def presentadores_keyboard(prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for pid, nombre in PRESENTADORES:
        rows.append([InlineKeyboardButton(nombre, callback_data=f"{prefix}:{pid}")])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")])
    return InlineKeyboardMarkup(rows)

def material_presentador_menu(pid: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        #[InlineKeyboardButton("🎬 Videos", callback_data=f"mat_videos:{pid}")],
        [InlineKeyboardButton("🎥 Videos", callback_data=f"mat_videos_url:{pid}")],  # NUEVO
        [InlineKeyboardButton("📄 Documentos", callback_data=f"mat_docs:{pid}")],
        [InlineKeyboardButton("⬅️ Elegir otro presentador", callback_data="menu_material")],
        [InlineKeyboardButton("🏠 Menú principal", callback_data="volver_menu_principal")],
    ])

def lista_archivos_inline(diccionario: Dict[str, Path], prefix: str, pid: str) -> InlineKeyboardMarkup:
    rows = []
    for nombre in diccionario.keys():
        rows.append([InlineKeyboardButton(nombre, callback_data=f"{prefix}:{pid}:{nombre}")])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data=f"mat_pres:{pid}")])
    return InlineKeyboardMarkup(rows)

def lista_video_links_inline(pid: str) -> InlineKeyboardMarkup:
    enlaces = VIDEO_LINKS.get(pid, {})
    rows = []
    for nombre, url in enlaces.items():
        rows.append([InlineKeyboardButton(nombre, url=url)])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data=f"mat_pres:{pid}")])
    rows.append([InlineKeyboardButton("🏠 Menú principal", callback_data="volver_menu_principal")])
    return InlineKeyboardMarkup(rows)

def enlaces_inline_general() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Enlaces por presentador", callback_data="enlaces_por_presentador")],
        [InlineKeyboardButton("🧩 Conexión al evento", callback_data="enlaces_conexion")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

def enlaces_presentador_lista(pid: str) -> InlineKeyboardMarkup:
    enlaces = ENLACES_POR_PRESENTADOR.get(pid, {})
    rows = []
    for nombre, url in enlaces.items():
        rows.append([InlineKeyboardButton(nombre, url=url)])
    rows.append([InlineKeyboardButton("⬅️ Elegir otro presentador", callback_data="enlaces_por_presentador")])
    rows.append([InlineKeyboardButton("🏠 Menú principal", callback_data="volver_menu_principal")])
    return InlineKeyboardMarkup(rows)

def ubicacion_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Abrir en Google Maps", url=UBICACION_URL)],
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

def exness_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Crear cuenta en Exness", url=EXNESS_ACCOUNT_URL)],
        [InlineKeyboardButton("🤝 Conectar al Copy JP TACTICAL", url=EXNESS_COPY_URL)],
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

def wifi_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

# Reply keyboard (persistente)
BTN_AGENDA = "📅 Agenda"
BTN_MATERIAL = "📚 Material de apoyo"
BTN_ENLACES = "🔗 Enlaces y Conexión"
BTN_UBICACION = "📍 Ubicación"
BTN_WIFI = "📶 Conectarme a la red"  # NUEVO
BTN_CERRAR = "❌ Cerrar menú"

def bottom_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(BTN_AGENDA), KeyboardButton(BTN_MATERIAL)],
            [KeyboardButton(BTN_ENLACES), KeyboardButton(BTN_UBICACION), KeyboardButton(BTN_WIFI)],  # agregado WIFI
            [KeyboardButton(BTN_CERRAR)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

# =========================
# HELPERS
# =========================

def normaliza(clave: str) -> str:
    return clave.strip().lower()

async def envia_documento(upd_or_q, context: ContextTypes.DEFAULT_TYPE, ruta: Path, nombre_mostrar: str):
    """
    Acepta Update o CallbackQuery (upd_or_q).
    Envía documentos y videos con manejo de timeouts + reintentos.
    """
    # Unificar chat y message
    if isinstance(upd_or_q, Update):
        chat = upd_or_q.effective_chat
        message = upd_or_q.effective_message
    else:
        q = upd_or_q  # CallbackQuery
        chat = q.message.chat
        message = q.message

    if not ruta.exists():
        await message.reply_text(f"⚠️ No encuentro el archivo: {nombre_mostrar}")
        return

    ext = ruta.suffix.lower()
    es_video = ext in {".mp4", ".mov", ".m4v"}

    action = ChatAction.UPLOAD_VIDEO if es_video else ChatAction.UPLOAD_DOCUMENT
    texto_espera = "⏳ Preparando y enviando el video… puede tardar unos minutos." if es_video \
                   else "⏳ Preparando y enviando el archivo…"

    await chat.send_action(action=action)
    aviso = await message.reply_text(texto_espera)

    READ_T = 600
    WRITE_T = 600
    intentos = 3

    for i in range(1, intentos + 1):
        try:
            with ruta.open("rb") as f:
                if es_video:
                    await message.reply_video(
                        video=InputFile(f, filename=ruta.name),
                        caption=nombre_mostrar,
                        supports_streaming=True,
                        read_timeout=READ_T,
                        write_timeout=WRITE_T,
                    )
                else:
                    await message.reply_document(
                        document=InputFile(f, filename=ruta.name),
                        caption=nombre_mostrar,
                        read_timeout=READ_T,
                        write_timeout=WRITE_T,
                    )
            await aviso.edit_text("✅ Archivo enviado.")
            await message.reply_text("¿Qué deseas hacer ahora?", reply_markup=principal_inline())
            return

        except (TimedOut, NetworkError) as e:
            if i < intentos:
                espera = 2 ** i
                try:
                    await aviso.edit_text(f"⚠️ Conexión inestable, reintentando en {espera}s… (intento {i}/{intentos})")
                except Exception:
                    pass
                await asyncio.sleep(espera)
                continue
            else:
                await aviso.edit_text(f"❌ No se pudo enviar el archivo por tiempo de espera agotado.\nDetalle: {e}")
                return
        except Exception as e:
            await aviso.edit_text(f"❌ Error al enviar el archivo: {e}")
            return

# =========================
# MIDDLEWARE: VALIDACIÓN
# =========================

@dataclass
class PerfilUsuario:
    nombre: str
    autenticado: bool = False

# Guardaremos por user_id un dict con su perfil
PERFILES: Dict[int, PerfilUsuario] = {}

async def ensure_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, int]:
    user_id = update.effective_user.id if update.effective_user else 0
    perfil = PERFILES.get(user_id)
    return (perfil is not None and perfil.autenticado), user_id

# =========================
# HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Modo pre-lanzamiento
    en_pre, msg = esta_en_prelanzamiento()
    if en_pre:
        await update.message.reply_text(msg)
        return

    await update.message.reply_text(
        f"👋 Hola, este es el bot del {NOMBRE_EVENTO}.\n\n"
        "Para continuar, por favor escribe tu **cédula** o **correo registrado**:",
        reply_markup=bottom_keyboard()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Iniciar/validar acceso\n"
        "/menu - Mostrar menú\n"
        "/help - Ayuda\n"
        "\nPrimero valida tu cédula o correo registrado. Luego usa el menú."
    )

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    autenticado, _ = await ensure_auth(update, context)
    if not autenticado:
        await update.message.reply_text("⚠️ Debes validarte primero. Escribe tu **cédula** o **correo**.")
        return
    await update.message.reply_text("Menú principal:", reply_markup=principal_inline())

async def text_ingreso_o_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Si aún estamos en pre-lanzamiento, no permitir flujos
    en_pre, msg = esta_en_prelanzamiento()
    if en_pre:
        await update.message.reply_text(msg)
        return

    autenticado, user_id = await ensure_auth(update, context)
    texto = (update.message.text or "").strip()

    # Si ya está autenticado, procesar botones del teclado persistente
    if autenticado:
        if texto == BTN_AGENDA:
            await accion_agenda(update, context)
            return
        if texto == BTN_MATERIAL:
            await update.message.reply_text(
                "📚 *Material de apoyo*\nElige un presentador:",
                reply_markup=presentadores_keyboard("mat_pres"),
                parse_mode="Markdown",
            )
            return
        if texto == BTN_ENLACES:
            await update.message.reply_text(
                "🔗 *Enlaces y Conexión*",
                reply_markup=enlaces_inline_general(),
                parse_mode="Markdown",
            )
            return
        if texto == BTN_UBICACION:
            await accion_ubicacion(update, context)
            return
        if texto == BTN_WIFI:
            await accion_wifi(update, context)
            return
        if texto == BTN_CERRAR:
            await update.message.reply_text(
                "Menú ocultado. Usa /menu para mostrarlo de nuevo.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        await update.message.reply_text("Estás autenticado. Usa el menú:", reply_markup=principal_inline())
        return

    # NO autenticado → validar credencial
    clave = normaliza(texto)
    if not clave:
        await update.message.reply_text("❗ Por favor escribe tu **cédula** o **correo**.")
        return

    nombre = USUARIOS_AUTORIZADOS.get(clave)
    if nombre:
        PERFILES[user_id] = PerfilUsuario(nombre=nombre, autenticado=True)
        primer_nombre = nombre.split()[0]
        await update.message.reply_text(
            f"¡Hola, {primer_nombre}! 😊\n{BIENVENIDA}".replace("}}", "}"),
            reply_markup=bottom_keyboard()
        )
        await update.message.reply_text("Menú principal:", reply_markup=principal_inline())
    else:
        await update.message.reply_text(
            "🚫 No estás en la lista de registrados.\n"
            "Ingresa nuevamente tu cédula o correo registrados:",
            reply_markup=bottom_keyboard()
        )

# Acciones comunes reutilizables
async def accion_agenda(upd_or_q, context: ContextTypes.DEFAULT_TYPE):
    # Si aún estamos en pre-lanzamiento, bloquear
    en_pre, msg = esta_en_prelanzamiento()
    if en_pre:
        if isinstance(upd_or_q, Update):
            await upd_or_q.message.reply_text(msg)
        else:
            await upd_or_q.message.reply_text(msg)
        return

    if isinstance(upd_or_q, Update):
        message = upd_or_q.message
        edit = None
    else:
        q = upd_or_q
        message = q.message
        edit = q.edit_message_text

    if AGENDA_PDF.exists():
        if edit:
            await edit("📅 Agenda del evento (PDF disponible para descargar).")
        else:
            await message.reply_text("📅 Agenda del evento (PDF disponible para descargar).")
        await envia_documento(upd_or_q, context, AGENDA_PDF, "Agenda del evento")
        return  # evitar duplicado

    texto = (
        "📅 *Agenda del evento*\n"
        "- Día 1: Introducción y Setup\n"
        "- Día 2: Estrategias y Práctica\n"
        "- Horario: 7:00 pm - 9:00 pm (Hora Colombia)\n\n"
        "_(Puedes subir un PDF como `data/agenda.pdf` para compartirlo automáticamente.)_"
    )
    if edit:
        await edit(texto, parse_mode="Markdown")
    else:
        await message.reply_text(texto, parse_mode="Markdown")

    await message.reply_text("¿Qué deseas hacer ahora?", reply_markup=principal_inline())

async def accion_ubicacion(upd_or_q, context: ContextTypes.DEFAULT_TYPE):
    # Bloqueo en pre-lanzamiento
    en_pre, msg = esta_en_prelanzamiento()
    if en_pre:
        if isinstance(upd_or_q, Update):
            await upd_or_q.message.reply_text(msg)
        else:
            await upd_or_q.message.reply_text(msg)
        return

    if isinstance(upd_or_q, Update):
        message = upd_or_q.message
        edit = None
    else:
        q = upd_or_q
        message = q.message
        edit = q.edit_message_text

    texto = "📍 *Ubicación del evento*\nToca el botón para abrir en Google Maps."
    if edit:
        await edit(texto, parse_mode="Markdown", reply_markup=ubicacion_inline())
    else:
        await message.reply_text(texto, parse_mode="Markdown", reply_markup=ubicacion_inline())

async def accion_wifi(upd_or_q, context: ContextTypes.DEFAULT_TYPE):
    # Bloqueo en pre-lanzamiento (por si lo quieres restringir)
    en_pre, msg = esta_en_prelanzamiento()
    if en_pre:
        if isinstance(upd_or_q, Update):
            await upd_or_q.message.reply_text(msg)
        else:
            await upd_or_q.message.reply_text(msg)
        return

    if isinstance(upd_or_q, Update):
        message = upd_or_q.message
        edit = None
    else:
        q = upd_or_q
        message = q.message
        edit = q.edit_message_text

    texto = (
        "📶 *Wi-Fi del evento*\n\n"
        f"• **Nombre de red:** `{WIFI_SSID}`\n\n"
        #f"• **Clave:** `{WIFI_PASS}`\n\n"
        "_*La red es abierta (no necesita clave) \n\n *Se abre una pestaña, le das en visitantes \n\n *Escoges Estelar easy conection \n\n *Y escribes la palabra Estelar2025_"
    )
    if edit:
        await edit(texto, parse_mode="Markdown", reply_markup=wifi_inline())
    else:
        await message.reply_text(texto, parse_mode="Markdown", reply_markup=wifi_inline())

async def menu_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Bloqueo en pre-lanzamiento
    en_pre, msg = esta_en_prelanzamiento()
    if en_pre:
        await query.message.reply_text(msg)
        return

    autenticado, _ = await ensure_auth(update, context)
    if not autenticado:
        await query.edit_message_text("⚠️ Debes validarte primero. Escribe tu **cédula** o **correo**.")
        return

    data = query.data

    # Volver al menú principal
    if data == "volver_menu_principal":
        await query.edit_message_text("Menú principal:", reply_markup=principal_inline())
        return

    # ====== AGENDA ======
    if data == "menu_agenda":
        await accion_agenda(query, context)
        return

    # ====== MATERIAL POR PRESENTADOR ======
    if data == "menu_material":
        await query.edit_message_text(
            "📚 *Material de apoyo*\nElige un presentador:",
            reply_markup=presentadores_keyboard("mat_pres"),
            parse_mode="Markdown",
        )
        return

    if data.startswith("mat_pres:"):
        pid = data.split(":", 1)[1]
        nombre = next((n for (i, n) in PRESENTADORES if i == pid), "Presentador")
        await query.edit_message_text(
            f"📚 *Material de {nombre}*",
            reply_markup=material_presentador_menu(pid),
            parse_mode="Markdown",
        )
        return

    if data.startswith("mat_videos:"):
        pid = data.split(":", 1)[1]
        videos = MATERIALES.get(pid, {}).get("videos", {})
        if not videos:
            await query.edit_message_text("🎬 No hay videos disponibles por ahora.",
                                          reply_markup=material_presentador_menu(pid))
        else:
            await query.edit_message_text("🎬 *Videos:*",
                                          reply_markup=lista_archivos_inline(videos, "video", pid),
                                          parse_mode="Markdown")
        return

    if data.startswith("mat_videos_url:"):  # NUEVO (Drive)
        pid = data.split(":", 1)[1]
        enlaces = VIDEO_LINKS.get(pid, {})
        if not enlaces:
            await query.edit_message_text("🎥 No hay videos por ahora.",
                                          reply_markup=material_presentador_menu(pid))
        else:
            await query.edit_message_text("🎥 *Videos:*",
                                          reply_markup=lista_video_links_inline(pid),
                                          parse_mode="Markdown")
        return

    if data.startswith("mat_docs:"):
        pid = data.split(":", 1)[1]
        docs = MATERIALES.get(pid, {}).get("docs", {})
        if not docs:
            await query.edit_message_text("📄 No hay documentos disponibles por ahora.",
                                          reply_markup=material_presentador_menu(pid))
        else:
            await query.edit_message_text("📄 *Documentos:*",
                                          reply_markup=lista_archivos_inline(docs, "doc", pid),
                                          parse_mode="Markdown")
        return

    # ====== ENLACES ======
    if data == "menu_enlaces":
        await query.edit_message_text("🔗 *Enlaces y Conexión*",
                                      reply_markup=enlaces_inline_general(),
                                      parse_mode="Markdown")
        return

    if data == "enlaces_por_presentador":
        await query.edit_message_text("⭐ Elige un presentador:",
                                      reply_markup=presentadores_keyboard("link_pres"))
        return

    if data.startswith("link_pres:"):
        pid = data.split(":", 1)[1]
        nombre = next((n for (i, n) in PRESENTADORES if i == pid), "Presentador")
        enlaces = ENLACES_POR_PRESENTADOR.get(pid, {})
        if not enlaces:
            await query.edit_message_text(f"⭐ *Enlaces de {nombre}*\n(No hay enlaces por ahora.)",
                                          reply_markup=enlaces_presentador_lista(pid),
                                          parse_mode="Markdown")
        else:
            await query.edit_message_text(f"⭐ *Enlaces de {nombre}*:",
                                          reply_markup=enlaces_presentador_lista(pid),
                                          parse_mode="Markdown")
        return

    if data == "enlaces_conexion":
        texto = f"{ALERTA_CONEXION}\n\nSelecciona una opción:"
        if not ENLACES_CONEXION:
            await query.edit_message_text(texto + "\n\nNo hay enlaces de conexión todavía.", parse_mode="Markdown")
        else:
            rows = [[InlineKeyboardButton(nombre, url=url)] for nombre, url in ENLACES_CONEXION.items()]
            rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="menu_enlaces")])
            await query.edit_message_text("🧩 Conexiones del evento:", reply_markup=InlineKeyboardMarkup(rows))
        return

    # ====== UBICACIÓN ======
    if data == "menu_ubicacion":
        await accion_ubicacion(query, context)
        return

    # ====== EXNESS ======
    if data == "menu_exness":
        texto = (
            "💳 *Apertura de cuenta y Copy Trading*\n\n"
            "1) Primero crea y **verifica** tu cuenta en Exness.\n"
            "2) Luego conéctate a nuestro **Copy JP TACTICAL**.\n\n"
            "Usa los botones de abajo 👇"
        )
        await query.edit_message_text(texto, parse_mode="Markdown", reply_markup=exness_inline())
        return

    # ====== WIFI ======
    if data == "menu_wifi":
        await accion_wifi(query, context)
        return

    # ====== Descargas concretas (videos/documentos) ======
    if data.startswith("video:"):
        # formato: video:<pid>:<titulo>
        _, pid, titulo = data.split(":", 2)
        ruta = MATERIALES.get(pid, {}).get("videos", {}).get(titulo)
        if ruta:
            await envia_documento(update, context, ruta, titulo)
        else:
            await query.message.reply_text("No se encontró el video solicitado.")
        return

    if data.startswith("doc:"):
        # formato: doc:<pid>:<titulo>
        _, pid, titulo = data.split(":", 2)
        ruta = MATERIALES.get(pid, {}).get("docs", {}).get(titulo)
        if ruta:
            await envia_documento(update, context, ruta, titulo)
        else:
            await query.message.reply_text("No se encontró el documento solicitado.")
        return

# =========================
# MAIN / ARRANQUE
# =========================

def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("Falta la variable de entorno BOT_TOKEN.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_ingreso_o_menu))
    app.add_handler(CallbackQueryHandler(menu_callbacks))

    return app


if __name__ == "__main__":
    application = build_app()

    if USE_WEBHOOK and WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=WEBHOOK_URL,
        )
    else:
        print("Iniciando en modo polling. Establece USE_WEBHOOK=true y WEBHOOK_HOST para producción.")
        application.run_polling(drop_pending_updates=True)
