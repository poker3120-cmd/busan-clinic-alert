
import os
import json
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

REGIONS = ["김해시", "부산 강서구", "부산 사하구", "부산 사상구"]

# 개원 관련성이 높은 표현
OPENING_PHRASES = [
    "신규 개원", "신규개원", "개원 예정", "개원예정",
    "개원 멤버", "개원멤버", "개원 직원", "개원직원",
    "개원 준비", "개원준비", "개원 병원", "개원 의원",
    "신규 오픈", "신규오픈", "오픈 예정", "오픈예정",
    "오픈 멤버", "오픈멤버", "개원팀", "개원 인력",
    "개원인력", "개원합니다", "개원에 함께",
]

# 제목이나 본문에 이 표현만 단독으로 있으면 개원 공고로 인정하지 않음
WEAK_WORDS = ["개원", "오픈", "병원", "의원"]

# 관련 채용공고에 자주 등장하는 직종
JOB_WORDS = [
    "간호사", "임상병리사", "방사선사", "원무과",
    "코디네이터", "간호조무사", "의료기사", "직원 모집",
    "직원모집", "채용", "구인", "모집",
]

SITES = [
    "site:saramin.co.kr",
    "site:jobkorea.co.kr",
    "site:nursejob.co.kr",
]

def normalize(text):
    text = html.unescape(text or "").lower()
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def fetch_rss(query):
    params = urllib.parse.urlencode({
        "q": query, "hl": "ko", "gl": "KR", "ceid": "KR:ko"
    })
    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return ET.fromstring(response.read())

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=25) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram 전송 실패")

def is_relevant(title, description):
    title = normalize(title)
    body = normalize(description)
    combined = title + " " + body

    # 단순히 '개원'이라는 단어만 등장한 일반 채용은 제외
    strong_in_title = any(p in title for p in OPENING_PHRASES)
    strong_in_text = any(p in combined for p in OPENING_PHRASES)

    # 개원 관련 표현이 없으면 제외
    if not strong_in_text:
        return False

    # 제목에 개원 신호가 있으면 우선 인정.
    # 본문에만 있으면 채용 관련 표현도 있어야 인정.
    if strong_in_title:
        return True

    return any(word in combined for word in JOB_WORDS)

def main():
    found = {}
    cutoff = datetime.now().astimezone() - timedelta(days=7)
    errors = 0

    for region in REGIONS:
        opening_query = " OR ".join(
            f'"{phrase}"' for phrase in OPENING_PHRASES[:12]
        )
        job_query = " OR ".join(f'"{word}"' for word in JOB_WORDS[:6])
        site_query = " OR ".join(SITES)

        query = (
            f'"{region}" ({opening_query}) '
            f'({job_query}) ({site_query})'
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
                except (TypeError, ValueError, OverflowError):
                    pass

                if not is_relevant(title, description):
                    continue

                found[link] = (region, title, link)

        except Exception as exc:
            errors += 1
            print(f"검색 실패 ({region}): {exc}")

    lines = ["🏥 부산 신규개원 알리미", "개원 관련성 필터 적용", ""]

    if found:
        for region, title, link in found.values():
            lines.append(f"📍 {region}\n{title}\n{link}\n")
    else:
        lines.append("조건에 맞는 공고가 검색되지 않았습니다.")
        lines.append("검색 결과가 없다고 실제 공고가 없는 것은 아닙니다.")

    lines.append(f"\n검색 결과: {len(found)}건")
    if errors:
        lines.append(f"검색 오류: {errors}개 지역")
    lines.append("※ 검색엔진 노출 여부에 따라 공고가 누락될 수 있습니다.")

    message = "\n".join(lines)

    for start in range(0, len(message), 3500):
        send_telegram(message[start:start + 3500])

    print(f"전송 완료: {len(found)}건, 검색 오류: {errors}개")

if __name__ == "__main__":
    main()
