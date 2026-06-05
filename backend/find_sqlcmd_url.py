import re
import requests

urls = [
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility?view=sql-server-ver17',
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility?view=sql-server-ver16',
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-utility?view=sql-server-ver15',
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-download-install?view=sql-server-ver17',
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-download-install?view=sql-server-ver16',
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-download-install?view=sql-server-ver15',
    'https://learn.microsoft.com/en-us/sql/tools/sqlcmd/sqlcmd-download-install?view=sql-server-ver17&view=sql-server-ver17',
]

for url in urls:
    print('URL:', url)
    r = requests.get(url, timeout=20)
    print('Status:', r.status_code)
    for pattern in [r'href=["\']([^"\']*\.msi[^"\']*)["\']', r'href=["\']([^"\']*download[^"]*)["\']', r'\b(?:https?://[^"\']*sqlcmd[^"\']*)\b', r'\b(?:https?://[^"\']*mssql-tools[^"\']*)\b']:
        matches = re.findall(pattern, r.text, re.IGNORECASE)
        if matches:
            print('Pattern:', pattern)
            for m in matches[:10]:
                print('  ', m)
    if not any(re.findall(p, r.text, re.IGNORECASE) for p in [r'href=["\']([^"\']*\.msi[^"\']*)["\']', r'href=["\']([^"\']*download[^"]*)["\']', r'\b(?:https?://[^"\']*sqlcmd[^"\']*)\b', r'\b(?:https?://[^"\']*mssql-tools[^"\']*)\b']):
        print('No relevant links found.')
    print('---')
