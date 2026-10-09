"""Las "manos" de JARVIS: acciones reales en tu Mac y consultas a internet.

Cada función hace una cosa y devuelve la frase que JARVIS dirá en voz alta.
comandos.py decide cuál usar según lo que digas.
"""

import glob
import html
import os
import subprocess
import time

import httpx
from ddgs import DDGS

import fechas

# Ciudad que se usa para el clima cuando no dices otra.
CIUDAD_CASA = "Ciudad de México"
# Calendario donde se guardan los eventos nuevos (los tuyos: "Casa" o "Trabajo").
CALENDARIO = "Casa"

# Nombres en español → nombre real de la app en la Mac.
APPS_EN_ESPANOL = {
    "calculadora": "Calculator", "notas": "Notes", "calendario": "Calendar", "recordatorios": "Reminders",
    "musica": "Music", "mensajes": "Messages", "fotos": "Photos", "correo": "Mail", "mail": "Mail",
    "mapas": "Maps", "configuracion": "System Settings", "ajustes": "System Settings",
    "preferencias": "System Settings", "contactos": "Contacts", "reloj": "Clock", "camara": "Photo Booth",
    "vista previa": "Preview", "libros": "Books", "clima": "Weather", "el tiempo": "Weather",
    "notas de voz": "VoiceMemos", "atajos": "Shortcuts", "telefono": "Phone", "chrome": "Google Chrome",
    "google": "Google Chrome", "visual studio": "Visual Studio Code", "vs code": "Visual Studio Code",
    "bolsa": "Stocks", "notas adhesivas": "Stickies", "editor de texto": "TextEdit", "buscar": "FindMy",
}


def _applescript(codigo, *argumentos):
    """Ejecuta AppleScript. Los argumentos llegan como `item N of argv` (seguro ante comillas)."""
    resultado = subprocess.run(["osascript", "-e", codigo, *argumentos],
                               capture_output=True, text=True, timeout=60)
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr.strip())
    return resultado.stdout.strip()


# Convierte argumentos de texto en una fecha de AppleScript (independiente del idioma de la Mac).
FECHA_APPLESCRIPT = '''
on armarFecha(anio, mes, dia, hora, minuto)
    set f to current date
    set day of f to 1
    set year of f to anio as integer
    set month of f to mes as integer
    set day of f to dia as integer
    set time of f to (hora as integer) * 3600 + (minuto as integer) * 60
    return f
end armarFecha
'''


def _partes(cuando):
    return [str(x) for x in (cuando.year, cuando.month, cuando.day, cuando.hour, cuando.minute)]


# ---------- Controlar la Mac ----------

def _apps_instaladas():
    rutas = []
    for carpeta in ["/Applications", "/System/Applications", os.path.expanduser("~/Applications")]:
        rutas += glob.glob(f"{carpeta}/*.app") + glob.glob(f"{carpeta}/*/*.app")
    return {os.path.basename(r)[:-4]: r for r in rutas}


def abrir_app(nombre):
    buscado = fechas.sin_acentos(nombre.lower()).strip()
    buscado = APPS_EN_ESPANOL.get(buscado, buscado)
    apps = _apps_instaladas()
    elegida = (next((a for a in apps if a.lower() == buscado.lower()), None)
               or next((a for a in apps if a.lower().startswith(buscado.lower())), None)
               or next((a for a in apps if buscado.lower() in a.lower()), None))
    if not elegida:
        return f"No encontré ninguna app llamada {nombre}, señor."
    subprocess.run(["open", apps[elegida]])
    return f"Abriendo {elegida}, señor."


def reproducir_spotify(enlace):
    """Reproduce en Spotify. Acepta spotify:track:... o un enlace https://open.spotify.com/..."""
    if enlace.startswith("https://open.spotify.com/"):
        tipo, codigo = enlace.split("open.spotify.com/")[1].split("?")[0].split("/")[:2]
        enlace = f"spotify:{tipo}:{codigo}"
    subprocess.run(["open", "-a", "Spotify"])
    for _ in range(15):  # espera a que Spotify termine de abrir
        if _applescript('tell application "System Events" to (name of processes) contains "Spotify"') == "true":
            break
        time.sleep(1)
    time.sleep(2)
    _applescript('on run argv\n tell application "Spotify" to play track (item 1 of argv)\nend run', enlace)
    return "Reproduciendo en Spotify, señor."


def abrir_web(url, navegador="Google Chrome"):
    subprocess.run(["open", "-a", navegador, url])
    return f"Abriendo {url}, señor."


def volumen_actual():
    return int(_applescript("output volume of (get volume settings)"))


def cambiar_volumen(nivel):
    nivel = max(0, min(100, int(nivel)))
    _applescript(f"set volume output volume {nivel}")
    return "Silencio, señor." if nivel == 0 else f"Volumen al {nivel} por ciento, señor."


def controlar_musica(accion):
    comandos = {"reproducir": ("play", "Reproduciendo música"), "pausar": ("pause", "Música en pausa"),
                "siguiente": ("next track", "Siguiente canción"), "anterior": ("previous track", "Canción anterior")}
    comando, frase = comandos[accion]
    _applescript(f'tell application "Music" to {comando}')
    return f"{frase}, señor."


def buscar_archivo(nombre):
    resultado = subprocess.run(["mdfind", "-name", nombre], capture_output=True, text=True, timeout=20)
    rutas = [r for r in resultado.stdout.splitlines() if "/Library/" not in r and "/." not in r][:3]
    if not rutas:
        return f"No encontré archivos llamados {nombre}, señor."
    subprocess.run(["open", "-R", rutas[0]])  # lo muestra en Finder
    nombres = ", ".join(os.path.basename(r) for r in rutas)
    return f"Encontré {len(rutas)}: {nombres}. Le muestro el primero en Finder, señor."


# ---------- Recordatorios y alarmas (app Recordatorios) ----------

def pendientes():
    """Lista [(id, nombre)] de recordatorios sin completar (ignora la lista de aviso "⚠️" de Apple)."""
    texto = _applescript('''
        tell application "Reminders"
            set salida to ""
            repeat with r in (reminders whose completed is false)
                set salida to salida & (id of r) & "|" & (name of container of r) & "|" & (name of r) & linefeed
            end repeat
            return salida
        end tell''')
    lista = []
    for linea in texto.splitlines():
        partes = linea.split("|", 2)
        if len(partes) == 3 and "⚠" not in partes[1]:
            lista.append((partes[0], partes[2]))
    return lista


def ver_recordatorios():
    nombres = [nombre for _, nombre in pendientes()]
    if not nombres:
        return "No tiene pendientes, señor."
    if len(nombres) == 1:
        return f"Tiene un pendiente, señor: {nombres[0]}."
    return f"Tiene {len(nombres)} pendientes, señor: " + "; ".join(nombres[:-1]) + f"; y {nombres[-1]}."


def borrar_recordatorios(ids):
    """Borra recordatorios por su id. (Las alarmas también son recordatorios.)"""
    _applescript('''
        on run argv
            tell application "Reminders"
                repeat with i in argv
                    delete (first reminder whose id is (i as text))
                end repeat
            end tell
        end run''', *ids)


def crear_recordatorio(texto, cuando=None, tiene_hora=True):
    """Crea un recordatorio. Si hay `cuando`, la Mac (y tu iPhone) avisarán a esa hora."""
    _applescript(FECHA_APPLESCRIPT + '''
        on run argv
            tell application "Reminders"
                set nuevo to make new reminder with properties {name:item 1 of argv}
                if (count of argv) > 1 then
                    set f to my armarFecha(item 2 of argv, item 3 of argv, item 4 of argv, item 5 of argv, item 6 of argv)
                    set due date of nuevo to f
                    set remind me date of nuevo to f
                end if
            end tell
        end run''', texto, *(_partes(cuando) if cuando else []))
    if cuando:
        return f"Listo, señor. Le recordaré {texto} {fechas.decir(cuando, tiene_hora)}."
    return f"Listo, señor. Agregué {texto} a sus pendientes."


def poner_alarma(cuando, motivo=""):
    """Alarma = recordatorio con aviso a esa hora (sonará como notificación en la Mac y el iPhone)."""
    crear_recordatorio(f"⏰ {motivo or 'Alarma'}", cuando)
    return f"Alarma puesta para {fechas.decir(cuando)}, señor."


# ---------- Notas (app Notas de Apple) ----------

def _html(texto):
    return html.escape(texto).replace("\n", "<br>")


def crear_nota(texto):
    _applescript('''
        on run argv
            tell application "Notes"
                make new note at (default folder of default account) with properties {body:item 1 of argv}
            end tell
        end run''', f"<div>{_html(texto)}</div>")
    return f"Anotado, señor: {texto}."


def _notas():
    """Lista [(nombre, segundos_desde_que_se_editó)] de la carpeta principal, la más reciente primero."""
    texto = _applescript('''
        tell application "Notes"
            set salida to ""
            set ahora to current date
            repeat with n in notes of (default folder of default account)
                set salida to salida & ((ahora - (modification date of n)) as integer) & "|" & (name of n) & linefeed
            end repeat
            return salida
        end tell''')
    notas = []
    for linea in texto.splitlines():
        edad, _, nombre = linea.partition("|")
        if nombre:
            notas.append((nombre.strip(), int(edad)))
    return sorted(notas, key=lambda n: n[1])


def ver_notas():
    notas = [n for n, _ in _notas()[:5]]
    if not notas:
        return "No tiene notas, señor."
    return f"Sus notas más recientes, señor: " + "; ".join(notas) + "."


def _buscar_nota(nombre):
    buscado = fechas.sin_acentos(nombre.lower())
    return next((n for n, _ in _notas() if buscado in fechas.sin_acentos(n.lower())), None)


def leer_nota(nombre):
    encontrada = _buscar_nota(nombre)
    if not encontrada:
        return f"No encontré una nota llamada {nombre}, señor."
    texto = _applescript('''
        on run argv
            tell application "Notes" to return plaintext of (first note of (default folder of default account) whose name is (item 1 of argv))
        end run''', encontrada)
    texto = " ".join(texto.split())
    if len(texto) > 400:
        texto = texto[:400].rsplit(" ", 1)[0] + "… La nota sigue, señor; es bastante larga."
    return f"Dice así, señor: {texto}"


def agregar_a_nota(nombre, texto):
    encontrada = _buscar_nota(nombre)
    if not encontrada:
        crear_nota(f"{nombre}\n{texto}")
        return f"No tenía una nota llamada {nombre}, así que la creé con: {texto}, señor."
    _applescript('''
        on run argv
            tell application "Notes"
                set n to first note of (default folder of default account) whose name is (item 1 of argv)
                set body of n to (body of n) & (item 2 of argv)
            end tell
        end run''', encontrada, f"<div>{_html(texto)}</div>")
    return f"Agregué {texto} a la nota {encontrada}, señor."


# ---------- Calendario ----------

def crear_evento(titulo, cuando, duracion_minutos=60):
    fin = cuando + fechas.dt.timedelta(minutes=duracion_minutos)
    _applescript(FECHA_APPLESCRIPT + '''
        on run argv
            set inicio to my armarFecha(item 2 of argv, item 3 of argv, item 4 of argv, item 5 of argv, item 6 of argv)
            set fin to my armarFecha(item 7 of argv, item 8 of argv, item 9 of argv, item 10 of argv, item 11 of argv)
            tell application "Calendar"
                tell calendar (item 12 of argv)
                    make new event with properties {summary:item 1 of argv, start date:inicio, end date:fin}
                end tell
            end tell
        end run''', titulo, *_partes(cuando), *_partes(fin), CALENDARIO)
    return f"Agendado, señor: {titulo}, {fechas.decir(cuando)}, en su calendario {CALENDARIO}."


def ver_agenda(dia):
    """Lee los eventos de todos tus calendarios para un día."""
    siguiente = dia + fechas.dt.timedelta(days=1)
    texto = _applescript(FECHA_APPLESCRIPT + '''
        on run argv
            set d1 to my armarFecha(item 1 of argv, item 2 of argv, item 3 of argv, 0, 0)
            set d2 to my armarFecha(item 4 of argv, item 5 of argv, item 6 of argv, 0, 0)
            set salida to ""
            tell application "Calendar"
                repeat with c in calendars
                    repeat with e in (every event of c whose start date ≥ d1 and start date < d2)
                        set s to start date of e
                        set salida to salida & (hours of s) & "|" & (minutes of s) & "|" & (allday event of e) & "|" & (summary of e) & linefeed
                    end repeat
                end repeat
            end tell
            return salida
        end run''', str(dia.year), str(dia.month), str(dia.day),
        str(siguiente.year), str(siguiente.month), str(siguiente.day))

    eventos = []
    for linea in texto.splitlines():
        partes = linea.split("|", 3)
        if len(partes) == 4:
            hora, minuto, todo_el_dia, titulo = partes
            eventos.append((int(hora), int(minuto), todo_el_dia == "true", titulo))
    cuando = fechas.decir(fechas.dt.datetime.combine(dia, fechas.dt.time()), tiene_hora=False)
    if not eventos:
        return f"No tiene nada en el calendario para {cuando}, señor."
    eventos.sort()
    descripcion = "; ".join(t if todo else f"a las {h}:{m:02d}, {t}" for h, m, todo, t in eventos)
    return f"Para {cuando} tiene: {descripcion}."


# ---------- Información en tiempo real ----------

CLIMA = {0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado",
         45: "con niebla", 48: "con niebla", 51: "con llovizna ligera", 53: "con llovizna", 55: "con llovizna fuerte",
         61: "con lluvia ligera", 63: "con lluvia", 65: "con lluvia fuerte", 80: "con chubascos", 81: "con chubascos",
         82: "con chubascos fuertes", 95: "con tormenta", 96: "con tormenta y granizo", 99: "con tormenta y granizo"}


def ver_clima(ciudad=""):
    ciudad = ciudad or CIUDAD_CASA
    lugar = httpx.get("https://geocoding-api.open-meteo.com/v1/search",
                      params={"name": ciudad, "count": 1, "language": "es"}, timeout=10).json()
    if not lugar.get("results"):
        return f"No encontré la ciudad {ciudad}, señor."
    lugar = lugar["results"][0]
    datos = httpx.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": lugar["latitude"], "longitude": lugar["longitude"], "timezone": "auto",
        "current": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": 1}, timeout=10).json()
    ahora, hoy = datos["current"], datos["daily"]
    lluvia = hoy["precipitation_probability_max"][0]
    consejo = " Le sugiero llevar paraguas." if lluvia >= 50 else ""
    return (f"En {lugar['name']} hay {round(ahora['temperature_2m'])} grados, "
            f"{CLIMA.get(ahora['weather_code'], 'con clima variable')}. Hoy la máxima será de "
            f"{round(hoy['temperature_2m_max'][0])} y la mínima de {round(hoy['temperature_2m_min'][0])}, "
            f"con {lluvia} por ciento de probabilidad de lluvia.{consejo}")


def ver_noticias(tema="México"):
    resultados = DDGS().news(tema or "México", region="mx-es", max_results=3)
    if not resultados:
        return f"No encontré noticias sobre {tema}, señor."
    titulares = ". ".join(r["title"].rstrip(".") for r in resultados)
    return f"Los titulares sobre {tema}, señor: {titulares}."


def buscar_en_internet(consulta):
    """Devuelve resultados crudos; el cerebro los resume en una respuesta corta."""
    resultados = DDGS().text(consulta, region="mx-es", max_results=4)
    return "\n".join(f"- {r['title']}: {r['body']}" for r in resultados) or "Sin resultados."
