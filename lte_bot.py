import requests
import os
import re
import socket
import time
import base64
from concurrent.futures import ThreadPoolExecutor

# --- НАСТРОЙКИ ---
GITHUB_USER = os.getenv("GH_USER")
REPO_NAME = os.getenv("GH_REPO")
TOKEN = os.getenv("GH_TOKEN")
FILE_PATH = "lte.txt"

# Источники (Добавлен новый гист)
SOURCES = [
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/1sub.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt"
]

MAX_PING = 650 
LIMIT_TOTAL = 1000

# ПОЛНЫЙ СПИСОК СТРАН
RU_COUNTRIES = {
    'RU': 'Россия', 'US': 'США', 'DE': 'Германия', 'NL': 'Нидерланды', 'FI': 'Финляндия',
    'TR': 'Турция', 'KZ': 'Казахстан', 'FR': 'Франция', 'GB': 'Великобритания', 'PL': 'Польша',
    'SG': 'Сингапур', 'HK': 'Гонконг', 'SE': 'Швеция', 'AT': 'Австрия', 'BY': 'Беларусь',
    'UA': 'Украина', 'JP': 'Япония', 'KR': 'Корея', 'CN': 'Китай', 'CH': 'Швейцария',
    'IT': 'Италия', 'ES': 'Испания', 'CA': 'Канада', 'AU': 'Австралия', 'BR': 'Бразилия',
    'AE': 'ОАЭ', 'IN': 'Индия', 'EE': 'Эстония', 'LV': 'Латвия', 'LT': 'Литва',
    'CZ': 'Чехия', 'HU': 'Венгрия', 'RO': 'Румыния', 'BG': 'Болгария', 'GR': 'Греция',
    'TW': 'Тайвань', 'CY': 'Кипр', 'TH': 'Таиланд', 'NO': 'Норвегия', 'DK': 'Дания',
    'BE': 'Бельгия', 'PT': 'Португалия', 'MD': 'Молдова', 'GE': 'Грузия', 'AM': 'Армения'
}

def get_ping(host, port, timeout=3.5):
    # Две попытки для уменьшения N/A
    for _ in range(2):
        try:
            ip = socket.gethostbyname(host)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            start = time.time()
            res = sock.connect_ex((ip, port))
            sock.close()
            if res == 0:
                return int((time.time() - start) * 1000)
        except: pass
        time.sleep(0.1)
    return None

def get_country_info(host):
    try:
        r = requests.get(f"http://ip-api.com/json/{host}?fields=status,countryCode", timeout=4.0)
        data = r.json()
        if data.get('status') == 'success':
            code = data.get('countryCode')
            return code, RU_COUNTRIES.get(code, code)
    except: pass
    return None, None

def process_key(key):
    key = key.strip()
    main_part = key.split('#')[0]
    host_match = re.search(r'@([^:/?#\s]+):?(\d+)?', main_part)
    if not host_match: return None
    
    host = host_match.group(1)
    port = int(host_match.group(2)) if host_match.group(2) else 443
    
    lat = get_ping(host, port)
    if not lat or lat > MAX_PING: return None
    
    code, name = get_country_info(host)
    if not code: return None 
    
    emoji = "".join(chr(127397 + ord(c)) for c in code.upper())
    return {'main': main_part, 'name': name, 'emoji': emoji, 'ping': lat}

def update_repo(content):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None
    
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {
        "message": f"LTE Update (Double-Gist): {time.strftime('%H:%M:%S')}",
        "content": encoded_content,
        "branch": "main"
    }
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

def run_once():
    try:
        all_raw_keys = []
        for src in SOURCES:
            try:
                r = requests.get(src, timeout=15)
                if r.status_code == 200:
                    keys = re.findall(r'(?:vless|ss|vmess|trojan|hysteria2?)://[^\s]+', r.text)
                    all_raw_keys.extend(keys)
            except: continue
        
        tasks = list(set(all_raw_keys))
        
        with ThreadPoolExecutor(max_workers=35) as executor:
            results = list(executor.map(process_key, tasks))
            
        processed = [res for res in results if res]
        processed.sort(key=lambda x: (x['name'], x['ping']))
        
        grouped = {}
        for item in processed:
            n = item['name']
            if n not in grouped: grouped[n] = []
            grouped[n].append(item)

        final_list = []
        count = 0
        for name in sorted(grouped.keys()):
            for idx, item in enumerate(grouped[name], 1):
                if count >= LIMIT_TOTAL: break
                final_list.append(f"{item['main']}#{item['emoji']} {name} LTE #{idx} | @halyava_vpnx")
                count += 1

        header = (
            "#profile-title: Халява ВПН | LTE 🏳️\n"
            "#profile-update-interval: 5\n"
            "#subscription-userinfo: expire=5774966400; total=10995116277760; used=0\n"
            "#profile-web-page-url: https://t.me/halyava_vpnx\n"
            f"#announce: LTE Обновлено! Найдено {len(final_list)} мощных конфигов :) @halyava_vpnx\n\n\n"
        )
        
        update_repo(header + "\n".join(final_list))
        print(f"Успешно! Добавлено {len(final_list)} серверов.")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    run_once()
