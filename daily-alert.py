import os
import json
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

REGIONS = ["김해", "부산 강서구", "부산 사하구", "부산 사상구"]

OPENING_WORDS = [
    "신규 개원", "신규개원", "개원 예정", "개원예정",
    "개원 멤버", "개원멤버", "개원 준비", "개원준비",
    "개원 직원", "개원직원", "오픈 예정", "오픈예정",
    "신규 오픈", "신규오픈", "개원합니다", "개원팀"
]

JOB_WORDS = [
    "간호사", "임상병리사", "방사선사", "간호조무사",
    "원무", "코디네이터", "채용", "구인", "모집", "직원"
]

def clean(text):
    text = html.unescape(text or "")
    return " ".join(text.replace("<b>", "").replace("</b>", "").split()).lower()

def search(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko"
    })
    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return ET.fromstring(response.read())

def send(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true"
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=25) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("텔레그램 전송 실패")

def main():
    results = {}
    errors = 0
    cutoff = datetime.now().astimezone() - timedelta(days=30)

    for region in REGIONS:
        for phrase in ["개원", "개원 예정", "신규 개원", "개원 멤버"]:
            query = f'"{region}" "{phrase}" 병원 채용'
            try:
                root = search(query)
                for item in root.findall(".//item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    desc = item.findtext("description", "")
                    pub_date = item.findtext("pubDate", "")
                    combined = clean(title + " " + desc)

                    if not link or link in results:
                        continue

                    try:
                        published = parsedate_to_datetime(pub_date)
                        if published < cutoff:
                            continue
                    except (TypeError, ValueError, OverflowError):
                        pass

                    if not any(word in combined for word in OPENING_WORDS):
                        continue
                    if not any(word in combined for word in JOB_WORDS):
                        continue

                    results[link] = (region, title, link)
            except Exception as exc:
                errors += 1
                print(f"검색 오류 ({region}, {phrase}): {exc}")

    lines = [
        "🏥 부산 신규개원 알리미",
        "검색 범위: 최근 30일",
        ""
    ]

    if results:
        for region, title, link in results.values():
            lines.append(f"📍 {region}\n{title}\n{link}\n")
    else:
        lines.append("조건에 맞는 공고가 없습니다.")
        lines.append("검색 오류가 없다면 검색엔진에 노출된 결과가 없을 수 있습니다.")
