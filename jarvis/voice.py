"""La voz de JARVIS.

Usa Piper (voz neuronal local, gratis y sin internet). Si el modelo no está, usa `say` de macOS.
Mientras dice una frase, ya va preparando la siguiente, y mide el volumen para que la
interfaz (HUD) se ilumine al ritmo de la voz.
"""

import os
import queue
import re
import subprocess
import threading
import time

import numpy as np
import sounddevice as sd

CARPETA = os.path.dirname(os.path.abspath(__file__))

# Voz neuronal elegida. Para cambiarla, descarga otra de https://huggingface.co/rhasspy/piper-voices
# (archivos .onnx y .onnx.json) a la carpeta voces/ y pon aquí su nombre.
VOZ_PIPER = os.path.join(CARPETA, "voces", "es_MX-ald-medium.onnx")
VELOCIDAD_PIPER = 0.8   # 1.0 = normal; 0.9 = más rápido; 1.1 = más lento
VOLUMEN = 0.85          # volumen máximo (0 a 1); más bajo evita que las bocinas distorsionen

# Voz de respaldo de macOS (si Piper no está disponible).
VOZ_MAC = "Reed (Español (México))"
VELOCIDAD_MAC = 190

FIN_DE_FRASE = re.compile(r"(?<=[.!?¡¿:;])\s+")
PASO_NIVEL = 0.05  # cada cuántos segundos se mide el volumen (20 veces por segundo)


def hora_hablada(m):
    """'17:00' → '5 de la tarde', '7:30' → '7 y media'."""
    hora, minutos = int(m.group(1)), int(m.group(2))
    if hora == 0:
        texto, parte = "12", "de la noche"
    elif hora < 12:
        texto, parte = str(hora), "de la mañana" if hora >= 6 else "de la madrugada"
    elif hora == 12:
        texto, parte = "12", "del día"
    else:
        texto, parte = str(hora - 12), "de la tarde" if hora < 20 else "de la noche"
    extra = {0: "", 15: " y cuarto", 30: " y media"}.get(minutos, f" y {minutos}")
    return f"{texto}{extra} {parte}"


def preparar(frase):
    """Limpia el texto para que se lea bien en voz alta."""
    frase = frase.replace("*", "").replace("⏰", "").replace("°C", " grados").replace("°", " grados")
    frase = re.sub(r"\b(\d{1,2}):(\d{2})\b", hora_hablada, frase)
    return frase.strip().lstrip("-–—•· ").strip()


class Voz:
    """Habla frase por frase mientras el cerebro todavía está escribiendo la respuesta.

    al_nivel(n):     se llama con el volumen de la voz (0 a 1) mientras habla.
    al_hablar(bool): se llama con True al empezar a hablar y False al terminar.
    """

    def __init__(self, al_nivel=None, al_hablar=None):
        self.al_nivel = al_nivel
        self.al_hablar = al_hablar
        self.pendiente = ""
        self.piper = self._cargar_piper()
        self.textos = queue.Queue()   # frases por convertir en audio
        self.audios = queue.Queue()   # audio listo para reproducir
        threading.Thread(target=self._sintetizar_en_fondo, daemon=True).start()
        threading.Thread(target=self._reproducir_en_fondo, daemon=True).start()

    def _cargar_piper(self):
        try:
            from piper import PiperVoice
            return PiperVoice.load(VOZ_PIPER)
        except Exception as error:
            print(f"(Voz neuronal no disponible, uso la de macOS: {error})")
            return None

    # ---------- Lo que usa el resto del programa ----------

    def agregar(self, trozo):
        """Recibe pedazos de texto; cuando completa una frase, la manda a decir."""
        self.pendiente += trozo
        partes = FIN_DE_FRASE.split(self.pendiente)
        for frase in partes[:-1]:
            self._decir(frase)
        self.pendiente = partes[-1]

    def terminar(self):
        """Dice lo que falte y espera a que JARVIS deje de hablar."""
        self._decir(self.pendiente)
        self.pendiente = ""
        self.textos.join()
        self.audios.join()

    def decir(self, texto):
        self._decir(texto)
        self.textos.join()
        self.audios.join()

    def _decir(self, frase):
        frase = preparar(frase)
        if frase:
            self.textos.put(frase)

    # ---------- Trabajo en segundo plano ----------

    def _sintetizar_en_fondo(self):
        """Convierte cada frase en audio (mientras la anterior todavía suena)."""
        from piper import SynthesisConfig
        config = SynthesisConfig(length_scale=VELOCIDAD_PIPER)
        while True:
            frase = self.textos.get()
            try:
                if self.piper:
                    pedazos = list(self.piper.synthesize(frase, syn_config=config))
                    audio = np.concatenate([p.audio_float_array for p in pedazos])
                    pico = float(np.max(np.abs(audio))) or 1.0
                    self.audios.put((audio * (VOLUMEN / pico), pedazos[0].sample_rate))
                else:
                    self.audios.put((frase, None))
            except Exception:
                self.audios.put((frase, None))
            finally:
                self.textos.task_done()

    def _reproducir_en_fondo(self):
        while True:
            audio, frecuencia = self.audios.get()
            try:
                if self.al_hablar:
                    self.al_hablar(True)
                if frecuencia is None:  # respaldo: voz de macOS
                    subprocess.run(["say", "-v", VOZ_MAC, "-r", str(VELOCIDAD_MAC), audio])
                else:
                    self._reproducir(audio, frecuencia)
            except Exception as error:
                print(f"(Error de audio: {error})")
            finally:
                self.audios.task_done()
                if self.textos.unfinished_tasks == 0 and self.audios.unfinished_tasks == 0:
                    if self.al_nivel:
                        self.al_nivel(0.0)
                    if self.al_hablar:
                        self.al_hablar(False)

    def _reproducir(self, audio, frecuencia):
        """Reproduce el audio y, si hay interfaz, reporta el volumen mientras suena."""
        sd.play(audio.astype(np.float32), frecuencia)
        if self.al_nivel:
            paso = int(frecuencia * PASO_NIVEL)
            inicio = time.time()
            for i in range(0, len(audio), paso):
                pedazo = audio[i:i + paso]
                self.al_nivel(min(1.0, float(np.sqrt(np.mean(pedazo ** 2))) * 3))
                time.sleep(max(0.0, inicio + (i + paso) / frecuencia - time.time()))
        sd.wait()
