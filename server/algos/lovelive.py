import re

from server import config
from server.algos._base import get_post_texts

LOVELIVE_NAME_EN_RE = re.compile(
    r"([^a-z0-9\-]|\b)love ?live($|[^a-z0-9\-]|rs?\b)", re.IGNORECASE
)
LOVELIVE_RE = re.compile(
    r"love\s?live[!\s]*(blue ?bird|days|heardle|s(eries|ky|oundtrack|taff|"
    r"u(nshine|per ?star)))|"
    r"([^ク]|\b)(リンクライク)?ラブライ(ブ[!！\s]*(サンシャイン|スーパースター)?|バー)|"
    r"(thank you|likes) love ?live\b|#lovelive_|lovelive(-anime|_staff)|"
    # School idol
    r"スクールアイドル|(?<!middle )(?<!high )(?<!old )(?<!old-)"
    r"school\s?idol(s?\b|\s?((festiv|music)al|project))?|"
    # Games
    r"\bl(l|ove ?live ?)sif2?\b|\b(ll)?sif(as\b|\s?all[\s\-]?stars)|puchiguru|"
    # ぷちぐる but not ぷちぐるみ
    r"ぷちぐる([^み]|$)|"
    # スクスタ/スクミュ but not words with マスク/スタンド/スタンプ/スタイル/スタッフ
    r"(^|[^マタ])スク(スタ(?!ン[ドプ]|イル|ッフ|ート)|ミュ)|"
    # Love Live! School Idol Project
    # NOTE: Printemps, lily white, BiBi not included due to too many false positives
    r"音ノ木坂?|otonokizaka|[μµ]['’‘`´′]s|にこりんぱな|nicorinpana|"
    r"高坂\s?穂乃果|絢瀬\s?絵里|南\s?ことり|園田\s?海未|星空\s?凛|西木野\s?真姫|東條\s?希|"
    r"小泉\s?花陽|矢澤\s?にこ|nico\snico\sni+\b|#niconiconi+\b|"
    r"エリーチカ|\belichika\b|金曜凛ちゃんりんりんりん|火曜日かよちゃん|"
    r"snow\s?halation([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"(^|[^a-z\u00C0-\u024F\u1E00-\u1EFF\-])a[-\u2010]rise([^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|$)|"
    r"綺羅\s?ツバサ|優木\s?あんじゅ|統堂\s?英玲奈|"
    # Love Live! Sunshine!!
    # NOTE: AZALEA not included due to too many false positives
    r"浦の星女?|uranohoshi|aq(ou|uo)rs|cyaron!?|guilty\s?kiss([^a-z]|$)|"
    # YYY (You, Yoshiko/Yohane, RubY)
    r"(?<!わい)(?<!わーい)わいわいわい(?!わー?い)|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)aiscream|"
    r"幻(日のヨハネ|ヨハ)|^(?!(.|\n)*(shaman ?king)(.|\n)*$)((.|\n)*\b(genjitsu ?no ?)?"
    r"yohane\b(.|\n)*)|sunshine\sin\sthe\smirror|"
    r"高海\s?千歌|桜内\s?梨子|松浦\s?果南|黒澤\s?(ダイヤ|ルビィ?)|渡辺\s?曜|津島\s?善子|"
    r"国木田\s?花丸|小原\s?鞠莉|"
    r"がんば(ルビ|るび)|(^|[^@])ganbaruby|"
    r"(永久|\beikyuu\s?)hours|"
    r"(?<!\bRT @)saint\s?snow([^a-z]|$)|"
    r"鹿角\s?(理亞|聖良)|"
    # Nijigasaki
    r"虹ヶ咲|ニジガク|(アニ|エイ)ガサキ|(あに|えい)がさき|にじ(よん|ちず)|"
    r"(nij|an|e)igasaki|niji(chizu|gaku|yon)|a・zu・na|qu4rtz|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(diver"
    r" ?diva|r3birth)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"高咲\s?侑|上原\s?歩夢|中須\s?かすみ|桜坂\s?しずく|朝香\s?果林|宮下\s?愛|近江\s?(彼方|遥)|"
    r"優木\s?せつ菜|中川\s?菜々|エマ・?ヴェルデ|天王寺\s?璃奈|三船\s?栞子|ミア・?テイラー|鐘\s?嵐珠|"
    # Love Live! Superstar!!
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)liella(?! kelly)[!！]?|結ヶ丘|yuigaoka|"
    r"5yncri5e!?|kaleidoscore"
    r"|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(?<!i )(?<!to"
    r" )catchu!?(?! later)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"トマカノーテ|tomakanote|スパスタ[3３]期|"
    r"澁谷\s?かのん|唐\s?可可|嵐千\s?砂都|平安名\s?すみれ|葉月\s?恋|桜小路\s?きな子|米女\s?メイ|"
    r"若菜\s?四季|鬼塚\s?(夏美|冬毬)|ウィーン・?マルガレーテ|"
    r"ク[ウゥ]ク[ウゥ]ちゃん?|oninatsu|オニナッツ|"
    r"sunny\s?pas(sion)?(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"sunnypa(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"聖澤悠奈|柊\s?摩央|"
    # Link! Like! Love Live! / Hasunosora
    # リンクラ but not リンクライン or katakana phrases with リンクラ character sequence
    r"(^|[^\u30a1-\u30f6\u30fc])リンクラ(?!イン)|"
    r"hasu\s?no\s?sora|蓮ノ(空|休日)|"
    r"cerise\sbouquet|スリーズブーケ|dollchestra(?!-art)|ドルケストラ|"
    r"mira-cra\spark!?|みらくらぱーく[!！]?|\bkahomegu\b|かほめぐ(♡じぇらーと)?|"
    r"るりのとゆかいなつづりたち|"
    r"乙宗\s?梢|夕霧\s?綴理|藤島\s?慈|日野下\s?花帆|村野\s?さやか|大沢\s?瑠璃乃|百生\s?吟子|"
    r"徒町\s?小鈴|安養寺\s?姫芽|大賀美沙知|"
    # Love Live! Bluebird
    r"いきづらい部|イキヅライブ|"
    # Concerts
    r"異次元フェス|ijigen\sfest?|#llsat_|"
    # Notable community groups
    r"\b(team )?onib(e|ased)\b",
    re.IGNORECASE,
)
SUKUFEST_RE = re.compile(
    r"(^|[^マ])スクフェス(?!札幌|大阪|福岡|神奈川|新潟|仙台|三河|沖縄)"
)
CHARACTER_NAMES = set(
    {
        # μ's
        ("Honoka", "Kou?saka", False),  # First name, Last name, First-Last order only
        ("Eli", "Ayase", False),
        ("Kotori", "Minami", False),
        ("Umi", "Sonoda", False),
        ("Rin", "Hoshizora", False),
        ("Maki", "Nishikino", False),
        ("Nozomi", "Tou?jou?", False),
        ("Hanayo", "Koizumi", False),
        ("Nico", "Yazawa", False),
        # A-RISE
        ("Kira", "Tsubasa", False),
        ("Anju", "Yuu?ki", False),
        ("Erena", "Tou?dou?", False),
        # Aqours
        ("Chika", "Takami", False),
        ("Riko", "Sakurauchi", False),
        ("Kanan", "Matsuu?ra", False),
        ("(Dia|Ruby)", "Kurosawa", False),
        ("You(?!['’])", "Watanabe", False),
        ("Yoshiko", "Tsushima", False),
        ("Hanamaru", "Kunikida", False),
        ("Mari", "Ohara", False),
        # Saint Snow
        ("(Le|Sar)ah", "Kazuno", False),
        # Nijigasaki
        ("Yuu?", "Takasaki", False),
        ("Ayumu", "Uehara", False),
        ("Kasumi", "Nakasu", False),
        ("Shizuku", "Ou?saka", False),
        ("Karin", "Asaka", False),
        ("Ai", "Miyashita", False),
        ("(Kanat|Haruk)a", "Konoe", False),
        ("Setsuna", "Yuu?ki", False),
        ("Nana", "Nakagawa", False),
        ("Emma", "Verde", True),
        ("Rina", "Tennou?ji", False),
        ("Shioriko", "Mifune", False),
        # Mia Taylor included in pattern builder due to so many false positives
        ("Lanzhu", "Zhong", False),
        # Liella
        ("Kanon", "Shibuya", False),
        ("Keke", "Tang", False),
        ("Chisato", "Arashi", False),
        ("Sumire", "Heanna", False),
        ("Ren", "Hazuki", False),
        ("Kinako", "Sakurakoji", False),
        ("Mei", "Yoneme", False),
        ("Shiki", "Wakana", False),
        ("(Natsum|Tomar)i", "Onitsuka", False),
        ("Wien", "Margarete", True),
        # Sunny Passion
        ("Yuu?na", "Hijirisawa", False),
        ("Mao", "Hiiragi", False),
        # Hasunosora
        ("Kozue", "Otomune", False),
        ("Tsuzuri", "Yugiri", False),
        ("Megumi", "Fujishima", False),
        ("Kaho", "Hinoshita", False),
        ("Sayaka", "Murano", False),
        ("Rurino", "Osawa", False),
        ("Ginko", "Momose", False),
        ("Kosuzu", "Kachimachi", False),
        ("Hime", "Anyoji", False),
        ("Sachi", "Ogami", False),
    }
)

EXCLUDE_RE = re.compile(
    # The great "I love live [something]" hoarde
    r"\b(i(['’]d)?|you(['’]ll)?|we( (all|both))?|they|gotta|who|people|s?he|[a-z]{3,}s)"
    r"( ([a-z]{3,}(ing?|ly)|just|al(so|ways)|(st|w)ill|do(es)?|bloody|don['’]t|"
    r"((ha(ve|ppen(ed)?)|used?) t|s|t(o|end t))o|would(v['’]e)?|[a-z]+[a-z] and)\,?)*"
    r"( love)+ live((?! (so(?! far)|and(?! learn)|but)\b)|rs?),?  ?#?\w+\b|"
    # People I/you/etc. love live
    r"people (i|you|they) love live|"
    # Anyone ... love live music?
    r"anyone( .+)? love live music\?|"
    # "love live music" at start of sentence or after "freaking/really/bloody/etc." but
    # not "love live music is"
    r"(^|([^\w ]|[a-z]+(ng?|ly)|bloody ))love live music (?!is )|"
    # "love live music" at end of sentence, "love live music at"
    r" love live music([^\w ]| at\b)|"
    # Words/phrases starting with "love live"
    r"\blove live ("
    # - love live action, love "Live and Let Die" (movie title), love "LIVE and FALL"
    #   (album by Xdinary Heroes)
    r"a(ction|nd (fall|let die))|"
    # - Love Live Italian/within
    r"(italia|withi)n|"
    # - love live laugh/life/local/long/loud (music), "love live love" but not "love live
    #   love wing bell"
    r"l(augh|o(cal|ife|ng|ud( music)?|ve(?! wing bell)))|"
    # - love live oak(s)
    r"oaks?|"
    # - love live service/streaming/streams
    r"s(ervice|tream(ing|s))|"
    # - love live theater/TV
    r"t(heat(er|re)|v)|"
    # - love live tour/your
    r"[ty]our|"
    # - love live bands/gigs/mealworms/performances/shows/sports, "Love Live in/from
    #   Paris" (misspelling of "Lover (Live from Paris)" album by Taylor Swift)
    r"(band|gig|mealworm|performance|s(how|port)|(in|from) pari)s)|"
    # [Artist] - [song name ending with "love"] live
    r"\w+ [\-\u2013] .+ love live\b[^!]|"
    # that love liver (as in body part)
    r"\bthat ([a-z]+[a-z] )?love liver\b|"
    # Words/phrases ending with "love live"
    # - Dangerously/Drunk in Love live, who live in love live (1 John 4:16)
    r"\b(d(angerously|runk)|who live) in love live\b|\b("
    # - does not/doesn't love live [something]
    r"do(es)?( not|n['’]t)|"
    # - Friday I'm In Love live
    r"friday i['’]?m in|"
    # - laugh/let/live/Lexicon of Love live
    r"l(augh|et|ive|exicon of)|"
    # - "life love live" but not "Link Life Love Live"
    r"(?<!link )life|"
    # - mad love live
    r"mad|"
    # - Radical/Rinku Love Live
    r"r(adical|inku)|"
    # - show some/Savage/Stone Love live
    r"s(avage|how some|tone)|"
    # - you are/you're in love live
    r"you( a|['’])re in) love live\b|"
    # perform(s/ed/ing/ance of) ... [song name ending with "Love"] live
    r"perform(ance of|ed|ing|s)? .+ love live($| +(at|[io]n|(in|out)side)\b)|"
    # if you live in/near/around [place name] and love live music/comedy
    r"((you(\s+liv|['’]r)e\s+(in|near|around)\s+.+\s+)?and\s+|[^\w ]\s*)love live"
    r"( (music|comedy)|r)(?! ((i|wa)s)|are)\b|"
    # whether you('re) ... or (just) love live [something]
    r"whether you.+ or (just )?love live |"
    # "love live the" as a typo of "long live the"
    r"(^|[^\w ] *?)love live the (?!school idol|musical)\b|"
    # "love live [something]" as a typo of "long live [something]" or "love love love
    # love [something]", "love liver" at beginning of sentence
    r"(([^\w\s:]+?  ?|^)(love )+liver?(?! (i[ns]|are) )|([^\w\s,:]+?  ?|^)(love"
    r" )+live,)( #?[a-z]+)+ ?([^\w'’ ]|$)|"
    # may your/his/her/their ... love live (on)
    r"\bmay (h(is|er)|(thei|you)r) (.+ )?love live |"
    # may love live in
    r"\bmay love live in\b|"
    # her/his/our/their/who(se) ... (and) love live in/on
    r"(h(er|is)|(ou|thei)r|who(se)?) (([a-z]+[a-z]|.+ and) )?love lives? [io]n\b|"
    # "you(r) love live" before period/comma
    r"\byour? love live[.,]|"
    # # playing [video game title ending with "Love"] live (on/at)
    r"\bplay(ing)? .+ love live (at|on)|"
    # I love Live and Learn (as in Sonic Adventure 2 theme song)
    r"\bi ([a-z]+[a-z] )?love live (&|and) learn|"
    # Love Live (rock music) Festival and its venue and bands
    r"\b(official )?love live festival\b|\blovelivefestival|"
    r"\b((black(pool| ?(lak|vultur)es?))|cancel ?the ?transmission|fugitive|"
    r"darker ?my ?horizon|g(in ?annie|r(a(ham ?oliver|nd ?slam)|eyfox))|"
    r"j(a(nice ?lee|yler)|oan ?of ?arc)|king ?voodoo|m(chale['‘’`]?s|idnite)|nazareth|"
    r"p(an ?tang|hil ?campbell)|r(amblin|e(d ?giant|venant))|screaming ?eagles|"
    r"t(akeaway ?thieve|his ?house ?we ?built|r(oy ?redfern|ucker ?diablo)|ygers)|"
    r"urban ?commandos?|zac ?the ?locust|winter ?gardens)|"
    # "Prophecy x This Love" by Taylor Swift
    r"prophecy x this love|"
    # "No Loss, No Love" by Spiritbox
    r"\bno loss,? no love",
    re.IGNORECASE | re.MULTILINE,
)
NSFW_KEYWORDS_RE = re.compile(
    r"\b(bds&?m|c(ock|um(ming)?\b)|di(ck|ldo)|(futanar|henta)i|n(sfw|ude)|"
    r"p(enis|regnant)|sex\b)",
    re.IGNORECASE,
)

# Prepopulate user list with only @lovelivenews.bsky.social just in case loading from
# file didn't work
LOVELIVENEWS_BSKY_SOCIAL = "did:plc:yfmm2mamtdjxyp4pbvdigpin"
DEDICATED_USERS = set({LOVELIVENEWS_BSKY_SOCIAL})
IGNORE_USERS: set[str] = set()

uri = config.LOVELIVE_URI
dedicated_userlist_uri = config.LOVELIVE_INCLUDE_LIST_URI
ignore_list_uri = config.LOVELIVE_IGNORE_LIST_URI


def make_characters_pattern() -> re.Pattern:
    patterns: list[str] = []
    for name in CHARACTER_NAMES:
        first, last, first_last_only = name
        if not first_last_only:
            patterns.append(f"{last} ?{first}")

        patterns.append(f"{first} ?{last}")

    return re.compile(
        f"(?:^|[^@a-z])(?:{'|'.join(patterns)}|mia taylor)\\b", re.IGNORECASE
    )


CHARACTERS_EN_RE = make_characters_pattern()


def filter(post: dict) -> bool:
    author = post["author"]
    if author in DEDICATED_USERS:
        return True

    if author in IGNORE_USERS:
        return False

    all_texts = "\n".join(get_post_texts(post))
    if not all_texts:
        return False

    return not NSFW_KEYWORDS_RE.search(all_texts) and any(
        (
            LOVELIVE_NAME_EN_RE.search(all_texts) and not EXCLUDE_RE.search(all_texts),
            SUKUFEST_RE.search(all_texts) and "scrum" not in all_texts.lower(),
            LOVELIVE_RE.search(all_texts),
            CHARACTERS_EN_RE.search(all_texts),
        )
    )
