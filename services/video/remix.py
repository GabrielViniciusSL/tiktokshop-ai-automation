from pathlib import Path
import re, subprocess
from yt_dlp import YoutubeDL
from services.video.generate import generate_video
from services.video.autoscript import build_auto_script

def sanitize_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\-_.]", "_", s)

def download_tiktok(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    template = str(out_dir / "%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": template,
        "format": "mp4/bestvideo+bestaudio/best",
        "quiet": True,
        "noprogress": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = Path(out_dir / f"{info['id']}.{info.get('ext','mp4')}")
    return filepath

def mute_audio(src: Path, dst: Path):
    cmd = ["ffmpeg","-y","-i",str(src),"-an","-c:v","copy",str(dst)]
    subprocess.run(cmd, check=True)

def remix_from_tiktok(
    url: str,
    sku: str,
    out_root: Path,
    script_text: str | None = None,
    autoscript_params: dict | None = None
) -> Path:
    """Baixa um TikTok, silencia o áudio original e gera uma nova versão com TTS/legendas."""
    dl_dir = out_root / "download"
    broll = download_tiktok(url, dl_dir)
    muted = out_root / "broll_muted.mp4"
    mute_audio(broll, muted)

    if script_text is None:
        p = autoscript_params or {}
        script_text = build_auto_script(
            product_sku=sku,
            product_name=p.get("product_name", sku),
            niche=p.get("niche","geral"),
            scenario=p.get("scenario","casa"),
            style=p.get("style","demonstração rápida"),
            seconds=p.get("seconds",35),
        )

    final = generate_video(
        product_name=sku,
        script_text=script_text,
        out_dir=out_root,
        broll_path=muted,
        duration=None  # usa a duração do vídeo baixado (cap 45s)
    )
    return final
