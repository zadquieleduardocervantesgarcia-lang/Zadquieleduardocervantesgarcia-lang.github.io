# JARVIS — asistente de voz local para tu Mac

Todo corre en tu computadora (gratis y privado) usando **Ollama** con el modelo `qwen2.5:3b`.

## Progreso
- [x] Fase 1 — Chat por texto con personalidad JARVIS
- [x] Fase 2 — Voz (oír y hablar)
- [x] Fase 3 — Herramientas (controlar la Mac, clima, web, recordatorios)
- [x] Fase 4 — Interfaz HUD estilo Iron Man (red de nodos en Chrome)
- [ ] Fase 5 — Mejoras (palabra "Jarvis", voz realista, memoria)

## Instalación (solo la primera vez)

Abre la app **Terminal** y corre estos comandos uno por uno.

**1. Instalar Homebrew** (el instalador de programas para Mac; te pedirá tu contraseña):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Al terminar, Homebrew muestra 2 comandos bajo "Next steps" para agregarlo a tu PATH. Cópialos y córrelos.

**2. Instalar Python moderno, Ollama y la librería de audio:**
```bash
brew install python@3.12 ollama portaudio
```

**3. Encender Ollama y descargar el cerebro (~2 GB):**
```bash
brew services start ollama
ollama pull qwen2.5:3b
```

**4. Preparar el proyecto:**
```bash
cd ~/Desktop/"Cloud code"/jarvis
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usar JARVIS
```bash
cd ~/Desktop/"Cloud code"/jarvis
source .venv/bin/activate
python main.py
```
O haz doble clic en `jarvis.command`.

### Interfaz en Chrome (HUD)
Doble clic en **`JARVIS HUD.command`** (o `python main.py --web`). Se abre Chrome en http://localhost:8777
con una red de nodos que se ilumina con la voz de JARVIS y con la tuya.
- Botón del micrófono o **barra espaciadora** para hablar; o escribe en la caja.
- Colores: cian en espera/hablando, blanco-cian escuchando, ámbar pensando.
- Para apagarlo: Ctrl+C en la Terminal que se abrió.

- **Modo voz** (por defecto): presiona Enter, habla, y JARVIS te contesta en voz alta. Di "adiós" para salir.
- **Modo texto**: `python main.py --texto`. Escribe `salir` para terminar u `olvida` para borrar la memoria.

La primera vez macOS pedirá permiso para usar el **micrófono**: acéptalo.

## Qué le puedes pedir
| Di algo como… | Qué hace |
|---|---|
| "Iniciemos modo de trabajo" | Rutina: Highway to Hell en Spotify + cranesa.com.mx en Chrome |
| "Recuérdame comprar leche mañana a las 7" | Crea un recordatorio con aviso (Recordatorios de Apple) |
| "Crea un recordatorio" → "¿Qué desea que le recuerde?" | Si falta un dato, JARVIS lo pregunta |
| "¿Qué pendientes tengo?" | Lee tus Recordatorios |
| "Borra las alarmas" / "Elimina el recordatorio de comprar leche" / "Borra todos los recordatorios" | Borra (siempre pide confirmación: "sí" / "no") |
| "Pon una alarma a las 6 de la mañana" / "Despiértame mañana a las 7:30" | Alarma (notificación en Mac e iPhone) |
| "Agenda junta con Pedro el viernes a las 5 de la tarde" | Crea un evento en tu Calendario |
| "¿Qué tengo mañana?" / "¿Qué citas tengo el lunes?" | Lee tu Calendario |
| "Toma nota: comprar cable HDMI" / "Crea una nota que diga…" / "Anota" | Crea una nota en la app Notas (iCloud) |
| "Agrega leche a la nota lista del súper" | Agrega texto a una nota (si no existe, la crea) |
| "Lee la nota lista del súper" / "¿Qué notas tengo?" | Lee una nota / tus 5 notas más recientes |
| "¿Qué clima hace?" / "¿Y en Monterrey?" | Clima real |
| "Dame las noticias de deportes" | Titulares recientes |
| "Busca quién ganó el partido del América" | Busca en internet y lo resume |
| "Abre la calculadora" / "Abre Chrome" | Abre apps (entiende nombres en español) |
| "Sube el volumen" / "Volumen a 30" / "Silencio" | Volumen de la Mac |
| "Pon música" / "Pausa" / "Siguiente canción" | Controla la app Música |
| "Busca el archivo presupuesto" | Busca un archivo y lo muestra en Finder |

Fechas que entiende: "hoy", "mañana", "pasado mañana", "el viernes", "el 15", "el 10 de octubre",
"a las 5 de la tarde", "a las 8 y media", "al mediodía", "en 20 minutos". Di "cancela" para cancelar una pregunta.

La primera vez que uses Recordatorios, Calendario o Música, macOS pedirá permiso: acéptalo.
Tu ciudad para el clima (`CIUDAD_CASA`) y el calendario para eventos nuevos (`CALENDARIO`) están en `tools.py`.

## Archivos
- `main.py` — el programa que ejecutas; maneja la conversación.
- `ears.py` — el "oído": graba el micrófono y lo convierte en texto (Whisper). Si no te oye bien, baja `UMBRAL_VOZ`; si hay ruido, súbelo.
- `voice.py` — la "voz": voz neuronal Piper `es_MX-ald` (carpeta `voces/`). Ajusta `VELOCIDAD_PIPER` o `VOLUMEN`; si falta el modelo usa la voz de macOS.
- `rutinas.py` — rutinas de varias acciones ("modo de trabajo"). Copia un bloque para crear la tuya.
- `fechas.py` — entiende fechas y horas en español ("mañana a las 7").
- `comandos.py` — reconoce las órdenes ("abre…", "clima", "recuérdame…") y elige la herramienta. Agrega reglas aquí para enseñarle frases nuevas.
- `tools.py` — las "manos": cada función es una acción (abrir apps, clima, recordatorios…).
- `web.py` + `hud/index.html` — la interfaz en Chrome (servidor local y la animación de nodos).
- `brain.py` — el "cerebro": personalidad de JARVIS y conexión con Ollama. Cambia `PERSONALIDAD` para darle otro carácter.
