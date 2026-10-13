#!/bin/bash
# usage: fetch_style.sh dir slug url   (curl; saves html + extracted txt)
d=$1; s=$2; u=$3
curl -sL --max-time 60 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36" -o $d/$s.html -w "$s %{http_code} %{size_download} %{url_effective}\n" "$u"
python3 - "$d" "$s" <<'P'
import re,html,sys
d,s=sys.argv[1:3]; t=open(f'{d}/{s}.html',errors='ignore').read()
for pat in [r'<article.*?</article>', r'<main.*?</main>']:
    m=re.search(pat,t,flags=re.S)
    if m: t=m.group(0); break
t=re.sub(r'<script.*?</script>|<style.*?</style>|<nav.*?</nav>','',t,flags=re.S)
t=re.sub(r'</(p|li|h\d|tr|div|td|th|blockquote)>','\n',t)
t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
open(f'{d}/{s}.txt','w').write(t)
P
