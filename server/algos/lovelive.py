import csv
import re
from pathlib import Path, PurePath

from click import style

from server import config
from server.algos._base import get_post_texts
from server.logger import logger

LOVELIVE_NAME_EN_RE = re.compile(
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)love ?live[!\s]*", re.IGNORECASE
)
LOVELIVE_RE = re.compile(
    r"love\s?live[!\s]*(s(ky|taff|u(nshine|perstar)))|thank you love ?live|"
    r"#lovelive_|ラブライブ[!！\s]*(サンシャイン|スーパースター)?|"
    r"スクールアイドル|school\s?idol(s?\b|\s?((festiv|music)al|project))?|"
    # Games
    r"\bllsif\b|[^マ]スク(フェス|スタ(?!ンド))|\b(ll)?sif(as\b|\s?all[\s\-]?stars)|"
    r"ぷちぐる|puchiguru|"
    # Love Live! School Idol Project
    r"音ノ木坂|otonokizaka|[μµ]['’`]s|にこりんぱな|nicorinpana|"
    r"高坂\s?穂乃果|honoka\s?kou?saka|kou?saka\s?honoka|"
    r"絢瀬\s?絵里|ayase\s?eli|eli\s?ayase|\belichika\b|"
    r"南\s?ことり|minami\s?kotori|kotori\s?minami|kotobirb|"
    r"園田\s?海未|sonoda\s?umi|umi\s?sonoda|"
    r"星空\s?凛|hoshizora\s?rin|rin\s?hoshizora|金曜凛ちゃんりんりんりん|"
    r"西木野\s?真姫|nishikino\s?maki|maki\s?nishikino|"
    r"東條\s?希|tou?jou?\s?nozomi|nozomi\s?tou?jou?|"
    r"小泉\s?花陽|koizumi\s?hanayo|hanayo\s?koizumi|火曜日かよちゃん|"
    r"矢澤\s?にこ|yazawa\s?nico|nico\s?yazawa|nico\snico\sni+\b|#niconiconi+\b|"
    r"snow\s?halation|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|\b)a[-\u2010]rise[^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|"
    r"綺羅\s?ツバサ|kira\s?tsubasa|tsubasa\s?kira|"
    r"優木\s?あんじゅ|yuu?ki\s?anju|anju\s?yuu?ki|"
    r"統堂\s?英玲奈|tou?dou?\s?erena|\berena\s?tou?dou?\b|"
    # Love Live! Sunshine!!
    r"浦の星女|uranohoshi|aq(ou|uo)rs|cyaron!|guilty\s?kiss|わいわいわい|\baiscream|"
    r"幻日のヨハネ|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(genjitsu\s?no\s?)?yohane\b|"
    r"sunshine\sin\sthe\smirror|"
    r"高海\s?千歌|takami\s?chika|chika\s?takami|"
    r"桜内\s?梨子|sakurauchi\s?riko|riko\s?sakurauchi|"
    r"松浦\s?果南|matsuu?ra\s?kanan|kanan\s?matsuu?ra|"
    r"黒澤\s?(ダイヤ|ルビィ?)|kurosawa\s?(dia|ruby)|(dia|ruby)\s?kurosawa|"
    r"がんば(ルビ|るび)|ganbaruby|"
    r"渡辺\s?曜|watanabe\s?you|you\s?watanabe|"
    r"ヨーソロー|ﾖｰｿﾛｰ|\byousoro|"
    r"津島\s?善子|tsushima\s?yoshiko|yoshiko\s?tsushima|堕天使ヨハネ|"
    r"国木田\s?花丸|kunikida\s?hanamaru|hanamaru\s?kunikida|zuramaru|"
    r"小原\s?鞠莉|ohara\s?mari|mari\s?ohara|"
    r"(永久|\beikyuu\s?)hours|"
    r"(?<!\bRT @)saint\s?snow|"
    r"鹿角\s?(理亞|聖良)|kazuno\s?(le|sar)ah|(le|sar)ah\s?kazuno|"
    # Nijigasaki
    r"虹ヶ咲|ニジガク|にじよん|niji(ga(saki|ku)|yon)|"
    r"a・zu・na|qu4rtz|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)diverdiva|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)r3birth|"
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
    r"ミア・?テイラー|\bmia\s?taylor(?!19)\b|"
    r"鐘\s?嵐珠|lanzhu\s?zhong|zhong\s?lanzhu|"
    # Love Live! Superstar!!
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)liella[!！]?|結ヶ丘|yuigaoka|"
    r"5yncri5e!|catchu!|kaleidoscore|tomakanote|スパスタ[3３]期|"
    r"澁谷\s?かのん|shibuya\s?kanon|kanon\s?shibuya|"
    r"唐\s?可可|ク[ウゥ]ク[ウゥ]ちゃん|\btang\s?keke|\bkeke\s?tang|"
    r"嵐千\s?砂都|arashi\s?chisato|chisato\s?arashi|"
    r"平安名\s?すみれ|heanna\s?sumire|sumire\s?heanna|"
    r"葉月\s?恋|hazuki\s?ren|ren\s?hazuki|"
    r"桜小路\s?きな子|sakurakoji\s?kinako|kinako\s?sakurakoji|"
    r"米女\s?メイ|yoneme\s?mei|mei\s?yoneme|"
    r"若菜\s?四季|wakana\s?shiki|shiki\s?wakana|"
    r"鬼塚\s?(夏美|冬毬)|onitsuka\s?(natsum|tomar)i|(natsum|tomar)i\s?onitsuka|oninatsu|"
    r"ウィーン・?マルガレーテ|\bwien\s?margarete\b|"
    r"sunny\s?pas(sion)?(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"sunnypa(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"聖澤悠奈|hijirisawa\s?yuu?na|yuu?na\s?hijirisawa|"
    r"柊\s?摩央|hiiragi\s?mao|mao\s?hiiragi|"
    # Link! Like! Love Live!! / Hasunosora
    r"(?<!スプ|ソブ)リンクラ(?!ウンジ)|link[!！]\s?like[!！]\s?love\s?live|"
    r"hasu\s?no\s?sora|蓮ノ空|"
    r"cerise\sbouquet|dollchestra|mira-cra\spark!|みらくらぱーく[!！]|"
    r"乙宗\s?梢|otomune\s?kozue|kozue\s?otomune|"
    r"夕霧\s?綴理|yugiri\s?tsuzuri|tsuzuri\s?yugiri|"
    r"藤島\s?慈|fujishima\s?megumi|megumi\s?fujishima|"
    r"日野下\s?花帆|hinoshita\s?kaho|kaho\s?hinoshita|"
    r"村野\s?さやか|murano\s?sayaka|sayaka\s?murano|"
    r"大沢\s?瑠璃乃|osawa\s?rurino|rurino\s?osawa|"
    r"百生\s?吟子|momose\s?ginko|ginko\s?momose|"
    r"徒町\s?小鈴|kachimachi\s?kosuzu|kosuzu\s?kachimachi|"
    r"安養寺\s?姫芽|anyoji\s?hime|hime\s?anyoji|"
    # Concerts
    r"異次元フェス|ijigen\sfest?",
    re.IGNORECASE,
)
EXCLUDE_RE = re.compile(
    r"\b(i(['’]d)?|you|we( (all|both))?|they|gotta|who|people)"
    r"( ([a-z]+(ing?|ly)|do|just|al(so|ways)|still|t(o|end"
    r" t)o|bloody|would(v['’]e)?)\,?)*( love)+ liver?|"
    r"love\s?live(s|rpool|d|ly| ?life)|\bthat (.\s)?love liver\b|"
    r"\b(d(angerously|runk)|who live) in love\b|\blovelivemusic|"
    r"((you(\s+liv|['’]r)e\s+(in|near|around)\s+.+\s+)?and\s+|[^\w ]\s*)love live"
    r"( (music|comedy)|r)(?! ((i|wa)s)|are)\b|\b(l(augh|et)|radical) love live\b|"
    r"(^|[^\w ]) *love live the (?!school idol)\b|"
    r"\blove live (service|t(heat(er|re)|v)|(band|show)s)|\byour love live[.,]|"
    r"\blove live[ \-](action|streaming)\b",
    re.IGNORECASE | re.MULTILINE,
)
NSFW_KEYWORDS_RE = re.compile("hentai|futanari|penis|dildo|#コイカツ", re.IGNORECASE)

# Prepopulate user list with only @lovelivenews.bsky.social just in case loading from
# file didn't work
LOVELIVENEWS_BSKY_SOCIAL = "did:plc:yfmm2mamtdjxyp4pbvdigpin"
DEDICATED_USERS = set({LOVELIVENEWS_BSKY_SOCIAL})

uri = config.LOVELIVE_URI


def _load_user_list():
    module_dir = PurePath(__file__).parent
    user_list_path = Path(*module_dir.parts[:-2], "lists", "lovelive_users.csv")

    try:
        with user_list_path.open() as f:
            reader = csv.DictReader(f)
            users_initial_count = len(DEDICATED_USERS)
            for row in reader:
                user_did = row.get("did", "")
                if user_did.startswith("did:"):
                    DEDICATED_USERS.add(row["did"])

            added_count = len(DEDICATED_USERS) - users_initial_count
            if added_count > 0:
                logger.debug(
                    "Loaded DIDs of dedicated LoveLive accounts: %d", added_count
                )
    except Exception:  # noqa: PIE786
        logger.warning(
            style(
                "Failed to load dedicated LoveLive accounts list",
                fg="yellow",
                bold=True,
            ),
            exc_info=True,
        )


def filter(post: dict) -> bool:
    all_texts = "\n".join(get_post_texts(post))
    if not all_texts:
        return False

    return post["author"] in DEDICATED_USERS or (
        any(
            (
                LOVELIVE_NAME_EN_RE.search(all_texts)
                and not EXCLUDE_RE.search(all_texts),
                LOVELIVE_RE.search(all_texts),
            )
        )
        and not NSFW_KEYWORDS_RE.search(all_texts)
    )


_load_user_list()
