import urllib.request, ssl, re, json

ctx = ssl._create_unverified_context()
base = 'http://10.10.0.102'

req = urllib.request.Request(base + '/static/js/app.js')
resp = urllib.request.urlopen(req, context=ctx, timeout=10)
js = resp.read().decode('utf-8', errors='replace')

# Find all string literals that look like API paths
paths = re.findall(r'["\x27](/\w[\w/]*)["\x27]', js)
unique = sorted(set(p for p in paths if len(p) > 3 and not any(ext in p for ext in ['.js','.css','.png','.jpg','.gif','.html','.svg','.ico','.woff','.ttf','.eot','app/','static/','http','www.'])))
for p in unique:
    print(p)
