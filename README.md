# 뉴스레이다 · 국회(정당)판

CBS노컷뉴스 국회 출입 박정환 기자용 보고 준비 페이지.
원본 [tolibre/news-monitor](https://github.com/tolibre/news-monitor)(김광일 기자 출입처판)에서 설정만 바꿔 만든 판이다.
같은 방식의 재경부판: [tolibre/newsradar-moef](https://github.com/tolibre/newsradar-moef).

- 페이지: https://tolibre.github.io/newsradar-assembly/ (→ `/live/`)
- 섹션: 더불어민주당 · 국민의힘 · 조국혁신당 · 개혁신당 (+ 맨 끝 박정환 기자 본인 기사, 보고 양식에서 `<기처리>`)
- 보고: 업무일 09:00 · 14:00 (원본과 같은 구간·화면 전환 시각)

## 코드를 직접 고치지 말 것

`news_monitor.py`·`render_page.py`·`merge_db.py`·`retitle.py`는 **`tools/make_variant.py`가 원본에서 생성**한다.

```
git clone --depth 1 https://github.com/tolibre/news-monitor /tmp/nm
python tools/make_variant.py /tmp/nm .
```

생성기는 치환마다 원본 등장 횟수를 검사하고, 생성본을 import해 검색어·그룹·보관 기간 값을 확인한 뒤에만 파일을 쓴다. 함수는 run_check의 폴백 한 줄(정당 관문)만 바꾼다.

## 원본과 다른 점

| | 원본 | 이 판 |
|---|---|---|
| 네이버 검색어 | 부처·CBS 등 | 더불어민주당 · 국민의힘 · 조국혁신당 · 개혁신당 (각 최대 3페이지) |
| 제목 판정 약칭 | — | 민주당·與·여당(→더불어민주당) · 국힘·野·야당(→국민의힘) · 혁신당 (네이버 검색 0페이지 — 제목 판정·구글 RSS만). **정권이 바뀌면 與·野 매핑을 바꿀 것** |
| 정당 관문(2026-10-15) | — | 제목에 정당 단서가 없는 기사(본문에만 정당명)는 **[단독]만** 남겨 맨 뒤 '기타 단독' 섹션으로. run_check 폴백 한 줄만 바뀜 |
| 사안 단위 섹션 합치기(2026-10-15) | — | 같은 사안 묶음이 정당 섹션 두 곳 이상에 걸치면 기사가 가장 많은 섹션 하나로 모은다(원본 `LIVE_STORY_MERGE_GROUPS` 자리에 정당 4개). 보고 전체를 한 번에 묶어 판정 — 구간 탭·'전체' 탭·칩·보고 양식이 같은 섹션을 쓴다 |
| 묶음 판정에서 정당명 제외(2026-10-15) | — | 정당명·약칭을 `TOPIC_STOPWORDS`에 더함 — {민주당, 신임}처럼 정당명 하나 + 한 단어로 다른 사안이 묶이던 것 차단(원본엔 안 넣음) |
| 약칭 오탐 규칙 | — | '혁신당'에서 '개혁신당', '민주당'에서 美·입헌·자유 등 다른 당명, '야당'에서 야당역·야당동 제외 |
| 클러스터링 정당명 토큰 | — | 정당명·약칭을 KEYWORD_GROUPS에 넣어 '흔한 토큰'으로 처리(한 단어로 다른 사안이 묶이지 않게) |
| DB 보관 | 90일 | 14일 (정당 기사량이면 90일치가 GitHub 파일 한도 100MB를 넘음) |
| 브라우저 저장키 | `nm-live-*` | `nm-asm-*` |
| 기기 연동·텔레그램·digest 페이지·수확 | 있음 | 없음(재경부판과 같음) |

**제목 판정 근거**(원본 DB 9/14~10/14 제목): '더불어민주당' 9건 vs '민주당' 210건, '국민의힘' 138건 vs '국힘' 223건.

## 운영 (cron-job.org → workflow_dispatch)

URL `https://api.github.com/repos/tolibre/newsradar-assembly/actions/workflows/newsradar-assembly.yml/dispatches`, POST,
헤더는 원본 잡과 같음(PAT `news-monitor-cron`에 이 저장소 추가 필요), 시간대 Asia/Seoul.

| 잡 | 스케줄 | body |
|---|---|---|
| asm-check | `0 5-22 * * *` | `{"ref":"main","inputs":{"mode":"check"}}` |
| asm-precut | `25 8,13 * * 1-5` | 위와 같음 |
| asm-digest | `0 6 * * *` | `{"ref":"main","inputs":{"mode":"digest"}}` |
| asm-retitle | `15 */2 * * *` | `{"ref":"main","inputs":{"mode":"retitle","apply":"1","limit":"100"}}` |

Secrets: `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`(원본과 같은 값 가능). Pages: main / docs.
