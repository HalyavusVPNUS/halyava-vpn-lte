import requests
import os
import re
import socket
import time
import base64
from concurrent.futures import ThreadPoolExecutor

# Данные берем из переменных окружения GitHub
GITHUB_USER = os.getenv("GH_USER")
REPO_NAME = os.getenv("GH_REPO")
TOKEN = os.getenv("GH_TOKEN")
FILE_PATH = "lte.txt"

SOURCE_LTE = "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/1sub.txt"
MAX_PING = 450
LIMIT_TOTAL = 500

RU_COUNTRIES = {'RU': 'Россия', 'US': 'США', 'DE': 'Германия', 'NL': 'Нидерланды', 'FI': 'Финляндия', 'TR': 'Турция', 'KZ': 'Казахстан', 'FR': 'Франция', 'GB': 'Великобритания', 'PL': 'Польша', 'SG': 'Сингапур', 'HK': 'Гонконг', 'SE': 'Швеция'}

def get_ping(host, port, timeout=2.5):
    try:
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        res = sock.connect_ex((ip, port))
        sock.close()
        if res == 0: return int((time.time() - start) * 1000)
    except: pass
    return None

def get_country_info(host):
    try:
        r = requests.get(f"http://ip-api.com/json/{host}?fields=status,countryCode", timeout=3.5)
        data = r.json()
        if data.get('status') == 'success':
            code = data.get('countryCode')
            return code, RU_COUNTRIES.get(code, code)
    except: pass
    return "UN", "Unknown"

def process_key(key):
    main_part = key.split('#')[0]
    host_match = re.search(r'@([^:/?#\s]+):?(\d+)?', main_part)
    if not host_match: return None
    host, port = host_match.group(1), int(host_match.group(2)) if host_match.group(2) else 443
    lat = get_ping(host, port)
    if not lat or lat > MAX_PING: return None
    code, name = get_country_info(host)
    emoji = "".join(chr(127397 + ord(c)) for c in code.upper()) if code != "UN" else "🌐"
    return {'main': main_part, 'name': name, 'emoji': emoji, 'ping': lat}

def update_repo(content):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": f"Auto-update LTE: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha: data["sha"] = sha
    res = requests.put(url, headers=headers, json=data)
    if res.status_code in [200, 201]:
        print("Репозиторий LTE обновлен!")
    else:
        print(f"Ошибка: {res.text}")

def run_once():
    r = requests.get(SOURCE_LTE, timeout=15)
    tasks = list(set(re.findall(r'(?:vless|ss|vmess|trojan|hysteria2?)://[^\s]+', r.text)))
    with ThreadPoolExecutor(max_workers=50) as executor:
        processed = [res for res in list(executor.map(process_key, tasks)) if res]
    processed.sort(key=lambda x: (x['name'], x['ping']))
    
    final_list = []
    for idx, item in enumerate(processed[:LIMIT_TOTAL], 1):
        final_list.append(f"{item['main']}#{item['emoji']} {item['name']} LTE #{idx} | @halyava_vpnx")

    header = (
        "#profile-title: Халява ВПН | LTE 🏳️\n"
        "#profile-update-interval: 5\n"
        "#subscription-userinfo: expire=5774966400; total=10995116277760; used=0\n"
        "#profile-web-page-url: https://t.me/halyava_vpnx\n"
        f"#announce: Обновлено! Найдено {len(final_list)} мощных конфигов :) @halyava_vpnx"
    )
    update_repo(header + "\n".join(final_list))

if __name__ == "__main__":
    run_once()
