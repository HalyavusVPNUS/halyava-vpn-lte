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

LIMIT_TOTAL = 1000

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# =========================
# ПИНГ (только фильтр)
# =========================
def get_ping(host, port, timeout=4.0):
    try:
        ip = socket.gethostbyname(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        start = time.time()
        res = sock.connect_ex((ip, port))
        sock.close()

        if res == 0:
            return int((time.time() - start) * 1000)
    except:
        pass

    return None


# =========================
# ОБРАБОТКА КЛЮЧА
# =========================
def process_key(key):
    key = key.strip()
    main_part = key.split('#')[0]

    host_match = re.search(r'@([^:/?#\s]+):?(\d+)?', main_part)
    if not host_match:
        return None

    host = host_match.group(1)
    port = int(host_match.group(2)) if host_match.group(2) else 443

    # просто проверяем жив ли сервер
    if not get_ping(host, port):
        return None

    return {
        "main": main_part
    }


# =========================
# GITHUB UPDATE
# =========================
def update_repo(content):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"

    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    r = requests.get(url, headers=headers)
    sha = r.json().get('sha') if r.status_code == 200 else None

    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    data = {
        "message": f"LTE Update: {time.strftime('%H:%M:%S')}",
        "content": encoded_content,
        "branch": "main"
    }

    if sha:
        data["sha"] = sha

    requests.put(url, headers=headers, json=data)


# =========================
# MAIN
# =========================
def run_once():
    all_raw_keys = []

    for src in SOURCES:
        try:
            r = requests.get(src, timeout=15)
            if r.status_code == 200:
                all_raw_keys.extend(
                    re.findall(r'(?:vless|ss|vmess|trojan|hysteria2?)://[^\s]+', r.text)
                )
        except:
            continue

    tasks = list(set(all_raw_keys))

    with ThreadPoolExecutor(max_workers=25) as executor:
        results = list(filter(None, executor.map(process_key, tasks)))

    final_list = []

    for idx, item in enumerate(results[:LIMIT_TOTAL], 1):
        final_list.append(
            f"{item['main']}#🇷🇺 Россия LTE #{idx} | @halyava_vpnx"
        )

    header = (
        "#profile-title: Халява ВПН | LTE 🇷🇺\n"
        "#profile-update-interval: 5\n"
        "#subscription-userinfo: expire=5774966400; total=10995116277760; used=0\n"
        "#profile-web-page-url: https://t.me/halyava_vpnx\n"
        f"#announce: LTE Обновлено! Найдено {len(final_list)} мощных конфигов :) @halyava_vpnx\n\n\n"
    )

    update_repo(header + "\n".join(final_list))


if __name__ == "__main__":
    run_once()
