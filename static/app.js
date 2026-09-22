const q=s=>document.querySelector(s);
let mode="inperson",recorder=null,chunks=[],streams=[],ctx=null,timer=null,start=0;
document.querySelectorAll(".mode").forEach(b=>b.onclick=()=>{if(recorder?.state==="recording")return;document.querySelectorAll(".mode").forEach(x=>x.classList.remove("active"));b.classList.add("active");mode=b.dataset.mode});
const fmt=ms=>{let s=Math.floor(ms/1000),h=Math.floor(s/3600),m=Math.floor((s%3600)/60);s%=60;return [h,m,s].map(x=>String(x).padStart(2,"0")).join(":")};
function stopTracks(){streams.forEach(s=>s.getTracks().forEach(t=>t.stop()));streams=[];if(ctx){ctx.close().catch(()=>{});ctx=null}}
async function stream(){
 const mic=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});streams.push(mic);
 ctx=new AudioContext();const dest=ctx.createMediaStreamDestination();ctx.createMediaStreamSource(mic).connect(dest);
 if(mode==="discord"){const d=await navigator.mediaDevices.getDisplayMedia({video:true,audio:true});streams.push(d);if(!d.getAudioTracks().length){stopTracks();throw Error("PC音声が共有されていません。システム音声共有をONにしてください。")}ctx.createMediaStreamSource(d).connect(dest)}
 return dest.stream
}
async function begin(){
 q("#result").classList.add("hidden");q("#progress").classList.add("hidden");
 const s=await stream(),mime="audio/webm;codecs=opus";recorder=MediaRecorder.isTypeSupported(mime)?new MediaRecorder(s,{mimeType:mime,audioBitsPerSecond:128000}):new MediaRecorder(s);chunks=[];
 recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
 recorder.onstop=async()=>{clearInterval(timer);stopTracks();await process(new Blob(chunks,{type:recorder.mimeType||"audio/webm"}))};
 recorder.start(1000);start=Date.now();timer=setInterval(()=>q("#timer").textContent=fmt(Date.now()-start),250);
 q("#status").textContent="RECORDING";q("#dot").classList.add("on");q("#recordButton").textContent="録音終了";
}
function end(){q("#recordButton").disabled=true;q("#status").textContent="FINISHING";recorder.stop()}
async function process(blob){
 q("#dot").classList.remove("on");q("#status").textContent="PROCESSING";q("#progress").classList.remove("hidden");
 const fd=new FormData();fd.append("audio",blob,"meeting.webm");
 try{const r=await fetch("/api/process",{method:"POST",body:fd}),d=await r.json();if(!r.ok||!d.ok)throw Error(d.error||"処理失敗");
 q("#result").textContent="Gmail送信完了\n処理デバイス: "+d.device+"\n\n"+d.preview;q("#result").classList.remove("hidden");q("#status").textContent="DONE"}
 catch(e){q("#result").textContent=e.message;q("#result").classList.remove("hidden");q("#status").textContent="ERROR"}
 finally{q("#progress").classList.add("hidden");q("#recordButton").disabled=false;q("#recordButton").textContent="録音開始";q("#timer").textContent="00:00:00";recorder=null}
}
q("#recordButton").onclick=async()=>{try{recorder?.state==="recording"?end():await begin()}catch(e){stopTracks();q("#result").textContent=e.message;q("#result").classList.remove("hidden");q("#status").textContent="ERROR"}};
async function load(){const d=await (await fetch("/api/settings")).json();q("#recipientEmail").value=d.recipient_email||"";q("#senderEmail").value=d.sender_email||"";q("#minSpeakers").value=d.min_speakers||"";q("#maxSpeakers").value=d.max_speakers||"";q("#hotwords").value=d.hotwords||"";q("#gmailState").textContent=d.has_gmail_app_password?"✓ 保存済み":"未設定";q("#hfState").textContent=d.has_hf_token?"✓ 保存済み":"未設定"}
q("#settingsButton").onclick=async()=>{await load();q("#settingsDialog").showModal()};q("#closeSettings").onclick=()=>q("#settingsDialog").close();
q("#settingsForm").onsubmit=async e=>{e.preventDefault();const payload={recipient_email:q("#recipientEmail").value,sender_email:q("#senderEmail").value,gmail_app_password:q("#gmailPassword").value,hf_token:q("#hfToken").value,min_speakers:q("#minSpeakers").value,max_speakers:q("#maxSpeakers").value,hotwords:q("#hotwords").value};const r=await fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});q("#settingsMessage").textContent=r.ok?"保存しました":"保存失敗";if(r.ok){q("#gmailPassword").value="";q("#hfToken").value="";await load()}};
