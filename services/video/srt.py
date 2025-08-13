from pathlib import Path

def ms_to_ts(ms: int) -> str:
    h = ms//3600000; m=(ms%3600000)//60000; s=(ms%60000)//1000; ms2=ms%1000
    return f"{h:02}:{m:02}:{s:02},{ms2:03}"

def build_srt(text: str, out_path: Path, wpm: int = 170):
    words = text.split()
    total_sec = max(3, int(len(words)/wpm*60))
    chunks = []
    i=0
    while i < len(words):
        chunk = " ".join(words[i:i+8])
        chunks.append(chunk)
        i += 8
    seg = max(0.6, total_sec / max(1,len(chunks)))
    cur = 0.0
    lines=[]
    for idx, ch in enumerate(chunks, start=1):
        start = int(cur*1000); end = int((cur+seg)*1000)
        lines.append(f"{idx}\n{ms_to_ts(start)} --> {ms_to_ts(end)}\n{ch}\n")
        cur += seg
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path

