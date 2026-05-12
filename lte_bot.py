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

SOURCES = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt"
]

MAX_PING = 1000 
LIMIT_TOTAL = 1000

RU_COUNTRIES = {
    'RU': 'Россия', 'US': 'США', 'DE': 'Германия', 'NL': 'Нидерланды', 'FI': 'Финляндия',
    'TR': 'Турция', 'KZ': 'Казахстан', 'FR': 'Франция', 'GB': 'Великобритания', 'PL': 'Польша',
    'SG': 'Сингапур', 'HK': 'Гонконг', 'SE': 'Швеция', 'AT': 'Австрия', 'BY': 'Беларусь',
    'UA': 'Украина', 'JP': 'Япония', 'KR': 'Корея', 'CN': 'Китай', 'CH': 'Швейцария',
    'IT': 'Италия', 'ES': 'Испания', 'CA': 'Канада', 'AU': 'Австралия', 'BR': 'Бразилия',
    'AE': 'ОАЭ', 'IN': 'Индия', 'EE': 'Эстония', 'LV': 'Латвия', 'LT': 'Литва'
}

def get_ping(host, port, timeout=3.5):
    try:
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        res = sock.connect_ex((ip, port))
        sock.close()
        if res == 0: return int((time.time() - start) * 1000), ip
    except: pass
    return None, None

def get_country(ip):
    # Попытка №1: ip-api (быстрый)
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode", timeout=3.0)
        code = r.json().get('countryCode')
        if code: return code
    except: pass
    
    # Попытка №2: ipwhois (запасной)
    try:
        r = requests.get(f"https://ipwho.is/{ip}?fields=country_code", timeout=3.0)
        code = r.json().get('country_code')
        if code: return code
    except: pass
    
    return "UN"

def process_key(key):
    key = key.strip()
    main_part = key.split('#')[0]
    host_match = re.search(r'@([^:/?#\s]+):?(\d+)?', main_part)
    if not host_match: return None
    
    host, port = host_match.group(1), int(host_match.group(2)) if host_match.group(2) else 443
    lat, ip = get_ping(host, port)
    
    if not lat or lat > MAX_PING: return None
    
    # Сначала быстрая проверка на РФ по хосту
    code = "RU" if any(m in host.lower() for m in ['.ru', 'msk', 'vdsina', 'beget']) else None
    
    # Если не РФ по хосту, идем в API
    if not code:
        code = get_country(ip)
    
    name = RU_COUNTRIES.get(code, "Иностранец" if code != "RU" else "Россия")
    emoji = "".join(chr(127397 + ord(c)) for c in code.upper()) if code != "UN" else "🌐"
    
    return {'main': main_part, 'name': name, 'emoji': emoji, 'ping': lat}

def update_repo(content):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None
    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    data = {"message": f"LTE Update (Geo Recovery): {time.strftime('%H:%M:%S')}", "content": encoded_content, "branch": "main"}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

def run_once():
    try:
        all_raw_keys = []
        for src in SOURCES:
            r = requests.get(src, timeout=15)
            if r.status_code == 200:
                all_raw_keys.extend(re.findall(r'(?:vless|ss|vmess|trojan|hysteria2?)://[^\s]+', r.text))
        
        tasks = list(set(all_raw_keys))
        # 20 потоков — золотая середина
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = [res for res in list(executor.map(process_key, tasks)) if res]
            
        # Сортируем так: Иностранцы ПЕРВЫМИ, потом Россия
        results.sort(key=lambda x: (x['name'] == 'Россия', x['name'], x['ping']))
        
        final_list = []
        grouped_counts = {}
        
        for item in results[:LIMIT_TOTAL]:
            name = item['name']
            grouped_counts[name] = grouped_counts.get(name, 0) + 1
            final_list.append(f"{item['main']}#{item['emoji']} {name} LTE #{grouped_counts[name]} | @halyava_vpnx")

        header = (
            "#profile-title: Халява ВПН | LTE 🏳️\n"
            "#profile-update-interval: 5\n"
            "#subscription-userinfo: expire=5774966400; total=10995116277760; used=0\n"
            "#profile-web-page-url: https://t.me/halyava_vpnx\n"
            f"#announce: LTE Обновлено! Найдено {len(final_list)} мощных конфигов :) @halyava_vpnx\n\n\n"
        )
        update_repo(header + "\n".join(final_list))
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    run_once()
