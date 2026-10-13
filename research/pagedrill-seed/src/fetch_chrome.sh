#!/bin/bash
# usage: fetch_chrome.sh dir slug url  (headless Chrome dump-dom, then text extraction)
d=$1; s=$2; u=$3
timeout 90 google-chrome --headless=new --no-sandbox --disable-gpu --user-data-dir=/tmp/chr-$s --virtual-time-budget=20000 --user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36" --dump-dom "$u" > $d/$s.html 2>/dev/null
python3 - "$d" "$s" <<'P'
import re,html,sys
d,s=sys.argv[1:3]; t=open(f'{d}/{s}.html',errors='ignore').read()
for pat in [r'<article.*?</article>', r'<main.*?</main>']:
    m=re.search(pat,t,flags=re.S)
    if m and len(m.group(0))>2000: t=m.group(0); break
t=re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>','',t,flags=re.S)
t=re.sub(r'</(p|li|h\d|tr|div|td|th|blockquote)>','\n',t)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(f'{d}/{s}.txt','w').write(t); print(s,len(t))
P
