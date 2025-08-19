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
    "✨ El bot estará disponible 🔥 2 días antes del evento."
    "⏳ Vuelve pronto y usa /start para comenzar. 🙌"
)

def parse_fecha(date_str: str) -> datetime | None:
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
            f"✨ El bot estará disponible 🔥 {PRELAUNCH_DAYS} días antes del evento.\n\n"
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

# Usuarios quemados (cédulas/ correos)
USUARIOS_AUTORIZADOS: Dict[str, str] = {
    "1234567890": "Alejandro Bedoya",
    "alejandro.bedoya@gmail.com": "Alejandro Bedoya",
    "9876543210": "Daniel Vásquez",
    "daniel.vasquez@gmail.com": "Daniel Vásquez",
    # Agrega más...
}

DATA_DIR = Path(__file__).parent / "data"
AGENDA_PDF = DATA_DIR / "agenda.pdf"   # Si no existe, se enviará texto
VIDEOS_DIR = DATA_DIR / "videos"
DOCS_DIR = DATA_DIR / "docs"

# Catálogos de materiales
VIDEOS: Dict[str, Path] = {
    "Video demo": VIDEOS_DIR / "TACTICAL TRADING 20 s.mov",   # .mov o .mp4
}
DOCUMENTOS: Dict[str, Path] = {
    "Documento PDF": DOCS_DIR / "RECOMENDACIONES LIZBETH CAROLINA VALVERDE CHILANGUAY.pdf",
    "Hoja Excel (CSV)": DOCS_DIR / "contactos_limpios_week.csv",
    "Documento Word": DOCS_DIR / "Proyecto de práctica.docx",
}

# Enlaces
ENLACES_INTERES: Dict[str, str] = {
    "Página JP Tactical Trading": "https://ttrading.co",
    "Canal YouTube": "https://www.youtube.com/@JPTacticalTrading",
}
ENLACES_CONEXION: Dict[str, str] = {
    "Conexión Sala Principal": "https://example.com/sala-principal",
    "Conexión Sala Alterna": "https://example.com/sala-alterna",
}
UBICACION_URL = "https://maps.app.goo.gl/zZfR7kPo9ZR1AUtu9"

# =========================
# MENÚS
# =========================

def principal_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Agenda", callback_data="menu_agenda")],
        [InlineKeyboardButton("📚 Material de apoyo", callback_data="menu_material")],
        [InlineKeyboardButton("🔗 Enlaces y Conexión", callback_data="menu_enlaces")],
        [InlineKeyboardButton("📍 Ubicación", callback_data="menu_ubicacion")],
    ])

def material_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Videos de interés", callback_data="material_videos")],
        [InlineKeyboardButton("📄 Documentos", callback_data="material_documentos")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

def enlaces_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Enlaces de interés", callback_data="enlaces_interes")],
        [InlineKeyboardButton("🧩 Conexión al evento", callback_data="enlaces_conexion")],
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

def ubicacion_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📍 Abrir en Google Maps", url=UBICACION_URL)],
        [InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu_principal")],
    ])

def lista_archivos_inline(diccionario: Dict[str, Path], prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for nombre, _ in diccionario.items():
        rows.append([InlineKeyboardButton(nombre, callback_data=f"{prefix}:{nombre}")])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="menu_material")])
    return InlineKeyboardMarkup(rows)

def lista_enlaces_inline(diccionario: Dict[str, str]) -> InlineKeyboardMarkup:
    rows = []
    for nombre, url in diccionario.items():
        rows.append([InlineKeyboardButton(nombre, url=url)])
    rows.append([InlineKeyboardButton("⬅️ Volver", callback_data="menu_enlaces")])
    return InlineKeyboardMarkup(rows)

# Reply keyboard (persistente)
BTN_AGENDA = "📅 Agenda"
BTN_MATERIAL = "📚 Material de apoyo"
BTN_ENLACES = "🔗 Enlaces y Conexión"
BTN_UBICACION = "📍 Ubicación"
BTN_CERRAR = "❌ Cerrar menú"

def bottom_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(BTN_AGENDA), KeyboardButton(BTN_MATERIAL)],
            [KeyboardButton(BTN_ENLACES), KeyboardButton(BTN_UBICACION)],
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
            await update.message.reply_text("📚 *Material de apoyo*", reply_markup=material_inline(), parse_mode="Markdown")
            return
        if texto == BTN_ENLACES:
            await update.message.reply_text("🔗 *Enlaces y Conexión*", reply_markup=enlaces_inline(), parse_mode="Markdown")
            return
        if texto == BTN_UBICACION:
            await accion_ubicacion(update, context)
            return
        if texto == BTN_CERRAR:
            await update.message.reply_text("Menú ocultado. Usa /menu para mostrarlo de nuevo.", reply_markup=ReplyKeyboardRemove())
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
            f"¡Hola, {primer_nombre}! 😊\n{BIENVENIDA}".replace("}}", "}"),  # evita typo accidental de doble llave
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

    if data == "volver_menu_principal":
        await query.edit_message_text("Menú principal:", reply_markup=principal_inline())
        return

    if data == "menu_agenda":
        await accion_agenda(query, context)
        return

    if data == "menu_material":
        await query.edit_message_text("📚 *Material de apoyo*", reply_markup=material_inline(), parse_mode="Markdown")
        return

    if data == "material_videos":
        if not VIDEOS:
            await query.edit_message_text("No hay videos disponibles por el momento.", reply_markup=material_inline())
        else:
            await query.edit_message_text("🎬 *Videos de interés*:", reply_markup=lista_archivos_inline(VIDEOS, "video"), parse_mode="Markdown")
        return

    if data == "material_documentos":
        if not DOCUMENTOS:
            await query.edit_message_text("No hay documentos disponibles por el momento.", reply_markup=material_inline())
        else:
            await query.edit_message_text("📄 *Documentos*:", reply_markup=lista_archivos_inline(DOCUMENTOS, "doc"), parse_mode="Markdown")
        return

    if data == "menu_enlaces":
        await query.edit_message_text("🔗 *Enlaces y Conexión*", reply_markup=enlaces_inline(), parse_mode="Markdown")
        return

    if data == "menu_ubicacion":
        await accion_ubicacion(query, context)
        return

    if data == "enlaces_interes":
        if not ENLACES_INTERES:
            await query.edit_message_text("No hay enlaces de interés disponibles por ahora.", reply_markup=enlaces_inline())
        else:
            await query.edit_message_text("⭐ Enlaces de interés:", reply_markup=lista_enlaces_inline(ENLACES_INTERES))
        await query.message.reply_text("Menú principal:", reply_markup=principal_inline())
        return

    if data == "enlaces_conexion":
        texto = f"{ALERTA_CONEXION}\n\nSelecciona una opción:"
        if not ENLACES_CONEXION:
            await query.edit_message_text(texto + "\n\nNo hay enlaces de conexión todavía.", parse_mode="Markdown")
        else:
            await query.edit_message_text(texto, reply_markup=lista_enlaces_inline(ENLACES_CONEXION), parse_mode="Markdown")
        await query.message.reply_text("Menú principal:", reply_markup=principal_inline())
        return

    if data.startswith("video:"):
        nombre = data.split(":", 1)[1]
        ruta = VIDEOS.get(nombre)
        if ruta:
            await envia_documento(update, context, ruta, nombre)
        else:
            await query.message.reply_text("No se encontró el video solicitado.")
        return

    if data.startswith("doc:"):
        nombre = data.split(":", 1)[1]
        ruta = DOCUMENTOS.get(nombre)
        if ruta:
            await envia_documento(update, context, ruta, nombre)
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
