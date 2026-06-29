import urllib.request, ssl, re

ctx = ssl._create_unverified_context()
base = 'http://10.10.0.102'

req = urllib.request.Request(base + '/static/js/app.js')
resp = urllib.request.urlopen(req, context=ctx, timeout=10)
js = resp.read().decode('utf-8', errors='replace')

# Get chunks file references
chunks = re.findall(r'static/js/chunk-[a-f0-9]+\.js', js)
chunks = list(set(chunks))[:10]
print('Chunks found:', chunks)

# Look for any URL patterns with http:// or https://
for m in re.finditer(r'https?://[^"\' ]+', js):
    print('URL:', m.group()[:100])

# Look for references to 8000 or port
for m in re.finditer(r'[^.]{0,30}8000[^.]{0,30}', js):
    ref = m.group().strip()[:100]
    # Filter out noise
    if any(c.isalpha() for c in ref):
        print(f'Port ref: {ref}')
