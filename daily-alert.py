
import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

REGIONS = [
    "김해시",
    "부산 강서구",
    "부산 사하구",
    "부산 사상구",
]

OPENING_WORDS = [
    "신규 개원", "개원 예정", "개원멤버",
    "개원 멤버", "신규 오픈", "개원",
]

JOB_WORDS = [
    "간호사", "임상병리사", "방사선사",
    "원무과", "코디네이터", "병원", "의원",
]

SITES = [
    "site:saramin.co.kr",
    "site:jobkorea.co.kr",
    "site:nursejob.co.kr",
]

def fetch_rss(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
    })
    url = "https://news.google.com/rss/search?" + params
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return ET.fromstring(response.read())

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode()
    request = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram 전송 실패")

def main():
    found = {}
    cutoff = datetime.now().astimezone() - timedelta(days=7)

    for region in REGIONS:
        query = (
            f'"{region}" '
            f'({" OR ".join(chr(34) + w + chr(34) for w in OPENING_WORDS)}) '
            f'({" OR ".join(chr(34) + w + chr(34) for w in JOB_WORDS)}) '
            f'({" OR ".join(SITES)})'
        )
        try:
            root = fetch_rss(query)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                description = item.findtext("description", "")

                if not link or link in found:
                    continue

                try:
                    published = parsedate_to_datetime(pub_date)
                    if published < cutoff:
                        continue
                except (TypeError, ValueError):
                    pass

                text = (title + " " + description).lower()
                if not any(w.lower() in text for w in OPENING_WORDS):
                    continue

                found[link] = (region, title, link)
        except Exception as exc:
            print(f"검색 실패 ({region}): {exc}")

    if not found:
        send_telegram(
            "🔎 부산 신규개원 알리미\n\n"
            "최근 7일 내 검색된 관련 공고가 없습니다.\n"
            "검색엔진에 노출되지 않은 공고는 누락될 수 있습니다."
        )
        return

    lines = ["🏥 부산 신규개원 알리미", "최근 7일 검색 결과"]
    for region, title, link in found.values():
        lines.append(f"\n📍 {region}\n{title}\n{link}")

    message = "\n".join(lines)
    # Telegram 메시지 길이 제한에 맞춰 분할 전송
    for start in range(0, len(message), 3500):
        send_telegram(message[start:start + 3500])

    print(f"전송 완료: {len(found)}건")

if __name__ == "__main__":
    main()
