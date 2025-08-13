from pathlib import Path
import subprocess, json
from services.video.tts import LocalMockTTS, ensure_ffmpeg
from services.video.srt import build_srt
from services.video.assemble import assemble_vertical

def _ffprobe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path)
    ]
    out = subprocess.check_output(cmd)
    data = json.loads(out)
    return float(data["format"]["duration"])

def generate_video(
    product_name: str,
    script_text: str,
    out_dir: Path,
    broll_path: Path | None = None,
    duration: int | None = 35
) -> Path:
    """Gera vídeo vertical com TTS + legendas. Se broll_path for passado, usa-o como plano de fundo."""
    ensure_ffmpeg()
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_wav = out_dir / "voice.wav"
    srt_file  = out_dir / "captions.srt"
    broll     = broll_path or Path("assets/broll/default.mp4")
    music     = Path("assets/music/bed.mp3")
    out_mp4   = out_dir / "output.mp4"

    # dur ação: se veio b-roll custom e não definiram duração, usa a duração dele (cap em 45s)
    if duration is None and broll.exists():
        dur = min(int(_ffprobe_duration(broll)), 45)
    else:
        dur = duration or 35

    # 1) TTS
    tts = LocalMockTTS()
    tts.synth(script_text, voice_wav, voice="female_en")

    # 2) SRT
    build_srt(script_text, srt_file, wpm=170)

    # 3) Montagem
    final = assemble_vertical(voice_wav, srt_file, out_mp4, broll=broll, music=music, duration=dur)
    return final


