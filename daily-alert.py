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

# 영업 관할지역
REGIONS = [
    {
        "label": "김해",
        "query": '("김해" OR "김해시" OR "경남 김해")'
    },
    {
        "label": "부산 강서구",
        "query": '("부산 강서구" OR "강서구")'
    },
    {
        "label": "부산 사하구",
        "query": '("부산 사하구" OR "사하구")'
    },
    {
        "label": "부산 사상구",
        "query": '("부산 사상구" OR "사상구")'
    },
]

# 검색 대상 채용 사이트
SOURCES = [
    ("사람인", "saramin.co.kr"),
    ("잡코리아", "jobkorea.co.kr"),
    ("널스잡", "nursejob.co.kr"),
    ("메디잡", "medijob.cc"),
    ("너스케입", "nurscape.net"),
]

JOB_WORDS = [
    "간호사", "간호조무사", "임상병리사", "방사선사",
    "원무", "코디네이터", "채용", "구인", "모집",
    "직원", "의료진", "진료실", "검진센터",
    "의원", "병원", "의료기관", "간호직"
]

OPENING_WORDS = [
    "개원", "신규 개원", "신규개원",
    "개원 예정", "개원예정", "개원 멤버", "개원멤버",
    "개원 준비", "개원준비", "오픈 예정", "오픈예정",
    "신설 의원", "신설 병원", "개소 예정", "진료 개시"
]


def clean(text):
    text = html.unescape(text or "")
    return " ".join(text.split()).lower()


def fetch_rss(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return ET.fromstring(response.read())


def search_web(query):
    """Bing 일반 웹 검색 RSS: 채용 사이트의 색인 페이지 검색"""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "rss",
        "cc": "KR",
        "setlang": "ko-KR"
    })
    url = "https://www.bing.com/search?" + params
    return fetch_rss(url)


def search_news(query):
    """Google 뉴스 RSS: 개원 관련 기사 검색"""
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko"
    })
    url = "https://news.google.com/rss/search?" + params
    return fetch_rss(url)


def send(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true"
    }).encode()

    request = urllib.request.Request(url, data=data)

    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError("텔레그램 전송 실패")


def build_search_plans():
    plans = []

    # 각 지역 × 각 채용 사이트
    for region in REGIONS:
        for source_name, domain in SOURCES:
            query = (
                f"site:{domain} {region['query']} "
                "(간호사 OR 간호조무사 OR 임상병리사 OR 방사선사 "
                "OR 원무 OR 코디네이터 OR 채용 OR 구인 OR 모집 "
                "OR 개원)"
            )

            plans.append({
                "region": region["label"],
                "source": source_name,
                "query": query,
                "kind": "job"
            })

        # 채용 사이트에 나타나지 않는 개원 기사도 별도 검색
        plans.append({
            "region": region["label"],
            "source": "Google 뉴스",
            "query": f'"{region["label"]}" 개원 의원 병원',
            "kind": "news"
        })

    return plans


def main():
    results = {}
    errors = 0
    raw_count = 0
    unknown_dates = 0
    source_counts = {}

    cutoff = datetime.now().astimezone() - timedelta(days=30)
    plans = build_search_plans()

    for plan in plans:
        region = plan["region"]
        source = plan["source"]
        query = plan["query"]

        try:
            if plan["kind"] == "news":
                root = search_news(query)
            else:
                root = search_web(query)

            items = root.findall(".//item")
            raw_count += len(items)
            source_counts[source] = (
                source_counts.get(source, 0) + len(items)
            )

            for item in items:
                title = html.unescape(
                    item.findtext("title", "")
                ).strip()
                link = item.findtext("link", "").strip()
                description = item.findtext("description", "")
                pub_date = item.findtext("pubDate", "")

                if not link or link in results:
                    continue

                combined = clean(title + " " + description)

                is_opening = any(
                    word in combined for word in OPENING_WORDS
                )
                is_job = any(
                    word in combined for word in JOB_WORDS
                )

                # 뉴스는 개원 관련 단서가 있는 경우만 수집
                if plan["kind"] == "news" and not is_opening:
                    continue

                # 채용 사이트 결과는 의료·채용 관련 단서가 필요
                if plan["kind"] == "job" and not (is_job or is_opening):
                    continue

                # 검색 결과에 게시일이 있으면 최근 30일 기준 적용
                published = None

                try:
                    if pub_date:
                        published = parsedate_to_datetime(pub_date)

                        if published.tzinfo is None:
                            published = published.astimezone()

                        if published < cutoff:
                            continue
                    else:
                        unknown_dates += 1

                except (TypeError, ValueError, OverflowError):
                    published = None
                    unknown_dates += 1

                results[link] = {
                    "region": region,
                    "source": source,
                    "title": title,
                    "link": link,
                    "date": (
                        published.astimezone().strftime("%Y-%m-%d")
                        if published else "게시일 확인 필요"
                    ),
                    "timestamp": (
                        published.timestamp() if published else 0
                    ),
                    "opening": is_opening
                }

        except Exception as exc:
            errors += 1
            print(
                f"검색 오류 ({source}, {region}): {exc}"
            )

    # 개원 징후가 뚜렷한 자료를 먼저 표시
    sorted_results = sorted(
        results.values(),
        key=lambda x: (x["opening"], x["timestamp"]),
        reverse=True
    )

    header = [
        "부산 신규개원 알리미",
        "검색 범위: 최근 30일 기준",
        "검색 대상: 사람인·잡코리아·널스잡·메디잡·너스케입·Google 뉴스",
        f"검색 요청: {len(plans)}건",
        f"검색엔진 수집 기사: {raw_count}건 (중복 포함)",
        ""
    ]

    for source, count in source_counts.items():
        header.append(f"{source} 검색 피드: {count}건 (중복 포함)")

    header.extend([
        "",
        f"최종 결과: {len(sorted_results)}건",
        f"검색 오류: {errors}건",
        f"게시일 확인 필요: {unknown_dates}건",
        "※ 검색 사이트의 색인 결과이며 모든 채용공고를 전수 수집하지는 않습니다."
    ])

    # 게시일 미확인 자료는 별도 표기
    blocks = []

    for item in sorted_results:
        category = (
            "개원 관련 단서"
            if item["opening"]
            else "채용공고·개원 여부 확인 필요"
        )

        blocks.append(
            f"[{category} | {item['region']} | {item['source']}]\n"
            f"게시일: {item['date']}\n"
            f"{item['title']}\n"
            f"{item['link']}"
        )

    if not blocks:
        blocks = [
            "조건에 맞는 공고를 찾지 못했습니다.",
            "검색 결과가 0건이어도 실제 공고가 없다는 뜻은 아닙니다."
        ]

    # 텔레그램의 메시지 길이 제한에 맞춰 분할 전송
    current_message = "\n".join(header)

    for block in blocks:
        if len(current_message) + len(block) + 2 > 3500:
            send(current_message)
            current_message = block
        else:
            current_message += "\n\n" + block

    if current_message:
        send(current_message)

    print(
        f"전송 완료: {len(sorted_results)}건, "
        f"수집 기사 {raw_count}건, 오류 {errors}건"
    )


if __name__ == "__main__":
    main()
