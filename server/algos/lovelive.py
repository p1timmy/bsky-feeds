import logging
import re

from atproto_client import models

# from time import perf_counter
from server import config
from server.algos._base import get_post_texts, post_has_media_embeds

logger = logging.getLogger(__name__)

LOVELIVE_NAME_EN_RE = re.compile(
    r"([^a-z0-9_=＝]|^-? *)love ?live($|[^a-z0-9\-]|rs?([^a-z0-9_]|\b))", re.IGNORECASE
)
LOVELIVE_RE = re.compile(
    # "Love Live" + other related words
    r"love[^\S\r\n]?live(([^\S\r\n]|[!:])*("
    r"a(cc((oun)?ts?|s)|(d|fter school|rcade|u)\b|ll[ -]stars|pp|nime)|"
    r"(tribute )?album\b|"
    r"b(adges?\b|lue ?bird)|"
    r"c(anon|ollab|yber|(d|osplay|haracter)s?)|"
    r"d(a(nce(s| groups?)|ys)|rama\b)|"
    r"heardle|"
    r"e(n|pisodes?|ra|tc)\b|"
    r"f(an(art|dom|s)?\b|(anf)?ics?\b|es ?2?\b|i(gur(in)?es?|nals)|ranchise)|"
    r"g(i(f|rls?)|lobal)\b|(rhythm )?game\b|"
    r"hasu|"
    r"i(ce cream|dols?|n general)|"
    r"jumpscare|"
    r"lieder|"
    r"m(aybe|e(ntion(ed)?|rch(andise)?|troidvania)|o(ots|vies?)|vs?)\b|"
    r"n(esoberis?|iji(gasaki)?)|"
    r"o(c(g|s?\b)|mf?g|p\b|r(?! die)\b|s(his?|t))|"
    r"p(ins?\b|l(aylist|ush(ies?)?))|"
    r"referenc(es?|ia)|"
    r"s(chool ?idol|e(ction|ries|iyuus?)|hips?\b|ip([^a-z]|\b)|(ifs)?orter|ky|potted|"
    r"o(los?\b|ng\b|undtrack)|taff|u(b ?units?|nshine|per ?star))|"
    r"t(cg|h(emed?\b|ings))|"
    r"u['’]s|"
    r"vn\b|"
    r"wa(ifus?|tch party)\b|"
    r"yuri\b"
    r")| ?!? +(vs|X)\b| fest?\b)|"
    r"lovelive(-(anime|fanfunfestival|news\.bsky\.social)|_staff|15th)|"
    r"\b((dan|enjoy|hate|is thi|love|m(eet|is)|think|variou|(?<!it )wa)s|draw(ing|s)|"
    r"thank you|like[ds]?) love ?live\b|#lovelive(art|_)|\bLL(heardle|s(ip|taff))|"
    # ラブライブ but not クラブライブ (club live)/イコラブライブ (Ikolab Live)/
    # マジラブライブ (Maji Love Live)
    r"([^クコジ]|\b)(リンクライク)?ラブライ(ブ[!！\s]*(サンシャイン|スーパースター)?|バー)|"
    # School idol
    r"スクールアイドル|(?<!middle )(?<!high )(?<!old )(?<!old-)(?<!your )\b"
    r"(?<!@)(#\w+)?school ?idol(?! (story|book)\b)(s\b| ?((festiv|music)al|project))?|"
    # Games
    r"\bl(l|ove ?live ?)sif2?\b|\b(ll)?sif(as\b|\s?all[\s\-]?stars)|"
    r"\bLL(_|official-)cardgame|#ラブカ\b|ラブカ感謝祭|"
    # ぷちぐる but not ぷちぐるみ
    r"ぷちぐる([^み]|$)|puchiguru\b|"
    # スクスタ/スクミュ but not words with マスク/デ(ィ)スク/スタンド/スタンプ/スタイル/スタッフ
    r"(^|[^\u30a1-\u30f6\u30fc])スク(スタ(?!ン[ドプ]|イル|ッフ|ート)|ミュ)|"
    # Love Live! School Idol Project
    # NOTE: Printemps, lily white, BiBi not included due to too many false positives
    r"音ノ木坂?|otonokizaka|([^a-z]|\b)[μµ](['’‘`´′]s(ic)?|sic\s?forever)([^a-z]|\b)|"
    r"高坂\s?穂乃果|絢瀬\s?絵里|南\s?ことり|園田\s?海未|星空\s?凛|西木野\s?真姫|東條\s?希|"
    r"小泉\s?花陽|矢澤\s?にこ|nico\snico\sni+\b|#niconiconi+\b|\bminalinsky\b|ミナリンスキー|"
    r"エリーチカ|\belichika\b|りんぱな|\b(nico)?rinpana\b|金曜凛ちゃんりんりんりん|火曜日かよちゃん|"
    r"#にこまき|ほのまき|のぞえり|\bnozoeli\b|"
    r"snow\s?halation([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"(^|[^a-z\u00C0-\u024F\u1E00-\u1EFF\-])a[-\u2010]rise([^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|$)|"
    r"綺羅\s?ツバサ|優木\s?あんじゅ|統堂\s?英玲奈|"
    # Love Live! Sunshine!!
    # NOTE: AZALEA not included due to too many false positives
    r"(^|[^三土])浦の星女?|uranohoshi|([^a-z0-9]|\b)aq(ou|uo)rs([^a-z0-9]|\b)|"
    r"(\W|\b)cyaron!?(\W|\b)|guilty\s?kiss([^a-z]|$)|"
    # AiScReam (Ayumu, Shiki, Ruby)
    r"([^a-z]|\b)((ai[♡-]?|(?-i:[Aa]i ))scream(?! queens)\b|"
    r"(?-i:AI (SCREAM\b|(?i:scream!))))|愛♡スクリ〜ム|"
    # Yohane the Parhelion
    r"幻(日のヨハネ|ヨハ)|genjitsu ?no ?yohane|yohane ?the ?parhelion|"
    r"sunshine in the mirror|blaze in( the)? deepblue|"
    r"numazu( in( the)?)? mirage|#ヨハネ(生誕|誕生)祭|"
    r"高海\s?千歌|桜内\s?梨子|松浦\s?果南|黒澤\s?(ダイヤ|ルビィ?)|渡辺\s?[曜月]|津島\s?善子|"
    r"国木田\s?花丸|小原\s?鞠莉|"
    r"がんば(ルビ|るび)|(^|[^@])ganbaruby|today['’]s maru\b|maru's month|"
    r"よし(ルビ|りこ)|#よしまる|るびまる|"
    r"\b((ruby|yoha)maru|yo((shi|ha)riko|u(chika|riko))|diamari)\b|"
    r"(永久|\beikyuu\s?)(hours|stage)|"
    r"(?<!\bRT @)(?<!x.com/)saint\s?snow([^a-z]|$)|"
    r"鹿角\s?(理亞|聖良)|"
    # Nijigasaki
    r"虹ヶ咲(?!学園交通運輸研究部)|ニジガク|(アニ|エイ)ガサキ|(あに|えい)がさき|にじ(よん|ちず)|"
    r"([^a-z]|\b)((nij|an|e)igasaki|niji(chizu|gaku|yon))([^a-z]|\b)|a・zu・na|qu4rtz|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(diver"
    r" ?diva|r3birth)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"tokimeki r(unners|oadmap to the future)|^me, a taylor\b|"
    r"(ゆう|せつ|#残業)ぽむ|ぽむせつ|\b(sets|yu?)upomu\b|\bsetsuayu\b|"
    r"高咲\s?侑|上原\s?歩夢|中須\s?かすみ|桜坂\s?しずく|朝香\s?果林|宮下\s?愛|近江\s?(彼方|遥)|"
    r"優木\s?せつ菜|中川\s?菜々|エマ・?ヴェルデ|天王寺\s?璃奈|三船\s?栞子|ミア・?テイラー|鐘\s?嵐珠|"
    r"かすみん|"
    # Love Live! Superstar!!
    r"([^a-z]|\b)(or|tuto|w+)?(?-i:[Ll]iella|LIELLA)(?!(nd|tte))|リエラジ|"
    r"結ヶ丘|yuigaoka|5yncri5e!?|kaleidoscore|トマカノーテ|tomakanote|スパスタ[3３]期|"
    r"澁谷\s?かのん|唐\s?可可|嵐千\s?砂都|平安名\s?すみれ|葉月\s?恋|桜小路\s?きな子|米女\s?メイ|"
    r"若菜\s?四季|鬼塚\s?(夏美|冬毬)|ウィーン・?マルガレーテ|"
    r"ク([ウゥ]ク[ウゥ]ちゃ|ーカー)|oninatsu|オニナッツ|"
    r"sunny\s?pas(sion)?(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"sunnypa(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"聖澤悠奈|柊\s?摩央|"
    # Link! Like! Love Live! / Hasunosora
    # リンクラ but not リンクライン or katakana phrases with リンクラ character sequence
    r"(^|[^\u30a1-\u30f6\u30fc])リンクラ(?!イ(ン|ブラリ)|ボ|ベル|ス|ッ|ブ)|"
    r"hasu\s?no\s?sora|\blink(ura|-like-lovelive)\b|蓮ノ(空|休日)|"
    r"^(?!(.|\n)*\broses?\b(.|\n)*$)((.|\n)*\bcerise\s?bouquet\b(.|\n)*)|"
    r"スリーズブーケ|dollches(tra(?!-art)|\b)|ドルケストラ|mira-cra\spark!?|"
    r"みらくらぱーく[!！]?|\bkahomegu\b|かほめぐ(♡じぇらーと)?|([^a-z]|\b)edel\s?note|"
    r"るりのとゆかいなつづりたち|ruri[&＆]to|PRINCEε[＞>]ε[＞>]|Nεw\sBlack|ichigo\smilk\slove|"
    r"#新メンバーお披露目105期|ハロめぐ|"
    r"乙宗\s?梢|夕霧\s?綴理|藤島\s?慈|日野下\s?花帆|村野\s?さやか|大沢\s?瑠璃乃|百生\s?吟子|"
    r"徒町\s?小鈴|安養寺\s?姫芽|大賀美沙知|桂城\s?泉|セラス[・\s]?柳田[・\s]?リリエンフェルト|"
    # Love Live! Bluebird
    # NOTE: "L(ove) High School" not included due to too many false positives
    r"いきづら[い絵]部|イキヅ(ライブ|LIVE配信)|\bikizu( ?(live|raibu))?|love学院|"
    r"高橋\s?ポルカ|麻布\s?麻衣|五桐\s?玲|駒形\s?花火|金澤\s?奇跡|調布\s?のりこ|春宮\s?ゆくり|"
    r"此花\s?輝夜|山田\s?真緑|佐々木\s?翔音|"
    r"\b(polka_lion|My_Mai_Eld|G_Akky304250|hanabistarmine|MiracleGoldSP|Noricco_U|"
    r"Yukuri_talk|Rollie_twinkle|LittlegreenCom|ShaunTheBunny)([^a-z]|$)|"
    # Concerts
    r"異次元フェス|ijigen\sfest?|#(llsat_|虹ブンブンビー_day[12])|"
    # Community stuff
    r"\bteam onibe\b|\bonib(e|ased)([^a-z’]|$)|schoolido\.lu|idol\.st(?!/user/\d+)|"
    r"#HasuTH_Tran|([^a-z]|\b)OurSIF([^a-z]|$)|\bidoltober|#LL_Calendar_Collab_2026",
    re.IGNORECASE,
)
SUKUFEST_RE = re.compile(
    r"(^|[^マアレ])スクフェス(?!札幌|大阪|[福盛]岡|神奈川|新潟|仙台|三河|沖縄|金沢|香川|名古屋|ニセコ)"
)
SOLDIER_GAME_RE = re.compile(r"([^a-z]|\b)soldier game([^a-z]|\b)", re.IGNORECASE)
YOHANE_RE = re.compile(r"\b(?<!@)yohane(?!(-label|.*mbatiza[jt]i))\b", re.IGNORECASE)
CATCHU_RE = re.compile(
    r"([^A-Za-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(C[Aa]t[Cc][Hh]u|catchu|CATCHU)!?"
    r"([^A-Za-z\u00C0-\u024F\u1E00-\u1EFF]|\b)"
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
        # NOTE: Watanabe You/You Watanabe included in pattern builder to try to skip
        # posts mentioning other people with Watanabe in their names, has the phrase
        # "thank you Watanabe", or contains "Lazarus" anywhere in the post
        ("Tsuki", "Watanabe", False),
        ("Yoshiko", "Tsushima", False),
        ("Hanamaru", "Kunikida", False),
        ("Mari", "(?<!Money )Ohara", False),
        # Saint Snow
        ("Kazuno", "Leah", True),
        # NOTE: Leah Kazuno included in pattern builder to try to skip posts containing
        # both "Donkey/Diddy Kong" and a speedrunner named "LeahKazuno"
        ("Sarah", "Kazuno", False),
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
        # NOTE: Mia Taylor included in pattern builder to prevent generating a pattern
        # for "MiaTaylor" due to too many false positives
        ("Lanzhu", "Zhong", False),
        # Liella
        ("Kanon", "Shibuya", False),
        ("Keke", "Tang", False),
        ("Chisato", "Arashi", False),
        ("Sumire", "Heanna", False),
        # NOTE: Ren Hazuki included in pattern builder to try to prevent posts about
        # Ren Hazuki from "The Expanse" from being added
        ("Hazuki", "Ren", True),
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
        ("Izumi", "Katsuragi", False),
        ("Ceras", "Yanagida", True),
        ("Yanagida", "Lilienfeld", True),
        ("Ceras", "Lilienfeld", True),
        # LL Bluebird
        ("Polka", "Takahashi", False),
        ("Mai", "Azabu", False),
        ("Akira", "Gotou?", False),
        ("Hanabi", "Komagata", False),
        ("Miracle", "Kanazawa", False),
        ("Noriko", "Chou?fu", False),
        ("Yukuri", "Harumiya", False),
        ("Aurora", "Konohana", False),
        ("Midori", "Yamada", False),
        ("Shion", "Sasaki", False),
    }
)

EXCLUDE_RE = re.compile(
    # The great "I love live [something]" hoarde
    # - I('d/'ve)/he/she/they/you (all)/y'all/you'll/we (all/both)/gotta/got to/have to/
    #   learn(ed) to/like to/who/anyone (else), people/ppl (in [some place]), [plural word]
    #   that, my ... and sister/brother/wife/etc.
    r"\b((i|s?he|they)(['’]?(d|ve))?|y(ou(['’]ll)?|(ou |['’])all)|we( (all|both))?|"
    r"gotta|(got|have|l(earn(ed)?|ike)) to|who|p(eople|pl)( in (the )?[a-z]+[a-z])?|"
    r"[a-z]{3,}(?<!a)(?<!e)s( that)?|my .+and [a-z]+[a-z]|"
    r"anyone( else['’]s|( else)?( (o(ver|ut) )?t?here)?)?)"
    # - *ly/also/always/bloody/can't/cannot/(sure) do/does/don't (but not "don't do")/
    #   even/f*king/hecking/just/lowkey/still/(came/come/grew/have/happened/use(d)/tend)
    #   to/too/will/would('ve)/... and
    r"(( ?,)? ([a-z]+ly|al(so|ways)|bloody|can(['’]|((['’]?t)? )?no)t|(sure )?do|does|"
    r"don['’]?t(?! do\b)|even|(f[a-z]+|hec)ki?n[g'’]?|just|lowkey|(st|w)ill|"
    r"((c[ao]me|ha(ve|ppen(ed)?)|used?|grew) t|s|t(o|end t))o|would(['’]ve)?|"
    r"[a-z]+[a-z] (and|&)))*"
    # - love live [something]/love liver(s)/love Live (as in a band named LĪVE, Ableton
    #   Live music software, or typo of "love life")
    r" ((love )+live((?! (so |a(nd|s well)|but)\b),? &? ?#?\w+\b|rs?)|"
    r"love live($|[^\s\w]| \w+))|"
    # "love live music/comedy/theater" at start of sentence or after any emoji but not
    # "love live music/comedy/theater is/was"
    r"(^|[^\w ] *)love live (music|comedy|theat(er|re))\b(?! ((i|wa)s\b))|"
    # "love live [something]" after *ly/f*king/hecking/bloody
    r"(([a-z]+ly|(f[a-z]+|hec)ki?n[g'’]?|bloody) +)love live \w+\b|"
    # "also/and/but (still) love live [something] (for)" at end of sentence but not
    # "also/and/but love live does(n't)/got/had/has/is/was/will"
    r"(a(lso|nd)|but) (still )?love live(?! (does(n['’]?t)?|got|ha[ds]|(i|wa)s|will)\b)"
    r"( [a-z]+[a-z]){1,2}( for\b| ?[^\w ]|$)|"
    # It's/What a ... to love live [something]
    r"(it['’]?s|what) a ([\w'’\-]+ +)+to love live [a-z]+[a-z]|"
    # "love live music" at end of sentence but not "about/i(t)s/of/to love live music"
    r"(?<!\babout )(?<!\bit['’]s )(?<!\bits )(?<!\bis )(?<!\bof )(?<!\bto )love live"
    r" music *[^\w ]|"
    # Words/phrases starting with "love live"
    r"\blove live ("
    # - love live @ (usually songs ending with "Love" + "live @ [some place/event]")
    # - love Live 2D (as in Live2D animation technique/software)
    r"@ |2d|"
    # - love live action
    # - love Live A Live (video game title)
    # - Love Live Alive (Genesis Climber MOSPEADA OVA)
    # - love live ammo (usually "Republicans love live ammo and dead kids")
    # - love live and be happy/nice/etc.
    # - love "Live and Dangerous" (album by Thin Lizzy)
    # - love "LIVE and FALL" (album by Xdinary Heroes)
    # - love live and let
    # - love live at (usually songs ending with "Love" + "live at [some place]" but not
    #   "love live at it(')s")
    r"a(ction|mmo|nd (be|dangerous|fall|let)\b|t\b(?!it['’]?s\b)| ?live)|"
    # - love "Live and Learn" (usually Sonic Adventure 2 theme song)
    r"(and|&) learn\b|"
    # - love live beyond/broadcasting
    # - Love Live Bleeding (typo of "Love Lies Bleeding")
    r"b(eyond|(leed|roadcast)ing)|"
    # - Love live Canada (typo of "Long live Canada")
    # - love live captioning/cricket
    r"c(a(nada|ptioning)|ricket)|"
    # - love live (and/or) die
    # - love "Live and Let Die" (James Bond movie title)
    # - love "Live Die Repeat" (alt name of "Edge of Tomorrow" movie)
    r"((and|&|or) (let )?)?die( repeat)?\b|"
    # - love live demos/dragons
    r"d(emo|ragon)s|"
    # - love live entertainment
    r"entertainment|"
    # - love live fact checking
    # - Love Live Festival (usually rock music festival by @solidents.bsky.social)
    # - love live folk
    # - love "Live Free and Die Hard"
    # - love live from (usually songs ending with "Love" + "live from [some place]",
    #   also includes "love Live from Daryl's/Tubby's House")
    r"f(act checking|estival|olk\b|r(ee (and|&) die hard|om))|"
    # - love live happily (ever after)
    # - love live him
    # - love live hockey
    r"h(appily|im|ockey)|"
    # - love "Live in Colo(u)r" (sometimes typo of "love Life In Color")
    # - love live interaction
    r"in( colou?r|teraction)|"
    # - Love Live Italian
    # - love live within
    r"(italia|withi)n|"
    # - love live jazz
    r"jazz|"
    # - love live (and) laugh
    r"(and )?laugh|"
    # - love live life/long/loud (music)
    # - Love Live Local (small business related nonprofit in Cape Cod, MA)
    # - "love live love" but not "love live love wing bell"
    r"l(ife|o(cal\b|ng|ud( music)?|ve(?! wing bell)))|"
    # - love live moments/music at
    r"m(oments|usic at\b)|"
    # - love live now at/on
    r"now (at|on)\b|"
    # - love live oak(s)/on stage
    r"o(aks?|n stage)|"
    # - love live reaction(s)
    # - love live renditions
    # - love live rock (typo of "long live rock")
    # - love "Live Rust" (album by Neil Young & Crazy Horse)
    r"r(e(actions?|nditions)|ock|ust)|"
    # - love live service/sport(s)/streaming/stream(s)/strings
    # - love Live Score (some sports app)
    # - Love Live Sweets (unrelated local bakery in New Jersey)
    r"s(core|ervice|ports?|tr(eam(ing|s)?|ings)|weets)|"
    # - love live tables/tapes/TV/television/texting/theater/trees/tweeting
    # - love "Live to Live" (song from Hazbin Hotel S2)
    # - love "Live to Tell" (song by Madonna)
    # - love "Live Through This" (usually album by Hole)
    r"t((a(bl|p)|re)es|elevision|(ex|wee)ting|h(eat(er|re)|rough this)|v|"
    r"o (live|tell))|"
    # - "love live the" (usually typo of "long live the") but not "Love Live the
    #   competition/most/Musical/other/same/School Idol"
    r"the\b(?! (competition|m(ost|usical)|other|s(ame|chool idol))\b)|"
    # - love live tour/your
    r"[ty]our|"
    # - "love live ur" (usually typo of "long live ur") but not "Love Live UR ... card"
    r"ur (?!.*\bcards?\b)|"
    # - love Live Wire
    r"wire|"
    # - love live bands/gigs/mealworms/performances/shows/versions
    # - "Love Live in Paris" (typo of "Lover (Live from Paris)" album by Taylor Swift)
    r"(band|gig|mealworm|performance|show|version|in pari)s|"
    # - 196x/197x after "love live" (usually live concert recordings)
    r".*\b19[67][0-9]\b)|"
    # [Artist] - [song name ending with "love"] live
    r"\w+ [\-\u2013] .+ love live\b[^!]|"
    # just/my/[plural word] ... love liver (body part or food)
    r"\b(just( [a-z]+[a-z])?|my( ([a-z,'’]{3,}|&))+|[a-z]{3,}s( [a-z]{3,}){,2})"
    r" love liver\b|"
    # Words/phrases ending with "love live"
    r"\b("
    # - "2Kindsa Love" live (song by The Jon Spencer Blues Explosion)
    r"2 ?kindsa|"
    # - about/confess(ed/es/ing) his/her/their love live (usually typo of "about his/
    #   her/their love life/lives")
    r"(about|confess[a-z]*) (h(er|is)|their)|"
    # - "Abandoned Love" live (song by Bob Dylan)
    # - absolutely love live [something]
    # - "Ain't Talkin' 'bout Love" live (song by Velvet Revolver or Van Halen)
    # - "A Little Love" live
    r"a(b(andoned|solutely)|in['’]?t talkin['’]? ['‘’]?bout| little)|"
    # - stuff ending with "my love live":
    #   - "All My Love" live (usually song by Coldplay or any song name ending with
    #   that phrase)
    #   - "Darker My Love" live (song by T.S.O.L.)
    #   - "Darkness at the Heart of My Love" live (song by Ghost)
    #   - "Make You Feel My Love" live (song by Adele)
    #   - "To Bring You My Love" live (song by PJ Harvey)
    r"(all|dark(er|ness at the heart of)|make you feel|to bring you) my|"
    # - stuff ending with "is love live":
    #   - "All You Need Is Love" live (usually song by The Beatles)
    #   - "What The World Needs Now Is Love" live (usually covers of 1960s song by
    #     Jackie DeShannon)
    #   - "What Time Is Love" live (usually song by The KLF)
    #   - his love live (usually typo of "his love life")
    #   - "Prophecy x This Love" live (song by Taylor Swift)
    r"((all you need|what t(he world needs now|ime)) |(prophecy x t)?h)is|"
    # Art(ist(s))/band(s)/music/people/[some plural word] I/you/etc. (... and) love live
    r"(art(ist)?|band|music|people|[a-z]+s) (i|you|they)( ([a-z]+[a-z],? )+(and|&))?|"
    # - "Bad Love" live (usually song by Key or Eric Clapton) but not "how bad Love Live"
    r"(?<!how )bad|"
    # - "Blind Love" live (different songs by different artists)
    # - "Bye Bye Love" live (usually song by The Everly Brothers or Simon & Garfunkel)
    r"b(lind|ye bye)|"
    # - stuff ending with "it's love live":
    #   - "Because It's Love" live (song by The Kelly Family)
    #   - "When It's Love" live (song by Van Halen)
    r"(because|when) it['’]s|"
    # - can/could you not love live
    # - "Can't Buy Me Love" live (usually song by the Beatles)
    # - "Can't Get Enough of Your Love" live (song by Bad Company)
    # - "Can't Hide Love" live (usually song by D'Angelo)
    # - complicated love live (typo of "complicated love life")
    # - "Computer Love" live (song by Kraftwerk)
    # - "Connected by Love" live (song by Jack White)
    # - "Cosmic Love" live (usually song by Florence + The Machine)
    r"c(an['’]?t (buy me|get enough of your|hide)|(an|ould) you not|"
    r"o(mp(licated|uter)|nnected by|smic))|"
    # - stuff ending with "of love live":
    #   - "All is Full of Love" live (song by Bjork)
    #   - "Any Kind of Love" live (song by REO Speedwagon)
    #   - "(The) Book of Love" live (usually song by The Magnetic Fields or its covers)
    #   - "Caravan of Love" live (usually song by The Housemartins)
    #   - "(The) Crush of Love" live (song by Joe Satriani)
    #   - "Dance Me to the End of Love" live (song by Leonard Cohen)
    #   - "Death of Love" live (usually song by James Blake)
    #   - "Definition of Love" live (song by Naomi Sharon)
    #   - "Fire of Love" live (usually album by The Gun Club)
    #   - "Genius of Love" live (song by Tom Tom Club)
    #   - "Hazards of Love" live (album by The Decemberists)
    #   - "(The) House of Love" live (usually British alt rock band or song by Christine)
    #   - "Lexicon of Love" live (album by ABC)
    #   - "Light of Love" live (usually song by Florence and the Machine)
    #   - "Miracle of Love" live (song by Eurythmics)
    #   - "Mystery of Love" live (usually song by Sufjan Stevens)
    #   - "Path of Love" live (usually song name)
    #   - "Prisoner of Love" live (song by James Brown)
    #   - "Satellite of Love" live (usually song by Lou Reed)
    #   - "Shot of Love" live (song by Bob Dylan)
    #   - "Songs of Love Live" (album by Mark Eitzel)
    #   - "Sunday Kind of Love" live (song by different artists, usually Etta James)
    #   - that/what kind of love live (sometimes typo of "that/what kind of love life")
    #   - "The Meaning of Love" live (song by Depreche Mode)
    #   - "The Look of Love" live (song by different artists)
    #   - "(Thee) Most Exalted Potentate of Love" live (song by The Cramps)
    #   - this/that/what kind of love live
    #   - "Tunnel of Love" live (usually song by Dire Straits or Bruce Springsteen)
    #   - "Victim of Love" live (song by Eagles)
    r"(all is full|book|c(aravan|rush)|d(ance me to the end|e(ath|finition))|fire|"
    r"genius|h(azards|ouse)|l(exicon|ight)|p(ath|risoner)|s(atellite|hot|ongs)|"
    r"m(iracle|ost exalted potentate|ystery)|(any|sunday|[tw]hat|this) kind|"
    r"t(he (look|meaning)|unnel)|victim) of|"
    # - stuff ending with "in love live":
    #   - "Crazy in Love" live (song by Beyonce)
    #   - "Dangerously in Love" live (album by Beyonce)
    #   - "Drunk in Love" live (song by Beyonce)
    #   - "Fall(s) in Love" live (usually different songs by different artists or any
    #     song name ending with that phrase)
    #   - "Fallin(g) in Love" live (usually different song names ending with that phrase)
    #   - "Friday I'm In Love" live (usually song by The Cure or cover by Robert Smith and
    #     Olivia Rodrigo)
    #   - "I'm Not in Love" live (usually song by 10cc)
    #   - "I'm Always in Love" live (song by Wilco)
    #   - "(I) Think I'm In Love" live (usually song by Eddie Money)
    #   - "Paris in Love" live (album by Ibrahim Maalouf)
    #   - "Stone in Love" live (song by Journey)
    r"(crazy|d(angerously|runk)|fall(in[g'’]?|s)?|(friday|think) i['’]?m|paris|stone|"
    r"i['’]?m (always|not)) in|"
    # - "Destination: Love Live" (album by The Make-Up)
    # - does not/doesn't love live [something]
    r"d(estination:?|o(es)?( not|n['’]t))|"
    # - "Faithless Love" live (song by Linda Ronstadt)
    # - "Fake Love" live (song by BTS)
    # - "Feelin' Love" live (song by Paula Cole)
    # - "Feel Like Makin' Love" live (song by Roberta Flack or Bad Company)
    # - feel the love live
    # - fight love live (usually Filoli, California historical marker)
    # - "Frozen Love" live (song by Buckingham Nicks)
    r"f(a(ithless|ke)|eel(in['’]?| (like makin['’g]?|the))|ight|rozen)|"
    # - stuff ending with "for love live":
    #   - "Ain't No Cure for Love" live (song by Leonard Cohen)
    #   - "Exist for Love" live (song by Aurora)
    #   - "Fool for Love" live (different songs by different artists)
    #   - "Kill for Love" live (usually song by Lady Gaga)
    #   - "Living for Love" live (song by Madonna)
    #   - "Out for Love" live (song from "Hazbin Hotel" animated series, but not "came
    #     out for love live")
    #   - "(Bardic) Quest for Love" live (indie visual novel game)
    #   - "Ready for Love" live (usually song by Bad Company, but not "get(ting) ready
    #     for love live")
    r"(ain['’]?t no cure|exist|(foo|kil)l|living|(?<!\bcame )out|quest|"
    r"(?<!\bget )(?<!\bgetting )ready) for|"
    # - G. Love live (American singer/rapper)
    # - Gerry Love live (British rock singer/bass guitar player)
    r"g(er(ard|ry)|\.?)|"
    # - give/show (them/me/etc.) some love live
    r"(give|show) (\w+ )?some|"
    # - Helen Love live (Welsh rock band)
    r"helen|"
    # - stuff ending with "your love live":
    #   - "All Your Love" live (usually song by Otis Rush or any song name ending with
    #     that phrase)
    #   - "Come And Get Your Love" live (song by Redbone)
    #   - "[song name ending with "For Your Love"]" live
    #   - "How Deep Is Your Love" live (usually song by Bee Gees)
    #   - in your love live (sometimes typo of "in your love life")
    #   - "Sunshine of Your Love" live (usually song by Cream)
    r"(all|come (and|&) get|for|how deep is|in|sunshine of) your|"
    # - compassion/happiness/hope/joy/kindness/pain/peace/unity and ([God/someone]'s)
    #   love live
    r"(compassion|h(appiness|ope)|joy|kindness|p(ain|eace)|unity),?"
    r" (and|&)( [a-z]+['’]s)?|"
    # - stuff ending with "to love live":
    #   - learn/want(ed/ing) to love live [something]
    #   - "How To Love" live (usually song by Lil Wayne or any song name ending with
    #     that phrase)
    #   - "Love to Love" live (usually song by UFO)
    #   - "Slave to Love" live (song by Bryan Ferry)
    #   - "Somebody to Love" live (usually song by Queen or Jefferson Airplane or any
    #     song name ending with that phrase)
    #   - what's/what is not to love live
    r"(how|(learn|want)(ed|ing)?|love|s(lave|omebody)|what(['’]| i)?s not) to|"
    # - (that) I('d) love live [something] (all other cases not caught by the Great "I
    #   love live [something]" Hoarde pattern)
    r"(that)?\bI(['’]d)?|"
    # - "I Feel Love" live (usually song by Donna Summer)
    # - "I'm Outta Love" live (song by Anastacia)
    # - "It Must Be Love" live (song by Madness)
    # - "It's Only Love" live (usually covers of song by The Beatles)
    r"I( feel|['’]m outta|t( must be|['’]s only))|"
    # - laugh/let (that)/live love live
    # - "La La Love" live (K-pop song by NCT DREAM)
    # - "Love, Hate, Love" live (song by Alice In Chains)
    # - "Love and Only Love" live (song by Neil Young)
    # - "Loud Love" live (song by Soundgarden)
    # - "Love Meeting Love" live (song by Level 42)
    r"l(a( la|ugh)|et( that)?|ive|o(ud|ve( and only|,? hate,?| meeting)))|"
    # - "life love live" but not "Link Life Love Live"
    r"(?<!link )life|"
    # - "Lotta Love" live (song by either Neil Young or Nicolette Larson) or "Whole
    #   Lotta Love" live (usually song by Led Zeppelin)
    r"(whole )?lotta|"
    # - "Mad Love" live (usually album by Linda Ronstadt)
    # - Maji Love Live (live concerts by ST☆RISH from Uta no Prince-sama)
    # - "Message of Love" live (song by The Pretenders)
    # - "Message to Love" live (song by Jimi Hendrix)
    # - Mike Love live (American reggae artist)
    # - "My True Love" live (song by The Promise)
    r"m(a(d|ji)|essage (of|to)|ike|y true)|"
    # - "Network Love" live (K-pop song by Seventeen)
    # - "No Loss, No Love" live (song by Spiritbox)
    # - "No Ordinary Love" live (song by Sade)
    # - "Nothing Without Your Love" live (K-pop song by (Seok-)Jin)
    r"n(etwork|o( (loss,? no|ordinary)|thing without your))|"
    # - "Pirate Love" live (song by The Heartbreakers)
    # - Pop the Balloon or/and/to/etc. Find Love live (dating show on YT/Netflix)
    # - "Punch-Drunk Love" live (romantic movie title)
    r"p(irate|op [a-z]+ balloon [a-z]+ find|unch[ -]drunk)|"
    # - Quest Love live (famous drummer/DJ)
    r"quest|"
    # - "Radar Love" live (song by Golden Earring)
    # - Radical Love Live (some religious podcast with a Bluesky presence)
    # - really love live [something]
    # - Rinku Love Live (NSFW/R18 AI artist sometimes featured on @mikubot.bsky.social)
    r"r(ad(ar|ical)|eally|inku)|"
    # - "Same Old Love" live (song by Selena Gomez)
    # - Savage Love Live (sex advice podcast by Dan Savage)
    # - "Sexy Love" live
    # - "Show Me Love" live (usually song by Robin S.)
    # - Simon Love live (some random British artist with an official Bluesky account)
    # - "Some Kinda Love" live (song by The Velvet Underground)
    # - "Soul Love" live (song by David Bowie)
    # - "Spiritual Love" live (usually song by Urban Species)
    # - spread love live
    # - Stone Love live (usually Jamaican DJ group)
    # - "Strange Love" live (usually song by Depreche Mode or album by T.S.O.L.)
    # - "Super Duper Love" live (song by Sugar Billy or Joss Stone)
    # - "Sweet Love" live (usually song by Anita Baker)
    r"s(a(me old|vage)|exy|imon|how me|o(me kinda|ul)|p(iritual|read)|t(one|range)|"
    r"uper duper|weet)|"
    # - hear/saw/see(n) [artist name] perform [song name ending with "Love"] live
    r"(hear|s(aw|een?)) .+ perform .+|"
    # - "Tainted Love" live (song by Soft Cell)
    # - Team Love Live (typo of "Team Love Life")
    # - "The One I Love" live (song by R.E.M.)
    # - they love live [something] (all other cases not caught by the Great "I love
    #   live [something]" Hoarde pattern)
    r"t(ainted|eam|he( one i|y))|"
    # - "Unconditional Love" live
    r"unconditional|"
    # - would love live [something] (all other cases not caught by the Great "I love
    #   live [something]" Hoarde pattern)
    # - "Wasted Love" live (song by JJ)
    # - we love live [something] (all other cases not caught by the Great "I love live
    #   [something]" Hoarde pattern)
    # - "We Are Love" live (album by The Charlatans)
    # - "We Found Love" live (song by Rihanna feat. Calvin Harris or any song name
    #   ending with that phrase)
    # - "We Got Love" live (usually different songs by The Beach Boys or Jessica Mauboy)
    # - "Wreckless Love" live (song by either Alicia Keys or Robert Plant)
    r"w(asted|e( (are|found|got))?|ould|reckless)|"
    # - you are/you're in love live
    r"you( a|['’])re in) love live\b|"
    # - @[user handle ending with ".love"] live
    r"@([a-z0-9\-]+\.)+love live\b|"
    # "Big Love" live (in) (song by Fleetwood Mac or Lindsey Buckingham)
    r"(fleetwood|linds[ae]y|buckingham)(.|\n)+big love live|"
    r"big love live( in|(.|\n)+(fleetwood|linds[ae]y|buckingham))|"
    # "I Need Love" live (different songs by different artists) but not "I need Love
    # Live ([some plural word]) to ..."
    r"\bI need love live\b(?! ([a-z]+s )?(to|2)\b)|"
    # "It Was Love" live (K-pop song by Latency)
    r"latency(.|\n)+\bit was love live|\bit was love live(.|\n)+latency|"
    # "Modern Love" live (song by David Bowie)
    r"bowie(.|\n)+\bmodern love live|\bmodern love live(.|\n)+bowie|"
    # "(The) Power of Love" live (different songs by different artists, except at end
    # of line/post or before exclamation mark)
    r"power of love live(?!!|$)|\b(frankie|huey).+power of love live|"
    # Trivia:Love Live (song by BTS)
    r"\btrivia( ?承)?[: ]{1,2}love live|"
    # perform(s/ed/ing/ance of)/sing(s/ing)/play(ing/s)/covers [song name ending with
    # "Love"] live on/in(side)/outside/with/again
    r"(perform(ance of|ed|ing|s)?|(play|sing)(ing|s)|covers) .+ (?<!from )love live"
    r"($| +([io]n|(in|out)side|with|again)\b)|"
    # if you (live in/near/around [place name]) ... and/but love live (...) music/comedy
    r"((you(\s+liv|['’]r)e\s+(in|near|around)|if you)\s+.+\s+)?(and|but)\s+love"
    r" live( .+)? (music|comedy)\b|"
    # can/will love live on
    r"(can|will) love live on|"
    # love liver (and/with) onions/spinach, love liver disease/pate
    r"love liver(( (and|&|with)|,)? (onions|spinach)| (disease|p[aâ]t[eé]))|"
    # "love liver(s and)" at beginning of sentence/after emoji and not before "is/are"
    r"(^|[^\w ] *)love liver(s and)?(?! (are|is))\b|"
    # whether you('re) ... or (just) love live [something]
    r"whether you.+ or (just )?love live |"
    # "(and) love live [something]" as a typo of "long live [something]" or "love love
    # love love [something]" but not "(and) love live all/also/always/and/are/as/auf/
    # but/can/could/did/does(n't)/doing/going/gone/got/had/has/hates/here/I/if/in/is(t)/
    # I'll/I'm/just/kinda/kind of/made/make(s)/making/may [be/have/not]/music [is/was]/
    # needs/never/not/on/really/siempre/should/song(s)/there/tries/tried/UR ... card(s)/
    # was/what/will/would"
    r"(([^\w\s:]+? *|^)(and )?(love )+live[\"'”’]?(?! (a(l(l(?! of)|so|ways)|nd|re|s|"
    r"uf)|but|can|[csw]ould|[dg]oing|d(id|oes(n['’]?t)?)|gone|[gn]ot|ha([ds]|tes)|just|"
    r"t?here|i([fn'’]|st?)?|kind(a| of)|ne(eds|ver)|on|really|s(iempre|ongs?)|trie[ds]|"
    r"m(a(de|k(es?|ing)|y( ?be| (have|not)))|usic (i|wa)s)|w(as|hat|ill)|"
    r"ur .*cards?)\b)|([^\w\s'’,:]+? +|^)(love )+live,)( #?[a-z\-'’]+)+ ?([^\w ]|$)|"
    # "love love live(r)" at beginning of sentence
    r"([^\w\s]+? *|^)love (love )+liver?\b|"
    # ... and love live(s) here/there
    r" (and|&) love lives? t?here\b|"
    # may/on your/our/his/her/their ... love live
    r"\b(may|on) (h(is|er)|their|y?our) (.+ )?love live |"
    # "our love live" at end of sentence/post
    r"\bour love live *[^\w ]|"
    # in/may/my love live in, includes:
    # - my ... in love live in (typo of "my ... in law live in")
    # - who live in love live (1 John 4:16)
    r"\b(in|ma?y) love live in\b|"
    # her/his/our/their/who(se)/yet ... (and) love live in/on/with
    r"(h(er|is)|(y?ou|thei)r|who(se)?|yet|\w+['’]s)( ([a-z]+[a-z]|.+ (and|&)))?"
    r" love lives? ([io]n|with)|"
    # "his/her/their/you(r) (...ing) love live" (sometimes a typo of "love life/lives")
    # or "learn love live" before period/comma/quote mark/"is/was" at end of sentence
    # or post
    r'\b((h(er|is)|their|your?)( [a-z]+ing)?|learn) love live([.,"”]|$| (i|wa)s\b)|'
    # playing [video game title ending with "Love"] live on
    r"\bplay(ing)? .+ love live on|"
    # "love live here/on/there" at end of sentence/post
    r"\blove live (on|t?here) *[^\w ]|"
    # I('d/'m/'ve)/who/my ... saw/have heard/[[[got/need/went/etc.] to/gotta/gonna]
    # hear/see] [song/artist name ending with "Love"] live
    r"\b(I(['’][dm]|ve)?|my( [a-z'’,&]+)+|who) ((([a-z]+ ){,2}to|go(tt|nn)a) "
    r"(h((ave h)?eard|ear)|s(aw|ee))) ([\w'’]+ )+love live|"
    # find love live and/your/etc.
    r"\bfind love live \w{3,}\b|"
    # hashtags frequently used in #lovelive/"(#)love live" false positives
    r"#(AEW\w*|b(b27|eyondthegates)|couple\w+|eaglerock|F(aith|otoVorschlag)|"
    r"g(od|ratitude)|hope|L(ove(Is(Blind|land\w*)|r|Story|Wins)?|ivemusic)|"
    r"M(o(m|tivation)|usic(Challenge|sky))|(NewYear|ValentinesDay)20[0-9]{2}|"
    r"O(nlyFans|wnOurVenues)|positivity|totp|v(iral|ss365)|"
    r"[a-z]+(daymo(rning|tivation)|vibes[a-z]*))\b|"
    # Random artists frequently mentioned in "love live (music)" false positive posts
    r"\b(d(['’]angelo|uran ?duran)|floyd|grateful dead|hot mulligan|john lewis|kahan|"
    r"marley|nick cave|oasis|phish)\b|"
    # Venue of Love Live (rock music) Festival
    r"\bblackpool|"
    # Macclesfield, UK has a design company called LOVELIVE
    r"\bmacclesfield|"
    # "Speak Now" (Taylor Swift song frequently paired with "Love live" (typo of "Lover
    # live" as in another 1 of her songs/albums))
    r"\bspeak ?now\b|"
    # lovelive.com/net/org/etc.
    r"\blovelive\.[a-z]+[a-z](?:[^.a-z0-9\-]|$)|"
    # "Lush" and "Lovelive" (typo of "Lovelife" album) in the same post
    r"\b(lush\b.+\blovelive|lovelive.+\blush)\b",
    re.IGNORECASE | re.MULTILINE,
)
FAKE_YOHANE_RE = re.compile(r"shaman ?king|touhou", re.IGNORECASE)
HI_YOHANE_RE = re.compile(r"\bh(e(llo|y)|i+) yohane\b", re.IGNORECASE)
FAKE_CATCHU_RE = re.compile(
    # Phrases ending with "catchu":
    # - coo coo(l) catchu
    # - don't catchu
    # - go/gonna/gotta catchu
    # - (when) I catchu
    # - I'll/I'm catchu
    # - lemme/let me catchu
    # - [something] is so/really/very/etc. catchu (typo of catchy)
    # - need/tried/try(ing)/wait/want to catchu
    # - wanna/will catchu
    r"(coo cool?|don['’]t|go((nn|tt)a)?|i(['’](ll|m)|s [a-z]+)?|le(m|t )me|w(anna|ill)|"
    r"(need|tr(ied|y(ing)?)|w(a(it|nt))) to) +catchu|"
    # Phrases starting with "catchu":
    # - catchu all/at the/catchme/later
    # - (Ricky when I) catchu Ricky
    # - (Don't) catchu slippin (up)
    # - Catchu The Future
    # - "catchu up" but not "CatChu up close/next"
    # - catchu p (typo of "catch up")
    # - catchu with (typo of "catchup with")
    r"catchu +((@|at) the|all|catchme|later|ricky|slippin|the future|"
    r"u?p\b(?! (close|next)))|\b(to )?catchu with|\bpinky[ -]catchu\b",
    re.IGNORECASE,
)
FAKE_SOLDIER_GAME_RE = re.compile(
    r"\b(alien|(an?|the)( \w+\w){,5}|child|h(is|er)|m(ilitar)?y|p(lastic|sycho)|"
    r"s(tar|uper)|t(heir|oy)|winter) soldier game(?! cover)",
    re.IGNORECASE,
)
BAD_KEYWORDS_RE = re.compile(
    r"\b(arxiv\b|(europesays|newsbeep)\.com\b|zmedia\.(twitren\.com|jp)\b|"
    # Moths with species names containing "liella" substring
    r"#teammoth|"
    # Political keywords often used in "love live"/"Mia Taylor" false positives
    r"amerikkka|charlie ?kirk|democrats?\b|GOP\b|MAGAs?\b|netanyahu|republicans?|"
    r"trump\b|"
    # Gaza war victim fundraiser spam
    r"abed|ABD-GFM|GFM-ABD|kutt\.it/|"
    # Jel Kawasaki bot posts
    r"\[商品リンク\]|"
    # "Buy Anything From Amazon" spam
    r"zort\.my/|"
    # NSFW keywords
    r"bds&?m|c(am ?girl|haturbate|ock(s|\b)|um(ming|shot)?([^a-z]|\b))|di(aper|ck|ldo)|"
    r"(futanar|henta)i|jock[sa]traps?|nude|p(enis|regnant)|s(ex([^a-z]|\b)|lut)"
    # NSFW hashtags
    r")|#(ecchi|nsfw|porn|r18)",
    re.IGNORECASE,
)

# Prepopulate user list with only @lovelivenews.bsky.social just in case loading from
# file didn't work
LOVELIVENEWS_BSKY_SOCIAL = "did:plc:yfmm2mamtdjxyp4pbvdigpin"
DEDICATED_USERS = set({LOVELIVENEWS_BSKY_SOCIAL})
DEDICATED_USERS_MEDIA_ONLY: set[str] = set()

MMMINAMI_BSKY_SOCIAL = "did:plc:vgygtg6ozeaudtzilxihgpca"
NIGAI58_BSKY_SOCIAL = "did:plc:danvhqwcktfn47vhuh77kn2z"
SPLATER765_BSKY_SOCIAL = "did:plc:7zsqikdjppjczb6cfc3bmse6"

IGNORE_USERS: set[str] = set()
SOLOVON_DILL_BURGGIT_MOE_AP_BRID_GY = "did:plc:dvxbc7qhvo7c2vf3pmzmswd6"

uri = config.LOVELIVE_URI
dedicated_userlist_uri = config.LOVELIVE_INCLUDE_LIST_URI
dedicated_userlist_media_only_uri = config.LOVELIVE_MEDIA_INCLUDE_LIST_URI
ignore_list_uri = config.LOVELIVE_IGNORE_LIST_URI


def make_characters_pattern() -> re.Pattern:
    patterns: list[str] = []
    for name in CHARACTER_NAMES:
        first, last, first_last_only = name
        if not first_last_only:
            patterns.append(f"{last} ?{first}")

        patterns.append(f"{first} ?{last}")

    return re.compile(
        f"(?:^|[^@a-z])(?:{'|'.join(patterns)}|"
        r"^(?!.*\blazarus\b.*).*((?<!thank )you ?watanabe|"
        r"(?<!momo )(?<!shinichiro )(?<!akio )watanabe ?you(?!['’][a-z]+[a-z]|"
        r" ([a-z]+[a-z]n['’]?t|are|have|will)\b)).*|"
        r"^(?!.*\b(kong|wario)\b.*).*\bleah kazuno|#leahkazuno|"
        r"(?<!\nby )(?<!^by )(?<!post by )(?<!\bby: )mia taylor|"
        r"^(?!.*\bexpanse\b.*).*ren ?hazuki.*)\b",
        re.IGNORECASE | re.DOTALL,
    )


CHARACTERS_EN_RE = make_characters_pattern()


def filter(post: dict) -> bool:
    author = post["author"]
    if author in DEDICATED_USERS or (
        author in DEDICATED_USERS_MEDIA_ONLY and post_has_media_embeds(post)
    ):
        return True

    if author in IGNORE_USERS or author == SOLOVON_DILL_BURGGIT_MOE_AP_BRID_GY:
        return False

    record: models.AppBskyFeedPost.Record = post["record"]

    # Don't add posts that quote an ignored user's post and/or is a reply to ignored user
    quoted_post_or_reply_parent_uri = ""
    if isinstance(record.embed, models.AppBskyEmbedRecord.Main):
        quoted_post_or_reply_parent_uri = record.embed.record.uri
    elif isinstance(record.embed, models.AppBskyEmbedRecordWithMedia.Main):
        quoted_post_or_reply_parent_uri = record.embed.record.record.uri
    elif record.reply is not None:
        quoted_post_or_reply_parent_uri = record.reply.parent.uri

    if (
        quoted_post_or_reply_parent_uri
        and quoted_post_or_reply_parent_uri.split("/")[2] in IGNORE_USERS
    ):
        return False

    all_texts = "\n".join(get_post_texts(post))
    if not all_texts:
        return False

    return not BAD_KEYWORDS_RE.search(all_texts) and any(
        (
            LOVELIVE_NAME_EN_RE.search(all_texts) and not EXCLUDE_RE.search(all_texts),
            SUKUFEST_RE.search(all_texts) and "scrum" not in all_texts.lower(),
            SOLDIER_GAME_RE.search(all_texts)
            and not FAKE_SOLDIER_GAME_RE.search(all_texts),
            LOVELIVE_RE.search(all_texts),
            YOHANE_RE.search(all_texts)
            and not FAKE_YOHANE_RE.search(all_texts)
            and not (
                # Exclude replies (usually by @kanto141.bsky.social) that say "Hi Yohane"
                record.reply is not None
                and HI_YOHANE_RE.search(all_texts)
            ),
            CATCHU_RE.search(all_texts) and not FAKE_CATCHU_RE.search(all_texts),
            CHARACTERS_EN_RE.search(all_texts),
            post_has_media_embeds(post)
            and (
                (author == NIGAI58_BSKY_SOCIAL and "ちゃん" in all_texts)
                or (author == MMMINAMI_BSKY_SOCIAL and "うみこと" in all_texts)
            ),
            (
                author == SPLATER765_BSKY_SOCIAL
                and "goodnight everyone" in all_texts.lower()
            ),
        )
    )
