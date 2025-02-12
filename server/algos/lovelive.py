import re

from server import config
from server.algos._base import get_post_texts

LOVELIVE_NAME_EN_RE = re.compile(
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)love ?live[!\s]*", re.IGNORECASE
)
LOVELIVE_RE = re.compile(
    r"love\s?live[!\s]*(blue ?bird|days|s(ky|taff|u(nshine|per ?star)))|"
    r"(thank you|likes) love ?live\b|#lovelive_|"
    r"ラブライ(ブ[!！\s]*(サンシャイン|スーパースター)?|バー)|スクールアイドル|"
    r"(?<!middle )(?<!high )school\s?idol(s?\b|\s?((festiv|music)al|project))?|"
    # Games
    r"\bl(l|ove ?live ?)sif2?\b|\b(ll)?sif(as\b|\s?all[\s\-]?stars)|puchiguru|"
    # ぷちぐる but not ぷちぐるみ
    r"ぷちぐる[^み]|"
    # スクフェス/スクスタ/スクミュ but not words with マスク/スタンド/スタンプ/スタイル/スタッフ
    r"(^|[^マ])スク(フェス|スタ(?!ン[ドプ]|イル|ッフ)|ミュ)|"
    # Love Live! School Idol Project
    # NOTE: Printemps, lily white, BiBi not included due to too many false positives
    r"音ノ木坂?|otonokizaka|[μµ]['’‘`´′]s|にこりんぱな|nicorinpana|"
    r"高坂\s?穂乃果|honoka\s?kou?saka|kou?saka\s?honoka|"
    r"絢瀬\s?絵里|ayase\s?eli|eli\s?ayase|エリーチカ|\belichika\b|"
    r"南\s?ことり|minami\s?kotori|kotori\s?minami|kotobirb|"
    r"園田\s?海未|sonoda\s?umi|umi\s?sonoda|"
    r"星空\s?凛|hoshizora\s?rin|rin\s?hoshizora|金曜凛ちゃんりんりんりん|"
    r"西木野\s?真姫|nishikino\s?maki|maki\s?nishikino|"
    r"東條\s?希|tou?jou?\s?nozomi|nozomi\s?tou?jou?|"
    r"小泉\s?花陽|koizumi\s?hanayo|hanayo\s?koizumi|火曜日かよちゃん|"
    r"矢澤\s?にこ|yazawa\s?nico|nico\s?yazawa|nico\snico\sni+\b|#niconiconi+\b|"
    r"snow\s?halation|"
    r"(^|[^a-z\u00C0-\u024F\u1E00-\u1EFF\-])a[-\u2010]rise[^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|"
    r"綺羅\s?ツバサ|kira\s?tsubasa|tsubasa\s?kira|"
    r"優木\s?あんじゅ|yuu?ki\s?anju|anju\s?yuu?ki|"
    r"統堂\s?英玲奈|tou?dou?\s?erena|\berena\s?tou?dou?\b|"
    # Love Live! Sunshine!!
    # NOTE: AZALEA not included due to too many false positives
    r"浦の星女?|uranohoshi|aq(ou|uo)rs|cyaron!?|guilty\s?kiss|"
    # YYY (You, Yoshiko/Yohane, RubY)
    r"(?<!わい)(?<!わーい)わいわいわい(?!わー?い)|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)aiscream|"
    r"幻(日のヨハネ|ヨハ)|\b(genjitsu ?no ?)?yohane\b(?!(.|\n)+shaman ?king)|"
    r"sunshine\sin\sthe\smirror|"
    r"高海\s?千歌|takami\s?chika|chika\s?takami|"
    r"桜内\s?梨子|sakurauchi\s?riko|riko\s?sakurauchi|"
    r"松浦\s?果南|matsuu?ra\s?kanan|kanan\s?matsuu?ra|"
    r"黒澤\s?(ダイヤ|ルビィ?)|kurosawa\s?(dia|ruby)|(dia|ruby)\s?kurosawa|"
    r"がんば(ルビ|るび)|ganbaruby|"
    r"渡辺\s?曜|watanabe\s?you|you\s?watanabe|ヨーソロー?|ﾖｰｿﾛｰ?|\byousoro|"
    r"津島\s?善子|tsushima\s?yoshiko|yoshiko\s?tsushima|堕天使ヨハネ|"
    r"国木田\s?花丸|kunikida\s?hanamaru|hanamaru\s?kunikida|\bzuramaru|"
    r"小原\s?鞠莉|ohara\s?mari|mari\s?ohara|"
    r"(永久|\beikyuu\s?)hours|"
    r"(?<!\bRT @)saint\s?snow|"
    r"鹿角\s?(理亞|聖良)|kazuno\s?(le|sar)ah|(le|sar)ah\s?kazuno|"
    # Nijigasaki
    r"虹ヶ咲|ニジガク|(アニ|エイ)ガサキ|(あに|えい)がさき|にじよん|"
    r"(nij|an|e)igasaki|niji(gaku|yon)|a・zu・na|qu4rtz|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(diver"
    r" ?diva|r3birth)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"高咲\s?侑|takasaki\s?yuu?|yuu?\s?takasaki|"
    r"上原\s?歩夢|uehara\s?ayumu|ayumu\s?uehara|"
    r"中須\s?かすみ|nakasu\s?kasumi|kasumi\s?nakasu|"
    r"桜坂\s?しずく|ou?saka\s?shizuku|shizuku\s?ou?saka|"
    r"朝香\s?果林|asaka\s?karin|karin\s?asaka|"
    r"宮下\s?愛|miyashita\s?ai|ai\s?miyashita|"
    r"近江\s?(彼方|遥)|konoe\s?(kanat|haruk)a|(kanat|haruk)a\s?konoe|"
    r"優木\s?せつ菜|yuu?ki\s?setsuna|setsuna\s?yuu?ki|"
    r"中川\s?菜々|nakagawa\s?nana|nana\s?nakagawa|"
    r"エマ・?ヴェルデ|emma\s?verde|"
    r"天王寺\s?璃奈|tennou?ji\s?rina|rina\s?tennou?ji|"
    r"三船\s?栞子|mifune\s?shioriko|shioriko\s?mifune|"
    r"ミア・?テイラー|\bmia\staylor\b|"
    r"鐘\s?嵐珠|lanzhu\s?zhong|zhong\s?lanzhu|"
    # Love Live! Superstar!!
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)liella(?! kelly)[!！]?|結ヶ丘|yuigaoka|"
    r"5yncri5e!?|kaleidoscore"
    r"|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(?<!i )(?<!to"
    r" )catchu!?(?! later)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"トマカノーテ|tomakanote|スパスタ[3３]期|"
    r"澁谷\s?かのん|shibuya\s?kanon|kanon\s?shibuya|"
    r"唐\s?可可|ク[ウゥ]ク[ウゥ]ちゃん?|\btang\s?keke|\bkeke\s?tang|"
    r"嵐千\s?砂都|arashi\s?chisato|chisato\s?arashi|"
    r"平安名\s?すみれ|heanna\s?sumire|sumire\s?heanna|"
    r"葉月\s?恋|\bhazuki\s?ren\b|ren\s?hazuki|"
    r"桜小路\s?きな子|sakurakoji\s?kinako|kinako\s?sakurakoji|"
    r"米女\s?メイ|yoneme\s?mei|mei\s?yoneme|"
    r"若菜\s?四季|wakana\s?shiki|shiki\s?wakana|"
    r"鬼塚\s?(夏美|冬毬)|onitsuka\s?(natsum|tomar)i|(natsum|tomar)i\s?onitsuka|"
    r"oninatsu|オニナッツ|"
    r"ウィーン・?マルガレーテ|\bwien\s?margarete\b|"
    r"sunny\s?pas(sion)?(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"sunnypa(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"聖澤悠奈|hijirisawa\s?yuu?na|yuu?na\s?hijirisawa|"
    r"柊\s?摩央|hiiragi\s?mao|mao\s?hiiragi|"
    # Link! Like! Love Live! / Hasunosora
    # リンクラ but not スプリンクラー/シュリンクラップ or words with ソブリン/クラウド/ドリンク/
    # ラウンジ/ライン/クラブ
    r"(^|[^ドキ])(?<!スプ|ソブ|シュ)リンクラ(?!ウ(ド|ンジ)|イン|ップ|ブ|フト)|"
    r"hasu\s?no\s?sora|蓮ノ(空|休日)|"
    r"cerise\sbouquet|スリーズブーケ|dollchestra|ドルケストラ|"
    r"mira-cra\spark!?|みらくらぱーく[!！]?|\bkahomegu\b|かほめぐ(♡じぇらーと)?|"
    r"るりのとゆかいなつづりたち|"
    r"乙宗\s?梢|otomune\s?kozue|kozue\s?otomune|"
    r"夕霧\s?綴理|yugiri\s?tsuzuri|tsuzuri\s?yugiri|"
    r"藤島\s?慈|fujishima\s?megumi|megumi\s?fujishima|"
    r"日野下\s?花帆|hinoshita\s?kaho|kaho\s?hinoshita|"
    r"村野\s?さやか|murano\s?sayaka|sayaka\s?murano|"
    r"大沢\s?瑠璃乃|osawa\s?rurino|rurino\s?osawa|"
    r"百生\s?吟子|momose\s?ginko|ginko\s?momose|"
    r"徒町\s?小鈴|kachimachi\s?kosuzu|kosuzu\s?kachimachi|"
    r"安養寺\s?姫芽|anyoji\s?hime|\bhime\s?anyoji\b|"
    r"大賀美沙知|ogami\s?sachi|sachi\s?ogami|"
    # Love Live! Bluebird
    r"いきづらい部|イキヅライブ|"
    # Concerts
    r"異次元フェス|ijigen\sfest?|#llsat_|"
    # Notable community groups
    r"\b(team )?onib(e|ased)\b",
    re.IGNORECASE,
)
EXCLUDE_RE = re.compile(
    # The great "I love live [something]" hoarde
    r"\b(i(['’]d)?|you(['’]ll)?|we( (all|both))?|they|gotta|who|people|s?he|[a-z]{3,}s)"
    r"( ([a-z]+(ing?|ly)|just|al(so|ways)|(st|w)ill|((have|used?) t|s|t(o|end t))o|"
    r"do(es)?|bloody|would(v['’]e)?|don['’]t|[a-z]+[a-z] and)\,?)*( love)+ live"
    r"(?! (so(?! far)|and(?! learn)|but)\b)(-|,?  ?#?)?\w+\b|"
    # People I/you/etc. love live
    r"people (i|you|they) love live|"
    # Anyone ... love live music?
    r"anyone( .+)? love live music\?|"
    # love lives/Liverpool/lived/lively/livelihood/Livejournal/LiveView/Livewire/Live2D,
    # love live life/love/local
    r"love\s?live(2?d|journal|l(y|ihood)|rpool|s|view|wire|"
    r" ?l(ife|o(cal|ve(?! wing bell))))|"
    # #lovelivemusic, lovelivegcw.com, loveliveitalian.com
    r"\blovelive(music|gcw|italian)|"
    # "love live music" at start of sentence but not "love live music is"
    r"(^|[^\w ] )love live music (?!is )|"
    # "love live music" at end of sentence
    r" love live music[^\w ]|"
    # [Artist] - [song name ending with "love"] live
    r"\w+ [\-\u2013] .+ love live\b[^!]|"
    # that love liver (as in body part)
    r"\bthat ([a-z]+[a-z] )?love liver\b|"
    # Dangerously/Drunk in Love, who live in love (1 John 4:16)
    r"\b(d(angerously|runk)|who live) in love\b|"
    # laugh/let/live/radical/you are in/life/performing .../savage/mad/Friday I'm In/
    # Rinku Love Live
    r"\b(l(augh|et|ive)|r(adical|inku)|you( a|['’])re in|(?<!link )life|savage|mad|"
    r"friday i['’]?m in|perform(ing|s)( \w+)+) love live\b|"
    # if you live in/near/around [place name] and love live music/comedy
    r"((you(\s+liv|['’]r)e\s+(in|near|around)\s+.+\s+)?and\s+|[^\w ]\s*)love live"
    r"( (music|comedy)|r)(?! ((i|wa)s)|are)\b|"
    # whether you('re) ... or (just) love live [something]
    r"whether you.+ or (just )?love live |"
    # love live(-)action/streaming
    r"\blove live[ \-](action|streaming)\b|"
    # "love live the" as a typo of "long live the"
    r"(^|[^\w ] *?)love live the (?!school idol|musical)\b|"
    # "love live [something]" as a typo of "long live [something]" or "love love love
    # love [something]"
    r"([^\w\s]+?  ?|^)(love )+liver?( #?[a-z]+[a-z]){1,3} ?([^\w ]|$)|"
    # love live laugh/service/theater/shows/sports/performances/TV/bands/oak(s)/
    # mealworms/Italian/your [something], "Live and Let Die" (movie title),
    # Love Live in/from Paris (misspelling of "Lover (Live From Paris)" album by
    # Taylor Swift)
    r"\blove live (laugh|service|t(heat(er|re)|v)|oaks?|your|italian|and let die|"
    r"(band|s(how|port)|mealworm|performance|(in|from) pari)s)|"
    # may your/his/her/their ... love live (on)
    r"\bmay (h(is|er)|(thei|you)r) (.+ )?love live |"
    # "you(r) love live" before period/comma
    r"\byour? love live[.,]|"
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
    r"prophecy x this love",
    re.IGNORECASE | re.MULTILINE,
)
NSFW_KEYWORDS_RE = re.compile(
    r"\b(hentai|futanari|p(enis|orn)|dildo|n(sfw|ude)|bds&?m|cum(ming)?\b)",
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
            LOVELIVE_RE.search(all_texts),
        )
    )
