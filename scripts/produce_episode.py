#!/usr/bin/env python
"""
人间清醒录 V1.0 单集生产脚本
用法:
  python produce_episode.py --sentences-file sentences.txt --keyword "奥德赛时期" --out radio_ep02.mp4

sentences.txt 每一行一句完整中文旁白（以句号/问号/感叹号结尾）。
"""
import argparse, base64, json, os, re, subprocess, sys, uuid, requests

# ===== 固定配置（V1.0 冻结）=====
APPID = "9696473772"
TOKEN = "aBnR07Ikq7CafO53FkzTIEHCslajs0gi"
VOICE = "zh_female_wanwanxiaohe_moon_bigtts"
SPEED = 1.0
CLUSTER = "volcano_tts"

PROJECT = r"C:\Users\Administrator\Doubao\chats\2026-09-20\new-chat\radio-template"
MAIN_TSX = os.path.join(PROJECT, "src", "Audiogram", "Main.tsx")
PUBLIC_DIR = os.path.join(PROJECT, "public")
OUT_DIR = os.path.join(PROJECT, "out")

def tts(text):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer;{TOKEN}"}
    body = {
        "app": {"appid": APPID, "token": TOKEN, "cluster": CLUSTER},
        "user": {"uid": "renjianqingxinglu"},
        "audio": {"voice_type": VOICE, "encoding": "mp3", "speed_ratio": SPEED, "rate": 48000},
        "request": {"reqid": str(uuid.uuid4()), "text": text, "operation": "query", "with_timestamp": True},
    }
    r = requests.post("https://openspeech.bytedance.com/api/v1/tts", headers=headers, data=json.dumps(body), timeout=120)
    data = r.json()
    if data.get("code") != 3000:
        raise RuntimeError(f"TTS API error: {data}")
    return data

def ffprobe_duration_ms(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        text=True
    ).strip()
    return int(float(out) * 1000)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentences-file", required=True)
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.sentences_file, encoding="utf-8") as f:
        sentences = [line.strip() for line in f if line.strip()]
    full_text = "".join(sentences)
    print(f"[1/8] 句子数={len(sentences)}, 字数={len(full_text)}")

    # TTS
    data = tts(full_text)
    mp3_path = os.path.join(PUBLIC_DIR, "_ep.mp3")
    with open(mp3_path, "wb") as f:
        f.write(base64.b64decode(data["data"]))
    audio_dur_ms = ffprobe_duration_ms(mp3_path)
    print(f"[2/8] TTS done, audio duration = {audio_dur_ms}ms")

    # WAV for Remotion
    wav_path = os.path.join(PUBLIC_DIR, "test_audio_raw.wav")
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "48000", "-c:a", "pcm_s24le", "-ac", "2", wav_path],
                   check=True, capture_output=True)
    print(f"[3/8] WAV converted")

    # Parse words
    fe = json.loads(data["addition"]["frontend"])
    words = fe["words"]
    word_text = "".join(w["word"] for w in words)
    if word_text != full_text:
        raise RuntimeError(f"[QC] words text mismatch: tts_len={len(word_text)} original={len(full_text)}")
    print(f"[4/8] words matched: {len(words)} tokens, text identical")

    # Build captions
    captions = []
    wi = 0
    for si, sent in enumerate(sentences):
        start_wi = wi
        consumed = 0
        while consumed < len(sent) and wi < len(words):
            consumed += len(words[wi]["word"])
            wi += 1
        start_ms = words[start_wi]["start_time"]
        end_ms = None
        captions.append({"text": sent, "startMs": start_ms, "endMs": end_ms})
    # endMs for non-last
    for i in range(len(captions) - 1):
        next_start = captions[i + 1]["startMs"]
        end_ms = next_start - 80
        if end_ms <= captions[i]["startMs"]:
            end_ms = next_start
        captions[i]["endMs"] = end_ms
    captions[-1]["endMs"] = audio_dur_ms

    # QC
    for i, c in enumerate(captions):
        assert c["endMs"] > c["startMs"], f"[{i}] end<=start"
        if i > 0:
            assert c["startMs"] >= captions[i-1]["endMs"] - 50, f"[{i}] overlap with prev"
        assert c["endMs"] <= audio_dur_ms + 100, f"[{i}] exceeds audio"
    print(f"[5/8] QC passed ({len(captions)} sentences)")

    # Write captions.json
    cap_path = os.path.join(PUBLIC_DIR, "captions.json")
    with open(cap_path, "w", encoding="utf-8") as f:
        json.dump(captions, f, ensure_ascii=False, indent=2)

    # Update keyword in Main.tsx
    with open(MAIN_TSX, encoding="utf-8") as f:
        tsx = f.read()
    # Replace the big keyword text (inside the golden div)
    tsx = re.sub(r'(fontWeight: 900, color: GOLD[^>]*>)[^<]+<', rf'\1{args.keyword}<', tsx)
    with open(MAIN_TSX, "w", encoding="utf-8") as f:
        f.write(tsx)
    print(f"[6/8] Keyword set to: {args.keyword}")

    # Render
    out_path = os.path.join(OUT_DIR, args.out)
    print(f"[7/8] Rendering...")
    res = subprocess.run(
        ["npx", "remotion", "render", "Audiogram", out_path, "--codec", "h264"],
        cwd=PROJECT, capture_output=True, text=True, shell=True
    )
    if res.returncode != 0:
        print(res.stdout[-2000:])
        print(res.stderr[-2000:])
        raise RuntimeError("Remotion render failed")
    print(f"[8/8] Done: {out_path}")

    # Final QC
    vdur = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", out_path],
        text=True
    ).strip()
    print(f"Final video stream: {vdur}")

if __name__ == "__main__":
    main()
