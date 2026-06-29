import urllib.request, ssl, re

ctx = ssl._create_unverified_context()
base = 'http://10.10.0.102'

req = urllib.request.Request(base + '/static/js/app.js')
resp = urllib.request.urlopen(req, context=ctx, timeout=10)
js = resp.read().decode('utf-8', errors='replace')

# Save the JS for analysis
with open('_app.js.txt', 'w', encoding='utf-8') as f:
    f.write(js)

# Extract all string literals more carefully
# Look for paths between quotes
paths = re.findall(r"['\"](/[a-zA-Z0-9_/.-]+)['\"]", js)
unique = sorted(set(p for p in paths if len(p) > 4))

with open('_paths.txt', 'w', encoding='utf-8') as f:
    for p in unique:
        # Filter out obvious non-API paths
        if not any(ext in p for ext in ['.js','.css','.png','.jpg','.gif','.svg','.ico','.woff','.ttf','.eot']):
            if '/static/' not in p and '//' not in p:
                f.write(p + '\n')

print(f"Found {len(unique)} paths, wrote to _paths.txt")
print("JS saved to _app.js.txt (" + str(len(js)) + " chars)")
