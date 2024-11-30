import re
from collections.abc import Iterable
from datetime import datetime
from typing import Optional

from atproto_client.models.app.bsky.feed.post import Record

from server import config
from server.database import Feed, Post

LOVELIVE_NAME_EN_RE = re.compile(
    r"love\s?live[!\s]*(su(nshine|perstar))?", re.IGNORECASE
)
LOVELIVE_RE = re.compile(
    r"""
ラブライブ[!！\s]*(サンシャイン|スーパースター)|幻日のヨハネ|
[μµ]['’]s|aq(ou|uo)rs|虹ヶ咲|ニジガク|にじよん|niji(ga(saki|ku)|yon)|\bliella\b|hasu\s?no\s?sora|蓮ノ空|
スクールアイドル|school\s?idol\s?((festiv|music)al|project)|llsif|スク(フェス|スタ)|(ll)?sif\s?all\s?stars|リンクラ|link[!！]\s?like[!！]|ぷちぐる|puchiguru
cyaron!|guilty\skiss|\ba・zu・na\b|\bqu4rtz\b|diverdiva|\br3birth\b|5yncri5e!|catchu!|\bkaleidoscore\b|\btomakanote\b|\bcerise\sbouquet|\bdollchestra\b|mira-cra\spark!|
\ba\-rise\b|saint\s?snow|sunny\s?passion|
高坂\s?穂乃果|honoka\s?kou?saka|kou?saka\s?honoka|
絢瀬\s?絵里|ayase\s?eli|eli\s?ayase|
南\s?ことり|minami\s?kotori|kotori\s?minami|
園田\s?海未|sonoda\s?umi|umi\s?sonoda|
星空\s?凛|hoshizora\s?rin|rin\s?hoshizora|
西木野\s?真姫|nishikino\s?maki|maki\s?nishikino|
東條\s?希|tou?jou?\s?nozomi|nozomi\s?tou?jou?|
小泉\s?花陽|koizumi\s?hanayo|hanayo\s?koizumi|
矢澤\s?にこ|yazawa\s?nico|nico\s?yazawa|nico\s?nico\s?ni|
高海\s?千歌|takami\s?chika|chika\s?takami|
桜内\s?梨子|sakurauchi\s?riko|riko\s?sakurauchi|
松浦\s?果南|matsuu?ra\s?kanan|kanan\s?matsuu?ra|
黒澤\s?(ダイヤ|ルビ)|kurosawa\s?(dia|ruby)|(dia|ruby)\s?kurosawa|
渡辺\s?曜|watanabe\s?you|you\s?watanabe|ヨーソロー[!！]|
津島\s?善子tsushima\s?yoshiko|yoshiko\s?tsushima|堕天使ヨハネ|yohane|
国木田\s?花丸|kunikida\s?hanamaru|hanamaru\s?kunikida|zuramaru|
小原\s?鞠莉|ohara\s?mari|mari\s?ohara|
鹿角\s?(理亞|聖良)|kazuno\s?(le|sar)ah|(le|sar)ah\s?kazuno|
高咲\s?侑|takasaki\s?yuu?|yuu?\s?takasaki|
上原\s?歩夢|uehara\s?ayumu|ayumu\s?uehara|
中須\s?かすみ|nakasu\s?kasumi|kasumi\s?nakasu|
桜坂\s?しずく|ou?saka\s?shizuku|shizuku\s?ou?saka|
朝香\s?果林|asaka\s?karin|karin\s?asaka|
宮下\s?愛|miyashita\s?ai|ai\s?miyashita|
近江\s?(彼方|遥)|konoe\s?(kanat|haruk)a|(kanat|haruk)a\s?konoe|
優木\s?せつ菜|yuu?ki\s?setsuna|setsuna\s?yuu?ki|中川\s?菜々|nakagawa\s?nana|nana\s?nakagawa|
エマ・ヴェルデ|emma\s?verde|
天王寺\s?璃奈|tennou?ji\s?rina|rina\s?tennou?ji|
三船\s?栞子|mifune\s?shioriko|shioriko\s?mifune|
ミア・テイラー|mia\s?taylor|
鐘\s?嵐珠|lanzhu\s?zhong|
澁谷\s?かのん|shibuya\s?kanon|kanon\s?shibuya|
唐\s?可可|ク[ウゥ]ク[ウゥ]ちゃん|tang\s?keke|keke\s?tang|
嵐千\s?砂都|arashi\s?chisato|chisato\s?arashi|
平安名\s?すみれ|heanna\s?sumire|sumire\s?heanna|
葉月\s?恋|hazuki\s?ren|ren\s?hazuki|
桜小路\s?きな子|sakurakoji\s?kinako|kinako\s?sakurakoji|
米女\s?メイ|yoneme\s?mei|mei\s?yoneme|
若菜\s?四季|wakana\s?shiki|shiki\s?wakana|
鬼塚\s?(夏美|冬毬)|onitsuka\s?(natsum|tomar)i|(natsum|tomar)i\s?onitsuka|oninatsu|
ウィーン・マルガレーテ|wien\s?margarete|
乙宗\s?梢|otomune\s?kozue|kozue\s?otomune|
夕霧\s?綴理|yugiri\s?tsuzuri|tsuzuri\s?yugiri|
藤島\s?慈|fujishima\s?megumi|megumi\s?fujishima|
日野下\s?花帆|hinoshita\s?kaho|kaho\s?hinoshita|
村野\s?さやか|murano\s?sayaka|sayaka\s?murano|
大沢\s?瑠璃乃|osawa\s?ruino|ruino\s?osawa|
百生\s?吟子|momose\s?ginko|ginko\s?momose|
徒町\s?小鈴|kachimachi\s?kosuzu|kosuzu\s?kachimachi|
安養寺\s?姫芽|anyoji\s?hime|hime\s?anyoji
""",
    re.IGNORECASE,
)
EXCLUDE_RE = re.compile(
    r"\b(i|you|we|they) love live\b|(love\s?live(s|rpool|d)\b)", re.IGNORECASE
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

    return any(
        (
            post["author"] == LOVELIVENEWS_BSKY_SOCIAL,
            LOVELIVE_NAME_EN_RE.search(all_texts) and not EXCLUDE_RE.search(all_texts),
            LOVELIVE_RE.search(all_texts),
        )
    )
