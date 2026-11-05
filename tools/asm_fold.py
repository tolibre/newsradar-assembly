
# ==================== 국회팀판: 사진 기사 보강·주요 매체 밖·지역 기사 접기 (0-88, 2026-11-06) ====================
# tools/make_variant.py가 이 파일 내용을 news_monitor.py 맨 아래(main 바로 앞)에 넣는다. 원본 함수는 그대로 두고
# 전역 이름을 감싸 바꾼다(_attach_weak·is_photo_article·build_live_data) — 호출하는 쪽이 실행 때 전역 이름으로 찾으므로 그대로 적용된다.
#
# 사용자 결정(11/6 00:39·00:48):
#  ① 주요 매체가 아니고 [단독]도 아닌 묶음은 접는다. 주요 매체 = 통신 3 + 종합일간지 10 + 방송 9(지상파·종편·보도채널)
#     + 헤럴드경제(석간) + 데일리안·오마이뉴스·노컷뉴스·내일신문. 경제지(매경·한경·머투·파뉴 등)는 국회팀엔 주요 매체가 아니다.
#  ② 사진 기사를 더 걸러 낸다(빼기).
#  ③ 국회팀이 볼 필요 없는 지역 기사(시·도당·지방의회·단체장 등)는 접는다.
# 접기는 원본 '관련 약함'(0-58) 장치를 그대로 쓴다 — 기사마다 wk=1, 묶음 기사 **전부**가 wk일 때만 섹션 끝 접힌 줄로.
# 그래서 주요 매체가 한 곳이라도 받은 묶음, [단독]이 든 묶음은 펼친 채로 남는다. 검색·'선택' 보기에선 펼쳐 보인다(원본 동작).

ASM_MAJOR_MEDIA = {
    "연합뉴스", "뉴시스", "뉴스1",
    "조선일보", "중앙일보", "동아일보", "한겨레", "경향신문", "한국일보", "서울신문", "국민일보", "세계일보", "문화일보",
    "KBS", "KBS 뉴스", "MBC", "MBC 뉴스", "SBS", "SBS 뉴스", "YTN", "연합뉴스TV", "JTBC", "TV조선", "채널A", "MBN",
    "헤럴드경제", "데일리안", "오마이뉴스", "노컷뉴스", "CBS노컷뉴스", "내일신문",
}
ASM_MAJOR_MEDIA |= {short_media_name(x) for x in ASM_MAJOR_MEDIA}   # 페이지 표시명('경향'·'한국'·'내일')도

# ③ 지역 기사 — 제목 낱말로만 판정(매체로는 안 한다: 매일신문·대전일보·부산일보 기사도 대부분 전국 정치였다, 11/6 실측).
#   '시장·도지사·교육감'은 넣지 않는다('서울시장 재선거' 같은 전국 이슈가 걸림). '당협'만 있는 것도 뺌('당무감사위…당협 평가'는 중앙당 기사).
ASM_REGION_RE = re.compile(
    r"(?:시당|도당|시·도당|당원협의회|당협위원장|지역위원회|지역위원장|"
    r"[시도구군]의회|[시도구군]의원|광역의원|기초의원|지방의원|구청장|군수|국비)")

ASM_WL = {"label": "비주요·지역",
          "desc": "주요 매체(통신 3·종합지 10·방송 9·헤럴드경제·데일리안·오마이뉴스·노컷뉴스·내일신문)가 한 곳도 받지 않은 묶음과, "
                  "시·도당·지방의회·구청장·군수·국비처럼 지역 사안인 묶음을 섹션 끝에 접어 둡니다. [단독]은 접지 않고, 건수에는 포함하며, "
                  "검색·‘선택’ 보기에서는 펼쳐 보입니다."}


def asm_fold_reason(title, source):
    """접을 기사면 사유('비주요'·'지역'), 아니면 ''. [단독]은 늘 ''."""
    if priority_mark(title) == "🔥":
        return ""
    if ASM_REGION_RE.search(strip_media_tail(clean(title or ""))):
        return "지역"
    if (source or "").strip() not in ASM_MAJOR_MEDIA:
        return "비주요"
    return ""


_asm_orig_attach_weak = _attach_weak


def _attach_weak(groups):
    n = _asm_orig_attach_weak(groups)
    for g in groups:
        for clu in g["clusters"]:
            for it in clu:
                if not it.get("wk") and asm_fold_reason(it.get("t") or "", it.get("s") or ""):
                    it["wk"] = 1
                    n += 1
    return n


# ② 사진 기사 보강 — 사진 설명형 장면 제목. 원본·생성기 규칙(직함으로 끝)이 놓치는 것: 정당·'의원들'·이름 나열로 끝나는 장면 제목
#    ('구호 외치는 국민의힘', '본회의장 앞에 모인 국민의힘 의원들', '본회의 참석한 김민석-한병도')과 행사 이름만 있는 제목('민주당 의원총회').
#    **사진을 내는 매체에만** — '조준 나선 與'(부산일보)·'정부광고 준다는 與'(한경) 같은 기사 제목이 같은 꼴이다.
#    (검토 후 버린 안: '같은 제목의 사진 원본(뉴시스 NISI 등)이 있으면 구글 경로 기사도 사진' — 뉴시스·뉴스1은 기사 제목을 그대로 단
#     사진을 함께 내서 '與, 가상자산 과세 2년 추가 유예 검토' 같은 진짜 기사가 걸렸다(11/6 실측 10여 건).)
ASM_PHOTO_DESK = {"뉴시스", "뉴스1", "뉴스핌", "노컷뉴스", "CBS노컷뉴스", "데일리안", "연합뉴스", "머니투데이",
                  "더팩트", "아시아투데이", "이데일리", "서울경제"}
ASM_PHOTO_DESK_DOMAINS = ("newsis.com", "news1.kr", "newspim.com", "nocutnews.co.kr", "dailian.co.kr", "yna.co.kr",
                          "mt.co.kr", "tf.co.kr", "asiatoday.co.kr", "edaily.co.kr", "sedaily.com")
_ASM_NFIN = "".join(chr(c) for c in range(0xAC00, 0xD7A4) if (c - 0xAC00) % 28 == 4)   # 받침 ㄴ 글자(선·인·간·든…)
_ASM_PARTY = r"(?:더불어민주당|민주당|국민의힘|국힘|조국혁신당|혁신당|개혁신당|진보당|여야|與|野|여당|야당|범여권)"
_ASM_CAP_SCENE = re.compile(
    r"(?:^|\s)\S*(?:는|[" + _ASM_NFIN + r"])\s(?:\S+\s+){0,4}"
    r"(?:" + _ASM_PARTY + r"(?:\s?(?:의원들|지도부|의원단|당원들|원내대표단|최고위원들))?"
    r"|[가-힣]{2,4}(?:\s?[-·,]\s?[가-힣]{2,4})+"
    r"|[가-힣]{2,4}\s(?:대표|원내대표|최고위원|의원|위원장|대변인|사무총장|의장|부의장|장관|총리|정책위의장|원내수석부대표|비대위원장)"   # 0-89 '의총장 들어선 한병도 원내대표'
    r"|[가-힣]*(?:위원회|특위)"                                                                                           # 0-89 '파이팅 외치는 민주당 체육특별위원회'
    r"|[가-힣]*(?:의원들|위원들|지도부))$")
# 0-89: 정당 + 작은따옴표 구호·행사만 — "국민의힘 '농협법 강행, 미래대응기금 규탄 기자회견'"(뉴시스 사진)
_ASM_CAP_QUOTE = re.compile(r"^" + _ASM_PARTY + r",?\s*['‘][^'’]{2,40}['’]$")
_ASM_CAP_EVENT = re.compile(
    r"^(?:" + _ASM_PARTY + r"|[가-힣]+(?:위원회|특위|원내대표|대표))?\s?"
    r"(?:의원총회|의총|최고위원회의|원내대책회의|비상대책위원회의|비대위회의|정책조정회의|확대간부회의|규탄대회|규탄집회|"
    r"출정식|현장\s?최고위|기자간담회|간담회|토론회|발대식|출범식|정책의원총회)(?:\s?(?:개최|열려|참석))?$")


def _asm_source_of(title, link):
    m = re.search(r"\s-\s([^-]{1,15})\s*$", title or "")
    if m and m.group(1).strip() in ASM_PHOTO_DESK:
        return True
    l = (link or "").lower()
    return any(d in l for d in ASM_PHOTO_DESK_DOMAINS)


def asm_caption_scene(title, link=""):
    """사진 설명형 장면 제목인지(사진 매체 한정)."""
    if not _asm_source_of(title, link):
        return False
    s = strip_media_tail(clean(title or ""))
    tags = re.findall(r"\[([^\]]*)\]", s)
    if any(not _CAP_NEUTRAL_TAG_RE.match(x) for x in tags):   # 코너명([속보]·[정치 인사이드]·[핫피플] 등)이 달리면 기사
        return False
    if _ASM_CAP_QUOTE.search(re.sub(r"\[[^\]]*\]", "", s).strip()):
        return True
    s = re.sub(r"\[[^\]]*\]|「[^」]*」", "", s).strip().rstrip("'’\" ")
    if not s or len(s) > 32 or re.search(r"[\"“”…?!,]|\.\.\.", s) or re.search(ARTICLE_ENDINGS, s):
        return False
    return bool(_ASM_CAP_EVENT.search(s) or _ASM_CAP_SCENE.search(s))


_asm_orig_is_photo = is_photo_article


def is_photo_article(title, link="", strict=False):
    if _asm_orig_is_photo(title, link, strict=strict):
        return True
    return asm_caption_scene(title, link)


_asm_orig_build_live_data = build_live_data


def build_live_data(conn, now):
    out = _asm_orig_build_live_data(conn, now)
    wl = out.setdefault("wl", {})
    for g in GROUP_ORDER:
        wl.setdefault(g, ASM_WL)
    return out


# ④ 해외 정당 기사(0-89, 사용자 11/6 01:04 "아직도 너무 많다") — '민주당'·'야당' 검색어가 미국 민주당·외국 야당 기사를 끌고 온다.
#    11/2~11/5(미 중간선거 주간) 보고에 펼쳐진 묶음의 약 10%가 미국 민주당 기사였고, 주요 매체가 여럿 받아 접기로도 안 걸렸다(20건짜리 묶음 다수).
#    두 갈래(둘 다 **한국 정치 표지가 없을 때만**):
#     (가) 미국: '민주당'·'공화당' + 미국 정치 낱말(중간선거·상원·하원·주지사·백악관·트럼프·美·미국 등).
#     (나) 그 밖의 나라: 정당 낱말(민주당·야당·여당·野·與·연정) + 나라 표지(日·일본·자민당·이스라엘·네타냐후 등).
#    與·野·여당·야당은 미국 표지와 짝짓지 않는다 — '진성준 美 비자 거부…與 "항의해야" 野 "외교 참사"'처럼 한국 기사가 많다(11/6 실측).
#    한국 표지: 더불어민주당·국민의힘·조국혁신당·李·이재명·국회·청와대·한국·한미·관세·비자·방미·정부 등과 여야 지도부 이름.
_ASM_KOREA_MARK = re.compile(
    r"더불어민주당|국민의힘|국힘|조국혁신당|혁신당|개혁신당|진보당|李|이재명|이\s?대통령|대통령실|청와대|靑|국회|국감|"
    r"한국|韓|한미|대미|방미|비자|관세|통상|우리\s?(?:정부|기업)|정부|여야|與野|윤석열|尹|순방|정청래|김민석|한병도|장동혁|송언석|조국|이준석|한동훈")
_ASM_US_PARTY = re.compile(r"민주당|공화당")
_ASM_US_MARK = re.compile(
    r"美|미국|(?:^|[\s\[(‘'\"“])미\s|중간선거|상원|하원|주지사|백악관|공화당|트럼프|오바마|바이든|해리스|밴스|헤그세스|머스크|"
    r"블루\s?(?:웨이브|쓰나미)|MAGA|뉴욕\s?증시|월가|다우|나스닥|텍사스|미시간|오하이오|알래스카|캘리포니아|애리조나|조지아주|펜실베이니아|위스콘신|CNN|NYT|폭스")
_ASM_ETC_PARTY = re.compile(r"민주당|야당|여당|野|與|연정|집권당")
_ASM_ETC_MARK = re.compile(r"日|일본|자민당|중의원|참의원|입헌민주|이스라엘|네타냐후|대만|민진당|국민당|英|영국|노동당|보수당|獨|독일|佛|프랑스|"
                           r"인도|파키스탄|파라과이|아르헨티나|멕시코|캐나다|호주|러시아|우크라이나|튀르키예|이란|헝가리|폴란드")


def asm_foreign_party(title):
    t = strip_media_tail(clean(title or ""))
    if _ASM_KOREA_MARK.search(t):
        return False
    return bool((_ASM_US_PARTY.search(t) and _ASM_US_MARK.search(t)) or (_ASM_ETC_PARTY.search(t) and _ASM_ETC_MARK.search(t)))


_asm_orig_noise_reason = noise_reason


def noise_reason(title, strict=False, kws=None):
    if asm_foreign_party(title):
        return "해외 정당"
    return _asm_orig_noise_reason(title, strict=strict, kws=kws)
