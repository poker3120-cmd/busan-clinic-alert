
import os
import json
import html
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 영업 관할지역과 검색에 사용할 지역명
REGIONS = [
    {
        "label": "김해",
        "terms": ["김해", "김해시"]
    },
    {
        "label": "부산 강서구",
        "terms": ["부산 강서구", "강서구 부산"]
    },
    {
        "label": "부산 사하구",
        "terms": ["부산 사하구", "사하구 부산"]
    },
    {
        "label": "부산 사상구",
        "terms": ["부산 사상구", "사상구 부산"]
    },
]

OPENING_WORDS = [
    "개원", "개설", "개원 예정", "개원예정",
    "신규 개원", "신규개원", "개원 준비", "개원준비",
    "개원 멤버", "개원멤버", "개원 직원", "개원직원",
    "오픈", "개소 예정", "개소예정", "신설 의원",
    "신설 병원", "진료 개시", "진료개시"
]

JOB_WORDS = [
    "간호사", "임상병리사", "방사선사", "간호조무사",
    "원무", "코디네이터", "채용", "구인", "모집",
    "직원", "의료진", "스탭", "스텝", "진료실",
    "검진센터", "물리치료사", "의사", "봉직의"
]

MEDICAL_WORDS = [
    "의원", "병원", "내과", "외과", "치과", "한의원",
    "피부과", "안과", "정형외과", "소아과", "산부인과",
    "이비인후과", "비뇨기과", "재활의학", "요양병원",
    "의료기관", "검진센터", "건강검진"
]


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split()).lower()


def search(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko"
    })

    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=20) as response:
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


def build_search_plans():
    plans = []
    seen = set()

    def add(label, query, category):
        key = (query, category)
        if key not in seen:
            seen.add(key)
            plans.append((label, query, category))

    for region in REGIONS:
        label = region["label"]
        primary = region["terms"][0]

        # 신규 개원 및 개원 예정 관련 검색
        opening_queries = [
            f"{primary} 의원 개원",
            f"{primary} 병원 개원",
            f'{primary} "개원 예정"',
            f'{primary} "개원 멤버"',
            f'{primary} "오픈 예정" 의원',
            f"{primary} 의원 개설",
        ]

        for query in opening_queries:
            add(label, query, "opening")

        # 개원 관련 인력 채용 검색
        job_queries = [
            f"{primary} 간호조무사 의원 채용",
            f"{primary} 원무과 병원 채용",
            f"{primary} 의원 직원 모집",
        ]

        for query in job_queries:
            add(label, query, "job")

        # 지역명 표기 차이를 보완하는 추가 검색
        for alias in region["terms"][1:]:
            add(label, f"{alias} 의원 개원", "opening")
            add(label, f'{alias} "개원 멤버"', "opening")

    return plans


def main():
    results = {}
    errors = 0
    rss_items = 0
    recent_items = 0
    date_unknown = 0

    cutoff = datetime.now().astimezone() - timedelta(days=30)
    plans = build_search_plans()

    for region, query, category in plans:
        try:
            root = search(query)

            for item in root.findall(".//item"):
                rss_items += 1

                title = item.findtext("title", "")
                link = item.findtext("link", "").strip()
                desc = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")

                if not link:
                    continue

                # 게시일 확인: 최근 30일인지 검증
                try:
                    if not pub_date:
                        date_unknown += 1
                        continue

                    published = parsedate_to_datetime(pub_date)

                    if published.tzinfo is None:
                        published = published.astimezone()

                    if published < cutoff:
                        continue

                except (TypeError, ValueError, OverflowError):
                    date_unknown += 1
                    continue

                recent_items += 1
                combined = clean(title + " " + desc)

                is_opening = any(
                    word in combined for word in OPENING_WORDS
                )
                is_job = any(
                    word in combined for word in JOB_WORDS
                )
                is_medical = any(
                    word in combined for word in MEDICAL_WORDS
                )

                # 개원 기사: 개원 단서와 의료기관 단서 확인
                if category == "opening":
                    matched = is_opening and is_medical

                # 채용공고: 개원 단서와 채용 단서를 모두 확인
                else:
                    matched = is_opening and is_job

                if not matched:
                    continue

                # 같은 기사가 여러 검색어에서 나오면 한 번만 등록
                if link in results:
                    continue

                results[link] = {
                    "region": region,
                    "title": html.unescape(title).strip(),
                    "link": link,
                    "date": published.astimezone().strftime("%Y-%m-%d")
                }

        except Exception as exc:
            errors += 1
            print(f"검색 오류 ({region}, {query}): {exc}")

    lines = [
        "부산 신규개원 알리미",
        "검색 범위: 최근 30일",
        f"검색 요청: {len(plans)}건",
        f"수집 기사: {rss_items}건 (검색어 중복 포함)",
        f"최근 30일 기사: {recent_items}건",
        ""
    ]

    if results:
        for item in results.values():
            lines.append(
                f"[{item['region']} | {item['date']}]\n"
                f"{item['title']}\n"
                f"{item['link']}\n"
            )
    else:
        lines.append("조건에 맞는 공고가 없습니다.")
        lines.append(
            "검색 결과가 0건이어도 실제 공고가 없다는 뜻은 아닙니다."
        )

    lines.append(f"최종 검색 결과: {len(results)}건")
    lines.append(f"검색 오류: {errors}건")
    lines.append(f"게시일 확인 불가: {date_unknown}건")
    lines.append(
        "※ Google 뉴스 RSS 기반이며 모든 구인 사이트를 검색하지는 않습니다."
    )

    message = "\n".join(lines)

    # 텔레그램 메시지 길이 제한에 대비
    for start in range(0, len(message), 3500):
        send(message[start:start + 3500])

    print(
        f"전송 완료: 결과 {len(results)}건 / "
        f"검색 요청 {len(plans)}건 / 오류 {errors}건"
    )


if __name__ == "__main__":
    main()

import os
import json
import html
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# 영업 관할지역과 검색에 사용할 지역명
REGIONS = [
    {
        "label": "김해",
        "terms": ["김해", "김해시"]
    },
    {
        "label": "부산 강서구",
        "terms": ["부산 강서구", "강서구 부산"]
    },
    {
        "label": "부산 사하구",
        "terms": ["부산 사하구", "사하구 부산"]
    },
    {
        "label": "부산 사상구",
        "terms": ["부산 사상구", "사상구 부산"]
    },
]

OPENING_WORDS = [
    "개원", "개설", "개원 예정", "개원예정",
    "신규 개원", "신규개원", "개원 준비", "개원준비",
    "개원 멤버", "개원멤버", "개원 직원", "개원직원",
    "오픈", "개소 예정", "개소예정", "신설 의원",
    "신설 병원", "진료 개시", "진료개시"
]

JOB_WORDS = [
    "간호사", "임상병리사", "방사선사", "간호조무사",
    "원무", "코디네이터", "채용", "구인", "모집",
    "직원", "의료진", "스탭", "스텝", "진료실",
    "검진센터", "물리치료사", "의사", "봉직의"
]

MEDICAL_WORDS = [
    "의원", "병원", "내과", "외과", "치과", "한의원",
    "피부과", "안과", "정형외과", "소아과", "산부인과",
    "이비인후과", "비뇨기과", "재활의학", "요양병원",
    "의료기관", "검진센터", "건강검진"
]


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split()).lower()


def search(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko"
    })

    url = "https://news.google.com/rss/search?" + params
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=20) as response:
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


def build_search_plans():
    plans = []
    seen = set()

    def add(label, query, category):
        key = (query, category)
        if key not in seen:
            seen.add(key)
            plans.append((label, query, category))

    for region in REGIONS:
        label = region["label"]
        primary = region["terms"][0]

        # 신규 개원 및 개원 예정 관련 검색
        opening_queries = [
            f"{primary} 의원 개원",
            f"{primary} 병원 개원",
            f'{primary} "개원 예정"',
            f'{primary} "개원 멤버"',
            f'{primary} "오픈 예정" 의원',
            f"{primary} 의원 개설",
        ]

        for query in opening_queries:
            add(label, query, "opening")

        # 개원 관련 인력 채용 검색
        job_queries = [
            f"{primary} 간호조무사 의원 채용",
            f"{primary} 원무과 병원 채용",
            f"{primary} 의원 직원 모집",
        ]

        for query in job_queries:
            add(label, query, "job")

        # 지역명 표기 차이를 보완하는 추가 검색
        for alias in region["terms"][1:]:
            add(label, f"{alias} 의원 개원", "opening")
            add(label, f'{alias} "개원 멤버"', "opening")

    return plans


def main():
    results = {}
    errors = 0
    rss_items = 0
    recent_items = 0
    date_unknown = 0

    cutoff = datetime.now().astimezone() - timedelta(days=30)
    plans = build_search_plans()

    for region, query, category in plans:
        try:
            root = search(query)

            for item in root.findall(".//item"):
                rss_items += 1

                title = item.findtext("title", "")
                link = item.findtext("link", "").strip()
                desc = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")

                if not link:
                    continue

                # 게시일 확인: 최근 30일인지 검증
                try:
                    if not pub_date:
                        date_unknown += 1
                        continue

                    published = parsedate_to_datetime(pub_date)

                    if published.tzinfo is None:
                        published = published.astimezone()

                    if published < cutoff:
                        continue

                except (TypeError, ValueError, OverflowError):
                    date_unknown += 1
                    continue

                recent_items += 1
                combined = clean(title + " " + desc)

                is_opening = any(
                    word in combined for word in OPENING_WORDS
                )
                is_job = any(
                    word in combined for word in JOB_WORDS
                )
                is_medical = any(
                    word in combined for word in MEDICAL_WORDS
                )

                # 개원 기사: 개원 단서와 의료기관 단서 확인
                if category == "opening":
                    matched = is_opening and is_medical

                # 채용공고: 개원 단서와 채용 단서를 모두 확인
                else:
                    matched = is_opening and is_job

                if not matched:
                    continue

                # 같은 기사가 여러 검색어에서 나오면 한 번만 등록
                if link in results:
                    continue

                results[link] = {
                    "region": region,
                    "title": html.unescape(title).strip(),
                    "link": link,
                    "date": published.astimezone().strftime("%Y-%m-%d")
                }

        except Exception as exc:
            errors += 1
            print(f"검색 오류 ({region}, {query}): {exc}")

    lines = [
        "부산 신규개원 알리미",
        "검색 범위: 최근 30일",
        f"검색 요청: {len(plans)}건",
        f"수집 기사: {rss_items}건 (검색어 중복 포함)",
        f"최근 30일 기사: {recent_items}건",
        ""
    ]

    if results:
        for item in results.values():
            lines.append(
                f"[{item['region']} | {item['date']}]\n"
                f"{item['title']}\n"
                f"{item['link']}\n"
            )
    else:
        lines.append("조건에 맞는 공고가 없습니다.")
        lines.append(
            "검색 결과가 0건이어도 실제 공고가 없다는 뜻은 아닙니다."
        )

    lines.append(f"최종 검색 결과: {len(results)}건")
    lines.append(f"검색 오류: {errors}건")
    lines.append(f"게시일 확인 불가: {date_unknown}건")
    lines.append(
        "※ Google 뉴스 RSS 기반이며 모든 구인 사이트를 검색하지는 않습니다."
    )

    message = "\n".join(lines)

    # 텔레그램 메시지 길이 제한에 대비
    for start in range(0, len(message), 3500):
        send(message[start:start + 3500])

    print(
        f"전송 완료: 결과 {len(results)}건 / "
        f"검색 요청 {len(plans)}건 / 오류 {errors}건"
    )


if __name__ == "__main__":
    main()
