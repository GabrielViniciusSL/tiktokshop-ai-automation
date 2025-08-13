from pathlib import Path
import subprocess

FFMPEG = "ffmpeg"

def assemble_vertical(
    voice_wav: Path,
    srt_file: Path,
    out_mp4: Path,
    broll: Path,
    music: Path = None,
    duration: int = 35
):
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # audio filters
    af = [
      "[0:a]loudnorm=I=-16:TP=-1.5:LRA=11:print_format=summary,",
      "equalizer=f=6500:t=h:width=200:g=-6[a0]"  # de-ess simples
    ]
    if music:
        a_complex = "".join(af) + f";[1:a]volume=0.15[a1];[a0][a1]amix=inputs=2:duration=longest[aout]"
        inputs = ["-i", str(voice_wav), "-i", str(music)]
        map_audio = ["-map", "[aout]"]
    else:
        a_complex = "".join(af) + "[aout]"
        inputs = ["-i", str(voice_wav)]
        map_audio = ["-map", "[aout]"]

    vf = (
      "[2:v]scale=1080:1920:force_original_aspect_ratio=increase,"
      "crop=1080:1920,setsar=1,format=yuv420p[vf];"
    )

    cmd = [
      FFMPEG,
      *inputs,
      "-stream_loop", "-1", "-t", str(duration), "-i", str(broll),
      "-filter_complex", vf + a_complex,
      *map_audio, "-map", "[vf]",
      "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
      "-preset", "medium", "-crf", "19",
      "-c:a", "aac", "-b:a", "192k",
      "-movflags", "+faststart",
      str(out_mp4)
    ]

    # aplicar legendas (passo 2) — estilo independente
    cmd_sub = [
      FFMPEG, "-i", str(out_mp4),
      "-vf", f"subtitles='{str(srt_file).replace('\\','/')}':force_style="
             f"'FontName=Arial,FontSize=32,OutlineColour=&H40000000,BorderStyle=3,Outline=2,Shadow=0,MarginV=80'",
      "-c:v", "libx264", "-crf", "19", "-preset", "medium",
      "-c:a", "copy",
      str(out_mp4.with_name(out_mp4.stem + '_cc.mp4'))
    ]

    subprocess.run(cmd, check=True)
    subprocess.run(cmd_sub, check=True)
    return out_mp4.with_name(out_mp4.stem + '_cc.mp4')

