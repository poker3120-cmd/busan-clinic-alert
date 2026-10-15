
import os
import json
import html
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEOUL_TZ = ZoneInfo("Asia/Seoul")

# 부산3지점 영업 관할지역
REGIONS = [
    {
        "label": "김해",
        "query": '("김해" OR "김해시" OR "경남 김해")',
        "match_terms": ["김해", "김해시", "경남 김해"],
    },
    {
        "label": "부산 강서구",
        "query": '("부산 강서구" OR "부산강서구")',
        "match_terms": ["부산 강서구", "부산강서구"],
    },
    {
        "label": "부산 사하구",
        "query": '("부산 사하구" OR "부산사하구")',
        "match_terms": ["부산 사하구", "부산사하구"],
    },
    {
        "label": "부산 사상구",
        "query": '("부산 사상구" OR "부산사상구")',
        "match_terms": ["부산 사상구", "부산사상구"],
    },
]

# 검색엔진에 색인된 각 채용 사이트 검색
SOURCES = [
    ("사람인", "saramin.co.kr"),
    ("잡코리아", "jobkorea.co.kr"),
    ("널스잡", "nursejob.co.kr"),
    ("메디잡", "medijob.cc"),
    ("너스케입", "recruit.nurscape.net"),
]

JOB_WORDS = [
    "간호사", "간호조무사", "임상병리사", "방사선사", "치위생사",
    "원무", "코디네이터", "채용", "구인", "모집", "직원",
    "의료진", "간호직", "스탭", "스텝", "급구", "정규직",
    "계약직", "인력 충원", "물리치료사", "요양보호사",
]

MEDICAL_WORDS = [
    "병원", "의원", "의료기관", "간호사", "간호조무사",
    "임상병리사", "방사선사", "치위생사", "진료", "검진센터",
    "내과", "치과", "한의원", "피부과", "정형외과", "외래",
    "건강검진", "의료진", "산부인과", "이비인후과", "소아과",
    "비뇨기과", "재활의학", "요양병원", "정신건강의학과",
]

OPENING_WORDS = [
    "개원", "신규 개원", "신규개원", "개원 예정", "개원예정",
    "개원 멤버", "개원멤버", "개원 준비", "개원준비",
    "오픈 예정", "오픈예정", "신설 의원", "신설 병원",
    "개소 예정", "개소예정", "진료 개시", "진료개시",
]

NON_MEDICAL_WORDS = [
    "의회", "국회", "군의회", "시의회", "구의회", "정례회",
    "본회의", "행정사무감사", "국회의원", "정당", "선거",
    "의원 발의", "의회 개원",
]


def clean(text):
    """HTML 엔티티와 태그, 불필요한 공백을 정리합니다."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split()).lower()


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
        content = response.read()

    return ET.fromstring(content)


def search_web(query):
    """Bing 웹 검색 RSS"""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "rss",
        "cc": "KR",
        "setlang": "ko-KR",
    })

    return fetch_rss(
        "https://www.bing.com/search?" + params
    )


def search_news(query):
    """Google 뉴스 RSS"""
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
    })

    return fetch_rss(
        "https://news.google.com/rss/search?" + params
    )


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


def build_search_plans(cutoff_date):
    plans = []

    role_query = (
        '(간호사 OR 간호조무사 OR 임상병리사 OR 방사선사 '
        'OR 치위생사 OR 원무 OR 코디네이터 OR 채용 OR 구인 OR 모집)'
    )

    for region in REGIONS:
        # 사람인·잡코리아·널스잡·메디잡·너스케입
        for source_name, domain in SOURCES:
            query = (
                f"site:{domain} {region['query']} {role_query} "
                f"after:{cutoff_date}"
            )

            plans.append({
                "region": region,
                "source": source_name,
                "query": query,
                "kind": "job",
            })

        # 신규 개원 관련 뉴스
        news_query = (
            f'{region["query"]} '
            '(개원 OR "개원 예정" OR 신규개원 OR "개원 멤버" '
            'OR "오픈 예정" OR "신설 병원") when:30d'
        )

        plans.append({
            "region": region,
            "source": "Google 뉴스",
            "query": news_query,
            "kind": "news",
        })

    return plans


def parse_date(pub_date):
    if not pub_date:
        return None

    try:
        published = parsedate_to_datetime(pub_date)

        if published.tzinfo is None:
            published = published.replace(tzinfo=SEOUL_TZ)

        return published.astimezone(SEOUL_TZ)

    except (TypeError, ValueError, OverflowError):
        return None


def main():
    results = {}
    errors = 0
    raw_count = 0
    fallback_count = 0
    source_counts = {}

    now = datetime.now(SEOUL_TZ)
    cutoff = now - timedelta(days=30)
    cutoff_date = cutoff.strftime("%Y-%m-%d")

    plans = build_search_plans(cutoff_date)

    for plan in plans:
        region = plan["region"]
        source = plan["source"]
        query = plan["query"]
        result_source = source

        try:
            if plan["kind"] == "news":
                try:
                    root = search_news(query)

                except Exception as google_exc:
                    # Google 뉴스 실패 시 Bing 웹 검색으로 대체
                    fallback_count += 1

                    fallback_query = (
                        f'{region["query"]} '
                        '(개원 OR "개원 예정" OR 신규개원 OR "개원 멤버" '
                        f'OR "오픈 예정" OR "신설 병원") after:{cutoff_date}'
                    )

                    print(
                        f"Google 뉴스 검색 실패 ({region['label']}): "
                        f"{google_exc}; Bing 대체 검색 실행"
                    )

                    root = search_web(fallback_query)
                    result_source = "Bing 대체검색"

            else:
                root = search_web(query)

        except Exception as exc:
            errors += 1

            print(
                f"검색 오류 ({source}, {region['label']}): "
                f"{type(exc).__name__}: {exc}"
            )

            continue

        items = root.findall(".//item")
        raw_count += len(items)

        source_counts[result_source] = (
            source_counts.get(result_source, 0) + len(items)
        )

        for item in items:
            title = html.unescape(
                item.findtext("title", "")
            ).strip()

            link = item.findtext("link", "").strip()
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")

            if not link:
                continue

            combined = clean(title + " " + description)

            is_opening = any(
                word in combined for word in OPENING_WORDS
            )

            is_job = any(
                word in combined for word in JOB_WORDS
            )

            is_medical = any(
                word in combined for word in MEDICAL_WORDS
            )

            is_nonmedical = any(
                word in combined for word in NON_MEDICAL_WORDS
            )

            # 의회·정치 관련 '개원' 오탐 제외
            if is_nonmedical:
                continue

            # 뉴스는 개원 단서와 의료기관 단서가 모두 필요
            if plan["kind"] == "news":
                if not (is_opening and is_medical):
                    continue

            else:
                # 채용 사이트 결과는 관련 단서가 하나라도 있으면 후보화
                if not (is_job or is_medical or is_opening):
                    continue

            published = parse_date(pub_date)

            # 게시일을 확인할 수 있고 30일보다 오래됐다면 제외
            if published and published < cutoff:
                continue

            # 날짜가 없으면 후보에서 버리지 않고 별도 표시
            date_unknown = published is None

            if date_unknown:
                date_text = "게시일 확인 필요"
                timestamp = 0
            else:
                date_text = published.strftime("%Y-%m-%d")
                timestamp = published.timestamp()

            region_matched = any(
                term.lower() in combined
                for term in region["match_terms"]
            )

            region_text = region["label"]

            if not region_matched:
                region_text += " (지역 확인 필요)"

            if link not in results:
                results[link] = {
                    "region": region_text,
                    "source": result_source,
                    "title": title or "제목 확인 필요",
                    "link": link,
                    "date": date_text,
                    "timestamp": timestamp,
                    "opening": is_opening,
                    "date_unknown": date_unknown,
                    "region_matched": region_matched,
                }

            else:
                # 중복 링크는 하나로 합치고 출처 정보를 보완
                existing = results[link]

                sources = existing["source"].split(", ")

                if result_source not in sources:
                    sources.append(result_source)
                    existing["source"] = ", ".join(sources)

                if is_opening:
                    existing["opening"] = True

                if region_matched and not existing["region_matched"]:
                    existing["region"] = region["label"]
                    existing["region_matched"] = True

                if timestamp and (
                    not existing["timestamp"]
                    or timestamp > existing["timestamp"]
                ):
                    existing["date"] = date_text
                    existing["timestamp"] = timestamp
                    existing["date_unknown"] = False

    # 개원 단서와 게시일 확인 여부를 기준으로 정렬
    sorted_results = sorted(
        results.values(),
        key=lambda item: (
            item["opening"],
            not item["date_unknown"],
            item["timestamp"],
        ),
        reverse=True,
    )

    header = [
        "부산 신규개원 알리미",
        "검색 기준: 최근 30일 (게시일 미확인 후보는 별도 표시)",
        "검색 대상: 사람인·잡코리아·널스잡·메디잡·너스케입·Google 뉴스",
        f"검색 요청: {len(plans)}건",
        f"검색엔진 수집 결과: {raw_count}건 (중복 포함)",
        "",
        "사이트별 검색 피드 (중복 포함):",
    ]

    for source_name, _domain in SOURCES:
        header.append(
            f"{source_name}: {source_counts.get(source_name, 0)}건"
        )

    header.append(
        f"Google 뉴스: {source_counts.get('Google 뉴스', 0)}건"
    )

    header.append(
        f"Bing 대체검색: {source_counts.get('Bing 대체검색', 0)}건"
    )

    header.extend([
        "",
        f"최종 후보: {len(sorted_results)}건",
        f"검색 오류: {errors}건",
        f"Google 뉴스에서 Bing으로 대체한 요청: {fallback_count}건",
        (
            "게시일 확인 필요 후보: "
            f"{sum(1 for item in sorted_results if item['date_unknown'])}건"
        ),
        "※ 검색엔진 색인 기반으로 모든 채용 사이트를 전수 수집하지는 않습니다.",
        "※ 게시일 미확인 후보는 최근 30일 게시 여부를 확정할 수 없습니다.",
    ])

    blocks = []

    for item in sorted_results:
        if item["opening"]:
            category = "개원 관련 단서"
        else:
            category = "채용 후보·개원 여부 확인 필요"

        blocks.append(
            f"[{category} | {item['region']} | {item['source']}]\n"
            f"게시일: {item['date']}\n"
            f"{item['title']}\n"
            f"{item['link']}"
        )

    if not blocks:
        blocks = [
            "조건에 맞는 공고를 찾지 못했습니다.",
            "검색 결과가 0건이어도 실제 공고가 없다는 뜻은 아닙니다.",
        ]

    # 텔레그램 메시지 길이 제한에 맞춰 항목별 분할 전송
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

    print(
        f"전송 완료: 후보 {len(sorted_results)}건, "
        f"검색 오류 {errors}건, "
        f"Google 뉴스 대체검색 {fallback_count}건"
    )


if __name__ == "__main__":
    main()
