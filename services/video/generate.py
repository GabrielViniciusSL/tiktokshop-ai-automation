from pathlib import Path
from services.video.tts import LocalMockTTS, ensure_ffmpeg
from services.video.srt import build_srt
from services.video.assemble import assemble_vertical

def generate_video(product_name: str, script_text: str, out_dir: Path) -> Path:
    ensure_ffmpeg()
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_wav = out_dir / "voice.wav"
    srt_file  = out_dir / "captions.srt"
    broll     = Path("assets/broll/default.mp4")
    music     = Path("assets/music/bed.mp3")
    out_mp4   = out_dir / "output.mp4"

    # 1) TTS
    tts = LocalMockTTS()
    tts.synth(script_text, voice_wav, voice="female_en")

    # 2) SRT
    build_srt(script_text, srt_file, wpm=170)

    # 3) Montagem
    final = assemble_vertical(voice_wav, srt_file, out_mp4, broll=broll, music=music, duration=35)
    return final

