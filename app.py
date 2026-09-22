from __future__ import annotations
import json, shutil, smtplib, subprocess, threading, time, uuid, webbrowser
from pathlib import Path
from email.message import EmailMessage
import keyring
from flask import Flask, jsonify, render_template, request

BASE=Path(__file__).resolve().parent
DATA=BASE/"data"; REC=BASE/"recordings"; SETTINGS=DATA/"settings.json"
DATA.mkdir(exist_ok=True); REC.mkdir(exist_ok=True)
SERVICE="OIF Meeting"
DEFAULT={
 "recipient_email":"","sender_email":"","model":"large-v3","language":"ja",
 "min_speakers":"","max_speakers":"",
 "hotwords":"OIF, Noema, ChatGPT, OpenAI, GitHub, Git, API, RAG, LLM, Python, JavaScript, TypeScript, React, Next.js, Notion, Discord"
}
app=Flask(__name__)

def load_settings():
    s=DEFAULT.copy()
    if SETTINGS.exists():
        try: s.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception: pass
    return s

def save_settings(s):
    SETTINGS.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")

def sec(k): return keyring.get_password(SERVICE,k) or ""
def setsec(k,v):
    if v and v.strip(): keyring.set_password(SERVICE,k,v.strip())

def device():
    try:
        import torch
        if torch.cuda.is_available(): return "cuda","float16","4"
    except Exception: pass
    return "cpu","int8","1"

def ts(x):
    n=max(0,int(float(x or 0))); h,r=divmod(n,3600); m,s=divmod(r,60)
    return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"

def transcript_from_json(p):
    data=json.loads(p.read_text(encoding="utf-8")); out=[]; last=None
    for seg in data.get("segments",[]):
        text=str(seg.get("text","")).strip()
        if not text: continue
        speaker=seg.get("speaker") or "SPEAKER_UNKNOWN"
        if out and last==speaker:
            out[-1][2]+=" "+text
        else:
            out.append([ts(seg.get("start")),speaker,text]); last=speaker
    return "\n\n".join(f"[{a}] {b}: {c}" for a,b,c in out)

def run_whisperx(audio,job,s):
    exe=shutil.which("whisperx")
    if not exe: raise RuntimeError("WhisperXが見つかりません。pip install whisperx を実行してください。")
    hf=sec("hf_token")
    if not hf: raise RuntimeError("Hugging Face tokenが未設定です。")
    dev,ctype,batch=device()
    cmd=[exe,str(audio),"--model",s.get("model") or "large-v3","--language","ja","--diarize",
         "--hf_token",hf,"--output_format","json","--output_dir",str(job),
         "--device",dev,"--compute_type",ctype,"--batch_size",batch,
         "--beam_size","5","--condition_on_previous_text","False","--verbose","False"]
    if s.get("hotwords","").strip(): cmd += ["--hotwords",s["hotwords"].strip()]
    if s.get("min_speakers","").strip(): cmd += ["--min_speakers",s["min_speakers"].strip()]
    if s.get("max_speakers","").strip(): cmd += ["--max_speakers",s["max_speakers"].strip()]
    r=subprocess.run(cmd,cwd=BASE,capture_output=True,text=True,encoding="utf-8",errors="replace")
    if r.returncode!=0: raise RuntimeError((r.stderr or r.stdout or "WhisperX失敗")[-4000:])
    js=sorted(job.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
    if not js: raise RuntimeError("WhisperXのJSON出力が見つかりません。")
    return js[0],dev

def send_mail(text,path,s):
    sender=s.get("sender_email","").strip(); to=s.get("recipient_email","").strip(); pw=sec("gmail_app_password")
    if not sender or not to: raise RuntimeError("送信元/送信先Gmailが未設定です。")
    if not pw: raise RuntimeError("Gmailアプリパスワードが未設定です。")
    msg=EmailMessage(); msg["From"]=sender; msg["To"]=to; msg["Subject"]="[OIF_TRANSCRIPT_READY] 会議文字起こし"
    msg.set_content("OIF Meeting の文字起こしです。\n\n"+text)
    msg.add_attachment(path.read_bytes(),maintype="text",subtype="plain",filename=path.name)
    with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as smtp:
        smtp.login(sender,pw); smtp.send_message(msg)

@app.get("/")
def index(): return render_template("index.html")

@app.get("/api/settings")
def get_settings():
    s=load_settings(); s["has_gmail_app_password"]=bool(sec("gmail_app_password")); s["has_hf_token"]=bool(sec("hf_token"))
    return jsonify(s)

@app.post("/api/settings")
def post_settings():
    p=request.get_json(force=True) or {}; s=load_settings()
    for k in DEFAULT:
        if k in p: s[k]=str(p[k]).strip()
    save_settings(s); setsec("gmail_app_password",str(p.get("gmail_app_password",""))); setsec("hf_token",str(p.get("hf_token","")))
    return jsonify(ok=True)

@app.post("/api/process")
def process():
    if "audio" not in request.files: return jsonify(ok=False,error="音声がありません"),400
    s=load_settings(); job=REC/uuid.uuid4().hex[:12]; job.mkdir()
    f=request.files["audio"]; suffix=Path(f.filename or "meeting.webm").suffix or ".webm"; audio=job/("meeting"+suffix); f.save(audio)
    try:
        jp,dev=run_whisperx(audio,job,s); text=transcript_from_json(jp)
        if not text: raise RuntimeError("文字起こし結果が空でした。")
        tp=job/"transcript.txt"; tp.write_text(text,encoding="utf-8"); send_mail(text,tp,s)
        return jsonify(ok=True,device=dev,preview=text[:1200])
    except Exception as e:
        return jsonify(ok=False,error=str(e)),500

def open_browser():
    time.sleep(1); webbrowser.open("http://127.0.0.1:8765")

if __name__=="__main__":
    threading.Thread(target=open_browser,daemon=True).start()
    app.run("127.0.0.1",8765,debug=False,threaded=True)
