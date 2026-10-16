import os
import re
import json
import html
import base64
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo


# =========================================================
# 부산3지점 대시보드
# - 실제 구인사이트 공고와 개원 관련 기사를 분리 수집
# - 기존 docs/results.json / GitHub Pages / Telegram 형식 유지
# - 검색 결과마다 원문 주소를 추가로 접속하지 않아 실행시간 단축
# =========================================================

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

SEOUL = ZoneInfo("Asia/Seoul")
DAYS_BACK = 30

REGIONS = [
    {"label": "김해시", "query": '(김해 OR 김해시)', "terms": ["김해", "김해시"], "district": None},
    {"label": "강서구", "query": '("부산 강서구" OR 부산강서구 OR 강서구)', "terms": ["강서구", "부산 강서구", "부산강서구"], "district": "강서구"},
    {"label": "사하구", "query": '("부산 사하구" OR 부산사하구 OR 사하구)', "terms": ["사하구", "부산 사하구", "부산사하구"], "district": "사하구"},
    {"label": "사상구", "query": '("부산 사상구" OR 부산사상구 OR 사상구)', "terms": ["사상구", "부산 사상구", "부산사상구"], "district": "사상구"},
]

# 실제 채용공고를 확인할 사이트 도메인
# 너스케입은 현재 채용 서비스가 recruit.nurscape.net에서 운영됩니다.
# 각 항목: 표시 이름, 검색할 도메인, 허용할 기본 도메인
SOURCES = [
    ("사람인", "saramin.co.kr", "saramin.co.kr"),
    ("잡코리아", "jobkorea.co.kr", "jobkorea.co.kr"),
    ("널스잡", "nursejob.co.kr", "nursejob.co.kr"),
    ("메디잡", "medijob.cc", "medijob.cc"),
    ("너스케입 커리어", "recruit.nurscape.net", "nurscape.net"),
]

JOB_WORDS = [
    "채용", "구인", "모집", "간호사", "간호조무사", "조무사",
    "임상병리사", "방사선사", "치위생사", "원무", "코디네이터",
    "의료진", "직원", "급구", "물리치료사", "요양보호사",
    "검사실", "진료 보조", "의료기사", "의사", "약사", "치과위생사",
]

MEDICAL_WORDS = [
    "병원", "의원", "의료", "간호", "임상병리", "방사선", "치과",
    "내과", "피부과", "한의원", "검진센터", "재활의학", "요양병원",
    "원무", "치위생", "물리치료", "검사실", "정형외과", "소아과",
    "이비인후과", "비뇨의학과", "산부인과", "안과", "신경외과",
    "정신건강의학과", "간호조무사", "의료기사",
]

OPENING_WORDS = [
    "개원", "신규 개원", "신규개원", "개원 예정", "개원예정",
    "개원 멤버", "개원멤버", "개원 준비", "개원준비", "오픈 예정",
    "오픈예정", "신설 병원", "신설 의원", "개소 예정", "개소예정",
    "진료 개시", "진료개시", "병원 이전", "의원 이전", "신규 오픈",
    "신규오픈", "진료 시작", "새 단장해", "새롭게 개원",
]

NON_MEDICAL_WORDS = [
    "국회의원", "시의원", "구의원", "군의원", "시의회", "구의회",
    "군의회", "의회 개원", "본회의", "행정사무감사", "의원 발의",
    "정당", "선거", "채용비리", "채용 비리", "부정채용", "징역",
    "선고", "의원직", "정치자금",
]

OTHER_REGION_WORDS = [
    "서울", "인천", "대구", "대전", "광주", "울산", "세종",
    "수원", "용인", "성남", "고양", "부천", "안양", "평택",
    "천안", "청주", "포항", "전주", "제주", "강원도",
    "충청북도", "충청남도", "전라북도", "전라남도",
]


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]*>", " ", value)
    return " ".join(value.split()).strip()


def compact(value):
    return re.sub(r"[\s\W_]+", "", clean(value).lower())


def fetch_rss(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Busan3Dashboard/3.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return ET.fromstring(response.read())


def search_bing(query):
    params = urllib.parse.urlencode({
        "q": query,
        "format": "rss",
        "cc": "KR",
        "setlang": "ko-KR",
    })
    return fetch_rss("https://www.bing.com/search?" + params)


def search_google_news(query):
    params = urllib.parse.urlencode({
        "q": query,
        "hl": "ko",
        "gl": "KR",
        "ceid": "KR:ko",
    })
    return fetch_rss("https://news.google.com/rss/search?" + params)


def parse_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SEOUL)
        return dt.astimezone(SEOUL)
    except (ValueError, TypeError, OverflowError):
        return None


def get_host(url):
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def source_url_matches(url, domain):
    host = get_host(url)
    return host == domain or host.endswith("." + domain)


def unwrap_bing_url(url):
    """Bing RSS의 추적 링크라면 URL 안에 포함된 실제 주소를 추출합니다."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if "bing.com" not in host:
            return url

        params = parse_qs(parsed.query)
        for key in ("url", "u", "r"):
            for raw_value in params.get(key, []):
                candidate = urllib.parse.unquote(raw_value)
                # Bing의 u 파라미터는 a1 + URL-safe Base64 형식일 수 있습니다.
                if candidate.startswith("a1"):
                    encoded = candidate[2:]
                    try:
                        decoded = base64.urlsafe_b64decode(
                            encoded + "=" * (-len(encoded) % 4)
                        ).decode("utf-8", errors="ignore")
                        if decoded.startswith(("http://", "https://")):
                            candidate = decoded
                    except Exception:
                        pass
                if candidate.startswith(("http://", "https://")):
                    return candidate
        return url
    except Exception:
        return url


def normalize_link(url):
    # 검색 결과마다 추가 접속을 하지 않아 워크플로우가 느려지는 것을 방지합니다.
    # Google 뉴스 링크는 클릭 시 열 수 있는 RSS 기사 링크 그대로 유지합니다.
    return unwrap_bing_url(clean(url))


def is_generic_page(url):
    try:
        parsed = urlparse(url)
        return not parsed.path.strip("/")
    except ValueError:
        return True


def parse_google_source(item):
    source_node = item.find("source")
    if source_node is not None and source_node.text:
        return clean(source_node.text)
    return "Google 뉴스"


def other_region_match(text):
    value = compact(text)
    return any(compact(term) in value for term in OTHER_REGION_WORDS)


def region_match(text, region):
    value = compact(text)
    if region["label"] == "김해시":
        return "김해" in value

    district = compact(region["district"])
    if district not in value:
        return False
    if "부산" in value:
        return True
    if other_region_match(text):
        return False
    # 구 이름은 확인되지만 부산이라는 단서가 없는 경우는 후보로 표시합니다.
    return True


def make_search_plans():
    plans = []
    job_groups = [
        '(간호사 OR 간호조무사 OR 조무사 OR 의료진 OR 채용 OR 구인 OR 모집)',
        '(임상병리사 OR 방사선사 OR 치위생사 OR 물리치료사 OR 원무 OR 코디네이터 OR 검사실)',
    ]
    opening_terms = (
        '(개원 OR "개원 예정" OR 신규개원 OR "오픈 예정" '
        'OR "신설 병원" OR "병원 이전" OR "새 단장")'
    )

    for region in REGIONS:
        region_query = region["query"]

        # 실제 채용사이트 검색만 구인 공고 후보로 분류합니다.
        for name, query_domain, allowed_domain in SOURCES:
            for job_terms in job_groups:
                plans.append({
                    "kind": "job",
                    "region": region,
                    "source": name,
                    "domain": allowed_domain,
                    "query": f'site:{query_domain} {region_query} {job_terms}',
                })

        # Google 뉴스는 신규 개원 관련 기사 확인에만 사용합니다.
        # 뉴스 기사가 실제 구인공고로 섞이지 않도록 채용 뉴스 검색은 제외합니다.
        plans.append({
            "kind": "news_opening",
            "region": region,
            "source": "Google 뉴스",
            "domain": None,
            "query": f'{region_query} {opening_terms} when:30d',
        })

    return plans


def extract_hospital_names(title):
    patterns = [
        r"[가-힣A-Za-z0-9·]+(?:종합병원|요양병원|대학병원|병원)",
        r"[가-힣A-Za-z0-9·]+(?:의원|치과|한의원|의료원|검진센터)",
    ]
    found = set()
    for pattern in patterns:
        for name in re.findall(pattern, title or ""):
            normalized = compact(name)
            if len(normalized) >= 3:
                found.add(normalized)
    return found


def extract_date_clues(title):
    value = compact(title)
    clues = set()
    for pattern in (r"\d{1,2}월\d{1,2}일", r"\d{4}년\d{1,2}월\d{1,2}일", r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"):
        clues.update(re.findall(pattern, value))
    return clues


def is_duplicate(result, results):
    if result["link"] in results:
        return True

    title = compact(result["title"])
    if len(title) < 8:
        return False

    hospitals = extract_hospital_names(result["title"])
    dates = extract_date_clues(result["title"])

    for old in results.values():
        old_title = compact(old["title"])
        if title == old_title:
            return True
        if len(title) >= 15 and len(old_title) >= 15:
            if SequenceMatcher(None, title, old_title).ratio() >= 0.90:
                return True
        if result["opening"] and old["opening"] and hospitals:
            old_hospitals = extract_hospital_names(old["title"])
            old_dates = extract_date_clues(old["title"])
            if hospitals & old_hospitals and dates and dates & old_dates:
                return True
    return False


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(url, data=payload)
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("텔레그램 메시지 전송에 실패했습니다.")


def main():
    now = datetime.now(SEOUL)
    cutoff = now - timedelta(days=DAYS_BACK)
    plans = make_search_plans()
    results = {}

    raw_count = 0
    rejected_region = 0
    rejected_source = 0
    rejected_content = 0
    errors = 0
    uncertain_region = 0
    job_site_matches = 0
    opening_news_matches = 0
    source_debug_printed = 0
    content_debug_printed = 0

    for plan in plans:
        region = plan["region"]
        try:
            root = search_google_news(plan["query"]) if plan["kind"].startswith("news_") else search_bing(plan["query"])
        except Exception as exc:
            errors += 1
            print(f"검색 오류 [{region['label']} / {plan['source']}]: {type(exc).__name__}: {exc}")
            continue

        items = root.findall(".//item")
        raw_count += len(items)

        for item in items:
            title = clean(item.findtext("title", ""))
            raw_link = clean(item.findtext("link", ""))
            description = clean(item.findtext("description", ""))
            pub_date = item.findtext("pubDate", "")
            if not title or not raw_link:
                continue

            link = normalize_link(raw_link)
            if is_generic_page(link):
                rejected_content += 1
                continue

            text = clean(title + " " + description)
            is_opening = any(word in text for word in OPENING_WORDS)
            is_job = any(word in text for word in JOB_WORDS)
            is_medical = any(word in text for word in MEDICAL_WORDS)

            if plan["kind"] == "job":
                # 실제 채용사이트 도메인 주소만 허용합니다.
                if not source_url_matches(link, plan["domain"]):
                    rejected_source += 1
                    if source_debug_printed < 8:
                        print(
                            f"[출처 제외 샘플] 검색={plan['source']} / 기대도메인={plan['domain']} / "
                            f"실제도메인={get_host(link)} / 제목={title} / 링크={link}"
                        )
                        source_debug_printed += 1
                    continue

                # 사이트 도메인이 확인된 경우 의료 단어까지 이중으로 요구하지 않습니다.
                # 직종/채용 단어가 있으면 후보로 남겨 실제 공고 누락을 줄입니다.
                if not is_job:
                    rejected_content += 1
                    if content_debug_printed < 8:
                        print(f"[내용 제외 샘플] 출처={plan['source']} / 제목={title} / 설명={description[:180]}")
                        content_debug_printed += 1
                    continue
                source = plan["source"]
                job_site_matches += 1

            else:
                # 정치·의회 기사는 개원 기사로 섞이지 않도록 제외합니다.
                if any(word in text for word in NON_MEDICAL_WORDS):
                    rejected_content += 1
                    continue
                if not is_opening or not is_medical:
                    rejected_content += 1
                    continue
                source = parse_google_source(item)
                opening_news_matches += 1

            if region_match(text, region):
                region_label = region["label"]
                region_confirmed = True
            elif other_region_match(text):
                rejected_region += 1
                continue
            else:
                region_label = "지역 확인 필요"
                region_confirmed = False
                uncertain_region += 1

            published = parse_date(pub_date)
            if published and published < cutoff:
                continue

            if published:
                date_text = published.strftime("%Y-%m-%d")
                timestamp = int(published.timestamp())
                date_unknown = False
            else:
                date_text = "게시일 확인 필요"
                timestamp = 0
                date_unknown = True

            result = {
                "region": region_label,
                "source": source,
                "title": title,
                "link": link,
                "date": date_text,
                "timestamp": timestamp,
                "opening": is_opening if plan["kind"] == "news_opening" else False,
                "date_unknown": date_unknown,
                "region_matched": region_confirmed,
            }

            if is_duplicate(result, results):
                continue
            results[link] = result

    sorted_results = sorted(
        results.values(),
        key=lambda item: (
            item["region_matched"],
            item["opening"],
            not item["date_unknown"],
            item["timestamp"],
        ),
        reverse=True,
    )

    base_dir = os.path.dirname(os.path.abspath(__file__))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    output_path = os.path.join(docs_dir, "results.json")

    data = {
        "updated_at": now.isoformat(timespec="seconds"),
        "summary": {
            "total": len(sorted_results),
            "search_requests": len(plans),
            "raw_count": raw_count,
            "errors": errors,
            "rejected_region": rejected_region,
            "rejected_source": rejected_source,
            "rejected_content": rejected_content,
            "uncertain_region": uncertain_region,
            "job_site_matches": job_site_matches,
            "opening_news_matches": opening_news_matches,
        },
        "results": sorted_results,
    }

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print(f"대시보드 데이터 저장 완료: {output_path}")
    print(f"검색 요청: {len(plans)}건")
    print(f"원시 검색 결과: {raw_count}건")
    print(f"구인사이트 도메인·채용키워드 통과 후보: {job_site_matches}건")
    print(f"개원 뉴스 통과 후보: {opening_news_matches}건")
    print(f"지역 불일치 제외: {rejected_region}건")
    print(f"출처 도메인 불일치 제외: {rejected_source}건")
    print(f"내용 불일치 제외: {rejected_content}건")
    print(f"지역 확인 필요 후보: {uncertain_region}건")
    print(f"최종 공고: {len(sorted_results)}건")
    print(f"검색 오류: {errors}건")

    header = [
        "부산3지점 신규개원·채용 알리미",
        f"갱신: {now.strftime('%Y-%m-%d %H:%M')}",
        f"검색 기간: 최근 {DAYS_BACK}일",
        "대상: 김해시·부산 강서구·사하구·사상구",
        f"최종 후보: {len(sorted_results)}건",
        f"구인사이트 도메인·채용키워드 통과 후보: {job_site_matches}건",
        f"개원 뉴스 후보: {opening_news_matches}건",
        f"지역 확인 필요: {uncertain_region}건",
        "",
    ]

    blocks = []
    for result in sorted_results:
        if result["opening"]:
            category = "개원 관련 기사"
        else:
            category = "구인사이트 공고"
        region_note = "" if result["region_matched"] else " (지역 원문 확인 필요)"
        blocks.append(
            f"[{category}] {result['region']}{region_note}\n"
            f"제목: {result['title']}\n"
            f"게시일: {result['date']}\n"
            f"출처: {result['source']}\n"
            f"{result['link']}"
        )

    if not blocks:
        blocks = [
            "조건에 맞는 결과가 없습니다.",
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
        send_telegram(message)
    print("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    main()
