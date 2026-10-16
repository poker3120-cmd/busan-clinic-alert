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
