
import os
import json
import html
import re
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse
from zoneinfo import ZoneInfo


# =========================================================
# 부산3지점 대시보드 - 검색 정확도 개선 버전
# =========================================================

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEOUL_TZ = ZoneInfo("Asia/Seoul")
DAYS_BACK = 30

REGIONS = [
    {
        "label": "김해시",
        "query": '("김해" OR "김해시" OR "경남 김해")',
        "terms": ["김해", "김해시"],
    },
    {
        "label": "부산 강서구",
        "query": '("부산 강서구" OR "부산강서구" OR "강서구 부산")',
        "terms": ["부산 강서구", "부산강서구", "강서구 부산"],
    },
    {
        "label": "부산 사하구",
        "query": '("부산 사하구" OR "부산사하구" OR "사하구 부산")',
        "terms": ["부산 사하구", "부산사하구", "사하구 부산"],
    },
    {
        "label": "부산 사상구",
        "query": '("부산 사상구" OR "부산사상구" OR "사상구 부산")',
        "terms": ["부산 사상구", "부산사상구", "사상구 부산"],
    },
]

# 검색할 채용 사이트와 허용 도메인
SOURCES = [
    ("사람인", "saramin.co.kr"),
    ("잡코리아", "jobkorea.co.kr"),
    ("널스잡", "nursejob.co.kr"),
    ("메디잡", "medijob.cc"),
    ("너스케입", "nurscape.net"),
]

JOB_WORDS = [
    "간호사", "간호조무사", "임상병리사", "방사선사",
    "치위생사", "원무", "코디네이터", "채용", "구인",
    "모집", "직원", "의료진", "간호직", "스탭", "스텝",
    "급구", "정규직", "계약직", "물리치료사", "요양보호사",
]

MEDICAL_WORDS = [
    "병원", "의원", "의료기관", "간호사", "간호조무사",
    "임상병리사", "방사선사", "치위생사", "검진센터",
    "내과", "치과", "한의원", "피부과", "정형외과",
    "건강검진", "의료진", "산부인과", "이비인후과",
    "소아과", "비뇨기과", "재활의학", "요양병원",
    "정신건강의학과",
]

OPENING_WORDS = [
    "개원", "신규 개원", "신규개원", "개원 예정",
    "개원예정", "개원 멤버", "개원멤버", "개원 준비",
    "개원준비", "오픈 예정", "오픈예정", "신설 의원",
    "신설 병원", "개소 예정", "개소예정",
    "진료 개시", "진료개시", "병원 이전", "의원 이전",
]

NON_MEDICAL_WORDS = [
    "의회", "국회", "군의회", "시의회", "구의회",
    "정례회", "본회의", "행정사무감사", "국회의원",
    "정당", "선거", "의원 발의", "의회 개원",
]


def clean(value):
    """HTML 태그와 엔티티를 정리하고 소문자로 변환합니다."""
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split()).lower()


def normalize_title(value):
    """제목 중복 비교를 위한 정규화."""
    value = clean(value)
    return re.sub(r"[^가-힣a-z0-9]", "", value)


def fetch_rss(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        return ET.fromstring(response.read())


def search_web(query):
    params = urllib.parse.urlencode({
        "q": query,
        "format": "rss",
        "cc": "KR",
        "setlang": "ko-KR",
    })
    return fetch_rss("https://www.bing.com/search?" + params)


def search_news(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
    })
    return fetch_rss("https://news.google.com/rss/search?" + params)


def send(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")

    request = urllib.request.Request(url, data=data)

    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError("텔레그램 전송 실패")


def parse_date(value):
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=SEOUL_TZ)
        return parsed.astimezone(SEOUL_TZ)
    except (TypeError, ValueError, OverflowError):
        return None


def region_matches(text, region):
    """제목 또는 요약에 관할 지역명이 실제로 있는지 확인."""
    normalized = clean(text).replace(" ", "")
    return any(
        term.replace(" ", "").lower() in normalized
        for term in region["terms"]
    )


def allowed_source_url(url, expected_domain):
    """검색한 채용 사이트와 실제 URL 도메인이 일치하는지 검사."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme in ("http", "https")
            and (
                host == expected_domain
                or host.endswith("." + expected_domain)
            )
        )
    except ValueError:
        return False


def build_search_plans(cutoff_date):
    plans = []

    role_query = (
        '(간호사 OR 간호조무사 OR 임상병리사 OR 방사선사 '
        'OR 치위생사 OR 원무 OR 코디네이터 OR 채용 OR 구인 OR 모집)'
    )

    for region in REGIONS:
        for source_name, domain in SOURCES:
            query = (
                f"site:{domain} {region['query']} "
                f"{role_query} after:{cutoff_date}"
            )
            plans.append({
                "region": region,
                "kind": "job",
                "source": source_name,
                "domain": domain,
                "query": query,
            })

        news_query = (
            f"{region['query']} "
            '(개원 OR "개원 예정" OR 신규개원 OR "개원 멤버" '
            'OR "오픈 예정" OR "신설 병원" OR "병원 이전") when:30d'
        )
        plans.append({
            "region": region,
            "kind": "news",
            "source": "Google 뉴스",
            "domain": None,
            "query": news_query,
        })

    return plans


def is_duplicate(item, existing_items):
    """같은 URL 또는 사실상 같은 제목의 결과를 중복으로 판단."""
    if item["link"] in existing_items:
        return True

    new_title = normalize_title(item["title"])
    if len(new_title) < 10:
        return False

    for old in existing_items.values():
        if old["region"] != item["region"]:
            continue

        old_title = normalize_title(old["title"])
        if not old_title:
            continue

        # 제목이 거의 같으면 중복으로 처리
        if SequenceMatcher(None, new_title, old_title).ratio() >= 0.92:
            return True

    return False


def main():
    now = datetime.now(SEOUL_TZ)
    cutoff = now - timedelta(days=DAYS_BACK)
    cutoff_date = cutoff.strftime("%Y-%m-%d")

    plans = build_search_plans(cutoff_date)
    results = {}
    errors = 0
    raw_count = 0
    rejected_region = 0
    rejected_source = 0
    rejected_content = 0

    for plan in plans:
        region = plan["region"]

        try:
            if plan["kind"] == "news":
                root = search_news(plan["query"])
            else:
                root = search_web(plan["query"])

        except Exception as exc:
            errors += 1
            print(
                f"검색 오류 [{region['label']} / {plan['source']}]: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        items = root.findall(".//item")
        raw_count += len(items)

        for item in items:
            title = html.unescape(
                item.findtext("title", "")
            ).strip()
            link = item.findtext("link", "").strip()
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")

            if not title or not link:
                continue

            combined = clean(title + " " + description)

            # 1. 지역이 실제로 확인되지 않는 결과는 제외
            if not region_matches(combined, region):
                rejected_region += 1
                continue

            # 2. 정치·의회 관련 오탐 제외
            if any(word in combined for word in NON_MEDICAL_WORDS):
                rejected_content += 1
                continue

            is_opening = any(
                word in combined for word in OPENING_WORDS
            )
            is_job = any(
                word in combined for word in JOB_WORDS
            )
            is_medical = any(
                word in combined for word in MEDICAL_WORDS
            )

            # 3. 채용 결과는 지정한 사이트의 실제 도메인과 일치해야 함
            if plan["kind"] == "job":
                if not allowed_source_url(link, plan["domain"]):
                    rejected_source += 1
                    continue

                if not (is_job and is_medical):
                    rejected_content += 1
                    continue

                source = plan["source"]

            else:
                # 뉴스는 개원 단서와 의료기관 단서가 모두 있어야 함
                if not (is_opening and is_medical):
                    rejected_content += 1
                    continue

                # Google 뉴스 링크는 Google 뉴스 중계 링크임을 명시
                host = (urlparse(link).hostname or "").lower()
                if host != "news.google.com":
                    # 예상하지 못한 외부 URL은 출처를 실제 도메인으로 표시
                    source = host or "출처 확인 필요"
                else:
                    source = "Google 뉴스(원문 중계)"

            published = parse_date(pub_date)

            if published and published < cutoff:
                continue

            date_unknown = published is None
            if date_unknown:
                date_text = "게시일 확인 필요"
                timestamp = 0
            else:
                date_text = published.strftime("%Y-%m-%d")
                timestamp = int(published.timestamp())

            result = {
                "region": region["label"],
                "source": source,
                "title": title,
                "link": link,
                "date": date_text,
                "timestamp": timestamp,
                "opening": is_opening,
                "date_unknown": date_unknown,
                "region_matched": True,
            }

            if is_duplicate(result, results):
                continue

            results[link] = result

    sorted_results = sorted(
        results.values(),
        key=lambda item: (
            item["opening"],
            not item["date_unknown"],
            item["timestamp"],
        ),
        reverse=True,
    )

    # 대시보드 데이터 저장
    dashboard_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "docs",
    )
    os.makedirs(dashboard_dir, exist_ok=True)

    dashboard_data = {
        "updated_at": now.isoformat(timespec="seconds"),
        "summary": {
            "total": len(sorted_results),
            "search_requests": len(plans),
            "raw_count": raw_count,
            "errors": errors,
            "rejected_region": rejected_region,
            "rejected_source": rejected_source,
            "rejected_content": rejected_content,
        },
        "results": sorted_results,
    }

    dashboard_path = os.path.join(dashboard_dir, "results.json")
    with open(dashboard_path, "w", encoding="utf-8") as file:
        json.dump(
            dashboard_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"대시보드 데이터 저장 완료: {dashboard_path}")
    print(f"검색 요청: {len(plans)}건")
    print(f"원시 검색 결과: {raw_count}건")
    print(f"지역 불일치 제외: {rejected_region}건")
    print(f"출처 도메인 불일치 제외: {rejected_source}건")
    print(f"내용 불일치 제외: {rejected_content}건")
    print(f"최종 공고: {len(sorted_results)}건")
    print(f"검색 오류: {errors}건")

    # 텔레그램 알림
    header = [
        "부산3지점 신규개원·채용 알리미",
        f"갱신 시각: {now.strftime('%Y-%m-%d %H:%M')}",
        f"검색 기준: 최근 {DAYS_BACK}일",
        "대상: 김해시·부산 강서구·사하구·사상구",
        f"검색 결과: {len(sorted_results)}건",
        f"지역 불일치 제외: {rejected_region}건",
        f"출처 불일치 제외: {rejected_source}건",
        "",
    ]

    blocks = []
    for item in sorted_results:
        category = "개원 관련 단서" if item["opening"] else "채용 후보"

        blocks.append(
            f"[{category} | {item['region']} | {item['source']}]\n"
            f"게시일: {item['date']}\n"
            f"{item['title']}\n"
            f"{item['link']}"
        )

    if not blocks:
        blocks = [
            "현재 조건에 맞는 공고를 찾지 못했습니다.",
            "검색 결과 0건은 실제 공고가 없다는 뜻은 아닙니다.",
        ]

    messages = []
    current = "\n".join(header)

    for block in blocks:
        if len(current) + len(block) + 2 > 3500:
            messages.append(current)
            current = block
        else:
            current += "\n\n" + block

    if current:
        messages.append(current)

    for message in messages:
        send(message)

    print("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    main()
