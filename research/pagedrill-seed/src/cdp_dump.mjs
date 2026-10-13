// usage: node cdp_dump.mjs <port> <url> <outfile> [waitms]
import fs from 'fs';
const [port,url,out,wait='15000']=process.argv.slice(2);
const r=await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`,{method:'PUT'}); const t=await r.json();
await new Promise(s=>setTimeout(s,+wait));
const ws=new WebSocket(t.webSocketDebuggerUrl);
await new Promise(s=>ws.onopen=s);
ws.onmessage=(m)=>{const d=JSON.parse(m.data); if(d.id===1){fs.writeFileSync(out,d.result.result.value); ws.close(); fetch(`http://127.0.0.1:${port}/json/close/${t.id}`); console.log(out, d.result.result.value.length);}};
ws.send(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression:'document.documentElement.outerHTML'}}));
