import re
import requests

from bs4 import BeautifulSoup

from bot import PHPSESSID, CRYPT
from bot.helper.ext_utils.exceptions import GDToTException
from bot.helper.telegram_helper.bot_commands import BotCommands

if CRYPT is not None:
    cookies = {"PHPSESSID": PHPSESSID, "crypt": CRYPT}

def gdtot(url: str) -> str:
    if CRYPT is None:
        raise GDToTException("PHPSESSID and CRYPT env variables are missing")

    headers = {'upgrade-insecure-requests': '1',
               'save-data': 'on',
               'user-agent': 'Mozilla/5.0 (Linux; Android 10; Redmi 8A Dual) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Mobile Safari/537.36',
               'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'sec-fetch-site': 'same-origin',
               'sec-fetch-mode': 'navigate',
               'sec-fetch-dest': 'document',
               'referer': '',
               'prefetchAd_3621940': 'true',
               'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7'}

    r1 = requests.get(url, headers=headers, cookies=cookies).content
    s1 = BeautifulSoup(r1, 'html.parser').find('button', id="down")
    if s1 is not None:
        s1 = s1.get('onclick').split("'")[1]
    else:
        raise GDToTException("No such file exists")
    headers['referer'] = url
    s2 = BeautifulSoup(requests.get(s1, headers=headers, cookies=cookies).content, 'html.parser').find('meta').get('content').split('=',1)[1]
    headers['referer'] = s1
    s3 = BeautifulSoup(requests.get(s2, headers=headers, cookies=cookies).content, 'html.parser').find('div', align="center")
    if s3 is not None:
        return s3.find('a', class_="btn btn-outline-light btn-user font-weight-bold").get('href')
    s3 = BeautifulSoup(requests.get(s2, headers=headers, cookies=cookies).content, 'html.parser')
    status = s3.find('h4').text
    raise GDToTException(f"{status}")
