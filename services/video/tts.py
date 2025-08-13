from pathlib import Path
import subprocess, sys

class TTSProvider:
    def synth(self, text: str, out_wav: Path, voice: str = "female_en") -> Path:
        raise NotImplementedError

class LocalMockTTS(TTSProvider):
    """Mock offline p/ dev. Trocar por XTTS/ElevenLabs na produção."""
    def __init__(self):
        import pyttsx3
        self.engine = pyttsx3.init()
        # tente ajustar voz/velocidade se quiser
        # for v in self.engine.getProperty("voices"): print(v.id)
        self.engine.setProperty("rate", 190)

    def synth(self, text: str, out_wav: Path, voice: str = "female_en") -> Path:
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        self.engine.save_to_file(text, str(out_wav))
        self.engine.runAndWait()
        return out_wav

def ensure_ffmpeg():
    try:
        subprocess.run(["ffmpeg","-version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        sys.exit("FFmpeg não encontrado no PATH. Instale e tente de novo.")
