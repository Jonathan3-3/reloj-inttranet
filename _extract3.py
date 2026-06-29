import urllib.request, ssl, re

ctx = ssl._create_unverified_context()
base = 'http://10.10.0.102'

req = urllib.request.Request(base + '/static/js/app.js')
resp = urllib.request.urlopen(req, context=ctx, timeout=10)
js = resp.read().decode('utf-8', errors='replace')

# Look for patterns around API calls
# Find strings near 'fetch', 'axios', 'POST', 'GET' in the minified code
for m in re.finditer(r'[\w$]+\([\"\'][\w/]+[\"\']\)', js):
    match = m.group()
    # If it looks like an API call
    print(match[:100])

print('---')

# Find all paths with /api/ or /iclock/
for m in re.finditer(r'["\'](/[\w/]+(?:api|iclock)[\w/]*)["\']', js):
    print(m.group(1)[:100])

print('---')

# Find paths that don't have common file extensions
for m in re.finditer(r'["\'](/[\w/-]{5,40})["\']', js):
    path = m.group(1)
    if not any(path.endswith(ext) for ext in ['.js','.css','.png','.jpg','.gif','.svg','.ico','.woff','.ttf','.eot','.html']):
        if not path.startswith('/static/') and '//' not in path:
            print(path)
