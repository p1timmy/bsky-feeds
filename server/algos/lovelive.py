import re
from collections.abc import Iterable
from datetime import datetime
from typing import Optional

from atproto_client.models.app.bsky.feed.post import Record

from server import config
from server.database import Feed, Post

LOVELIVE_NAME_EN_RE = re.compile(r"love\s?live[!\s]*", re.IGNORECASE)
LOVELIVE_RE = re.compile(
    r"love\s?live[!\s]*(s(ky|u(nshine|perstar)))|"
    r"ラブライブ[!！\s]*(サンシャイン|スーパースター)?|スパスタ(3|３)期|"
    r"幻日のヨハネ|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(genjitsu\s?no\s?)?yohane\b|"
    r"sunshine\sin\sthe\smirror|"
    r"[μµ]['’]s|aq(ou|uo)rs|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)liella[!！]?|"
    r"hasu\s?no\s?sora|蓮ノ空|"
    r"虹ヶ咲|ニジガク|にじよん|niji(ga(saki|ku)|yon)|"
    r"スクールアイドル|school\s?idol(\s?((festiv|music)al|project))?|"
    r"llsif|スク(フェス|スタ)|(ll)?sif(as\b|\s?all\s?stars)|"
    r"リンクラ|link[!！]\s?like[!！]\s?love\s?live|ぷちぐる|puchiguru|"
    r"cyaron!|guilty\s?kiss|"
    r"a・zu・na|qu4rtz|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)diverdiva|r3birth|"
    r"5yncri5e!|catchu!|kaleidoscore|tomakanote|"
    r"cerise\sbouquet|dollchestra|mira-cra\spark!|"
    r"にこりんぱな|nicorinpana|わいわいわい|aiscream|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|\b)a[-\u2010]rise[^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|"
    r"saint\s?snow|sunny\s?pas(sion)?(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"sunnypa(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"音ノ木坂|otonokizaka|浦の星女|uranohoshi|結ヶ丘|yuigaoka|"
    r"高坂\s?穂乃果|honoka\s?kou?saka|kou?saka\s?honoka|"
    r"絢瀬\s?絵里|ayase\s?eli|eli\s?ayase|elichika|"
    r"南\s?ことり|minami\s?kotori|kotori\s?minami|kotobirb|"
    r"園田\s?海未|sonoda\s?umi|umi\s?sonoda|"
    r"星空\s?凛|hoshizora\s?rin|rin\s?hoshizora|金曜凛ちゃんりんりんりん|"
    r"西木野\s?真姫|nishikino\s?maki|maki\s?nishikino|"
    r"東條\s?希|tou?jou?\s?nozomi|nozomi\s?tou?jou?|"
    r"小泉\s?花陽|koizumi\s?hanayo|hanayo\s?koizumi|火曜日かよちゃん|"
    r"矢澤\s?にこ|yazawa\s?nico|nico\s?yazawa|nico\s?nico\s?ni+\b|"
    r"綺羅\s?ツバサ|kira\s?tsubasa|tsubasa\s?kira|"
    r"優木\s?あんじゅ|yuu?ki\s?anju|anju\s?yuu?ki|"
    r"統堂\s?英玲奈|tou?dou?\s?erena|erena\s?tou?dou?|"
    r"高海\s?千歌|takami\s?chika|chika\s?takami|"
    r"桜内\s?梨子|sakurauchi\s?riko|riko\s?sakurauchi|"
    r"松浦\s?果南|matsuu?ra\s?kanan|kanan\s?matsuu?ra|"
    r"黒澤\s?(ダイヤ|ルビ)|kurosawa\s?(dia|ruby)|(dia|ruby)\s?kurosawa|"
    r"渡辺\s?曜|watanabe\s?you|you\s?watanabe|ヨーソロー[!！]|"
    r"津島\s?善子tsushima\s?yoshiko|yoshiko\s?tsushima|堕天使ヨハネ|"
    r"国木田\s?花丸|kunikida\s?hanamaru|hanamaru\s?kunikida|zuramaru|"
    r"小原\s?鞠莉|ohara\s?mari|mari\s?ohara|"
    r"鹿角\s?(理亞|聖良)|kazuno\s?(le|sar)ah|(le|sar)ah\s?kazuno|"
    r"高咲\s?侑|takasaki\s?yuu?|yuu?\s?takasaki|"
    r"上原\s?歩夢|uehara\s?ayumu|ayumu\s?uehara|"
    r"中須\s?かすみ|nakasu\s?kasumi|kasumi\s?nakasu|"
    r"桜坂\s?しずく|ou?saka\s?shizuku|shizuku\s?ou?saka|"
    r"朝香\s?果林|asaka\s?karin|karin\s?asaka|"
    r"宮下\s?愛|miyashita\s?ai|ai\s?miyashita|"
    r"近江\s?(彼方|遥)|konoe\s?(kanat|haruk)a|(kanat|haruk)a\s?konoe|"
    r"優木\s?せつ菜|yuu?ki\s?setsuna|setsuna\s?yuu?ki|"
    r"中川\s?菜々|nakagawa\s?nana|nana\s?nakagawa|"
    r"エマ・ヴェルデ|emma\s?verde|"
    r"天王寺\s?璃奈|tennou?ji\s?rina|rina\s?tennou?ji|"
    r"三船\s?栞子|mifune\s?shioriko|shioriko\s?mifune|"
    r"ミア・テイラー|mia\s?taylor|"
    r"鐘\s?嵐珠|lanzhu\s?zhong|"
    r"澁谷\s?かのん|shibuya\s?kanon|kanon\s?shibuya|"
    r"唐\s?可可|ク[ウゥ]ク[ウゥ]ちゃん|\btang\s?keke|\bkeke\s?tang|"
    r"嵐千\s?砂都|arashi\s?chisato|chisato\s?arashi|"
    r"平安名\s?すみれ|heanna\s?sumire|sumire\s?heanna|"
    r"葉月\s?恋|hazuki\s?ren|ren\s?hazuki|"
    r"桜小路\s?きな子|sakurakoji\s?kinako|kinako\s?sakurakoji|"
    r"米女\s?メイ|yoneme\s?mei|mei\s?yoneme|"
    r"若菜\s?四季|wakana\s?shiki|shiki\s?wakana|"
    r"鬼塚\s?(夏美|冬毬)|onitsuka\s?(natsum|tomar)i|(natsum|tomar)i\s?onitsuka|oninatsu|"
    r"ウィーン・マルガレーテ|wien\s?margarete|"
    r"聖澤悠奈|hijirisawa\s?yuu?na|yuu?na\s?hijirisawa|"
    r"柊\s?摩央|hiiragi\s?mao|mao\s?hiiragi|"
    r"乙宗\s?梢|otomune\s?kozue|kozue\s?otomune|"
    r"夕霧\s?綴理|yugiri\s?tsuzuri|tsuzuri\s?yugiri|"
    r"藤島\s?慈|fujishima\s?megumi|megumi\s?fujishima|"
    r"日野下\s?花帆|hinoshita\s?kaho|kaho\s?hinoshita|"
    r"村野\s?さやか|murano\s?sayaka|sayaka\s?murano|"
    r"大沢\s?瑠璃乃|osawa\s?ruino|ruino\s?osawa|"
    r"百生\s?吟子|momose\s?ginko|ginko\s?momose|"
    r"徒町\s?小鈴|kachimachi\s?kosuzu|kosuzu\s?kachimachi|"
    r"安養寺\s?姫芽|anyoji\s?hime|hime\s?anyoji|"
    r"snow\s?halation",
    re.IGNORECASE,
)
EXCLUDE_RE = re.compile(
    r"\b(i|you|we|they)( [a-z]+(ing?|ly))? love live|"
    r"love\s?live(s|rpool|d|ly)|\bthat\s(.\s)?love liver\b|"
    r"\b(d(angerously|runk)|who live) in love\b|"
    r"\blove live (music|service|theater|shows|tv)|"
    r"\blove live[\s\-](action|streaming)\b",
    re.IGNORECASE,
)
NSFW_KEYWORDS_RE = re.compile(
    "hentai|futanari|breasts?|penis|dildo|#コイカツ", re.IGNORECASE
)
LOVELIVENEWS_BSKY_SOCIAL = "did:plc:yfmm2mamtdjxyp4pbvdigpin"

uri = config.LOVELIVE_URI
CURSOR_EOF = "eof"


# TODO: move to common module
def handler(cursor: Optional[str], limit: int, feed_uri: str) -> dict:
    posts = (
        Post.select()
        .join(Feed.posts.get_through_model())
        .join(Feed)
        .where(Feed.uri == feed_uri)
        .order_by(Post.cid.desc())
        .order_by(Post.indexed_at.desc())
        .limit(limit)
    )

    if cursor:
        if cursor == CURSOR_EOF:
            return {
                "cursor": CURSOR_EOF,
                "feed": [],
            }

        cursor_parts = cursor.split("::")
        if len(cursor_parts) != 2:
            raise ValueError("Malformed cursor")

        indexed_at, cid = cursor_parts
        indexed_at = datetime.fromtimestamp(int(indexed_at) / 1000)
        posts: Iterable[Post] = posts.where(
            ((Post.indexed_at == indexed_at) & (Post.cid < cid))
            | (Post.indexed_at < indexed_at)
        )

    feed = [{"post": post.uri} for post in posts]

    cursor = CURSOR_EOF
    if posts:
        last_post: Post = posts[-1]
        cursor = f"{int(last_post.indexed_at.timestamp() * 1000)}::{last_post.cid}"

    return {
        "cursor": cursor,
        "feed": feed,
    }


# TODO: scan link URLs/embeds
def filter(post: dict) -> bool:
    record: Record = post["record"]
    texts: list[str] = []
    if record.text:  # some posts may not have any text at all
        texts.append(record.text)

    # Get alt text from images
    if record.embed:
        imagelist: Optional[Iterable] = getattr(record.embed, "images", None)
        if imagelist:
            for image in imagelist:
                if image.alt:
                    texts.append(image.alt)

    all_texts = "\n".join(texts)
    if not all_texts:
        return False

    return post["author"] == LOVELIVENEWS_BSKY_SOCIAL or (
        any(
            (
                LOVELIVE_NAME_EN_RE.search(all_texts)
                and not EXCLUDE_RE.search(all_texts),
                LOVELIVE_RE.search(all_texts),
            )
        )
        and not NSFW_KEYWORDS_RE.search(all_texts)
    )
