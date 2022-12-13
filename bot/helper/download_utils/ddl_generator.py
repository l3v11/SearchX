import base64
import re
import requests

from urllib.parse import urlparse, parse_qs

from bot import GDTOT_CRYPT
from bot.helper.ext_utils.exceptions import DDLExceptionHandler

def gdtot(url: str) -> str:
    if GDTOT_CRYPT is None:
        raise DDLExceptionHandler("GDTOT_CRYPT env var not provided")
    client = requests.Session()
    client.cookies.update({'crypt': GDTOT_CRYPT})
    res = client.get(url)
    dom = re.findall(r'https?://(.+)\.gdtot\.(.+)\/\S+\/\S+', url)[0]
    res = client.get(f"https://{dom[0]}.gdtot.{dom[1]}/dld?id={url.split('/')[-1]}")
    url = re.findall(r'URL=(.*?)"', res.text)[0]
    info = {}
    info['error'] = False
    params = parse_qs(urlparse(url).query)
    if 'gd' not in params or not params['gd'] or params['gd'][0] == 'false':
        info['error'] = True
        if 'msgx' in params:
            info['message'] = params['msgx'][0]
        else:
            info['message'] = 'Invalid link'
    else:
        decoded_id = base64.b64decode(str(params['gd'][0])).decode('utf-8')
        drive_link = f'https://drive.google.com/open?id={decoded_id}'
        info['gdrive_link'] = drive_link
    if not info['error']:
        return info['gdrive_link']
    else:
        raise DDLExceptionHandler(f"{info['message']}")
