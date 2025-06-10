import re

from server import config
from server.algos._base import get_post_texts

LOVELIVE_NAME_EN_RE = re.compile(
    r"([^a-z0-9\-_]|\b)love ?live($|[^a-z0-9\-]|rs?\b)", re.IGNORECASE
)
LOVELIVE_RE = re.compile(
    r"love\s?live([!\s]*(blue ?bird|days|fans\b|heardle|idols|mention(ed)?\b|"
    r"references?|s(eries|(ifs)?orter|ky|oundtrack|potted|taff|u(nshine|per ?star))|"
    r"[ot]cg)| x\b)|"
    r"([^ク]|\b)(リンクライク)?ラブライ(ブ[!！\s]*(サンシャイン|スーパースター)?|バー)|"
    r"\b(thank you|(like|mis)s) love ?live\b|#lovelive_|lovelive(-anime|_staff)|"
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
    r"音ノ木坂?|otonokizaka|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)[μµ]['’‘`´′]s|"
    r"高坂\s?穂乃果|絢瀬\s?絵里|南\s?ことり|園田\s?海未|星空\s?凛|西木野\s?真姫|東條\s?希|"
    r"小泉\s?花陽|矢澤\s?にこ|nico\snico\sni+\b|#niconiconi+\b|エリーチカ|\belichika\b|"
    r"にこりんぱな|nicorinpana|金曜凛ちゃんりんりんりん|火曜日かよちゃん|"
    r"snow\s?halation([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"(^|[^a-z\u00C0-\u024F\u1E00-\u1EFF\-])a[-\u2010]rise([^a-z\u00C0-\u024F\u1E00-\u1EFF\-]|$)|"
    r"綺羅\s?ツバサ|優木\s?あんじゅ|統堂\s?英玲奈|"
    # Love Live! Sunshine!!
    # NOTE: AZALEA not included due to too many false positives
    r"(^|[^三土])浦の星女?|uranohoshi|aq(ou|uo)rs|cyaron!?\b|guilty\s?kiss([^a-z]|$)|"
    # YYY (You, Yoshiko/Yohane, RubY)
    r"(?<!わい)(?<!わーい)わいわいわい(?!わー?い)|"
    # AiScReam (Ayumu, Shiki, Ruby)
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)ai[♡ ]?scream\b|愛♡スクリ〜ム|"
    r"幻(日のヨハネ|ヨハ)|genjitsu\s?no\s?yohane|sunshine\sin\sthe\smirror|"
    r"^(?!(.|\n)*(shaman ?king|touhou)(.|\n)*$)((.|\n)*\byohane\b(.|\n)*)|"
    r"高海\s?千歌|桜内\s?梨子|松浦\s?果南|黒澤\s?(ダイヤ|ルビィ?)|渡辺\s?曜|津島\s?善子|"
    r"国木田\s?花丸|小原\s?鞠莉|"
    r"がんば(ルビ|るび)|(^|[^@])ganbaruby|(daily|today['’]s) maru\b|maru's month|"
    r"(永久|\beikyuu\s?)hours|"
    r"(?<!\bRT @)(?<!x.com/)saint\s?snow([^a-z]|$)|"
    r"鹿角\s?(理亞|聖良)|"
    # Nijigasaki
    r"虹ヶ咲(?!学園交通運輸研究部)|ニジガク|(アニ|エイ)ガサキ|(あに|えい)がさき|にじ(よん|ちず)|"
    r"(nij|an|e)igasaki|niji(chizu|gaku|yon)|a・zu・na|qu4rtz|"
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(diver"
    r" ?diva|r3birth)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"tokimeki r(unners|oadmap to the future)|"
    r"高咲\s?侑|上原\s?歩夢|中須\s?かすみ|桜坂\s?しずく|朝香\s?果林|宮下\s?愛|近江\s?(彼方|遥)|"
    r"優木\s?せつ菜|中川\s?菜々|エマ・?ヴェルデ|天王寺\s?璃奈|三船\s?栞子|ミア・?テイラー|鐘\s?嵐珠|"
    # Love Live! Superstar!!
    r"([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(tuto)?liella(?!(nd| kelly))[!！]?|"
    r"結ヶ丘|yuigaoka|5yncri5e!?|kaleidoscore"
    r"|([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)(?<!i )(?<!to )(?<!will )"
    r"catchu!?(?! later)([^a-z\u00C0-\u024F\u1E00-\u1EFF]|\b)|"
    r"トマカノーテ|tomakanote|スパスタ[3３]期|"
    r"澁谷\s?かのん|唐\s?可可|嵐千\s?砂都|平安名\s?すみれ|葉月\s?恋|桜小路\s?きな子|米女\s?メイ|"
    r"若菜\s?四季|鬼塚\s?(夏美|冬毬)|ウィーン・?マルガレーテ|"
    r"ク[ウゥ]ク[ウゥ]ちゃん?|oninatsu|オニナッツ|"
    r"sunny\s?pas(sion)?(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"sunnypa(\b|[^a-z\u00C0-\u024F\u1E00-\u1EFF])|"
    r"聖澤悠奈|柊\s?摩央|"
    # Link! Like! Love Live! / Hasunosora
    # リンクラ but not リンクライン or katakana phrases with リンクラ character sequence
    r"(^|[^\u30a1-\u30f6\u30fc])リンクラ(?!イン|ボ|ベル)|"
    r"hasu\s?no\s?sora|蓮ノ(空|休日)|"
    r"^(?!(.|\n)*\broses?\b(.|\n)*$)((.|\n)*\bcerise\sbouquet\b(.|\n)*)|"
    r"スリーズブーケ|dollches(tra(?!-art)|\b)|ドルケストラ|mira-cra\spark!?|"
    r"みらくらぱーく[!！]?|\bkahomegu\b|かほめぐ(♡じぇらーと)?|\bedel\s?note\b|"
    r"るりのとゆかいなつづりたち|#新メンバーお披露目105期|"
    r"乙宗\s?梢|夕霧\s?綴理|藤島\s?慈|日野下\s?花帆|村野\s?さやか|大沢\s?瑠璃乃|百生\s?吟子|"
    r"徒町\s?小鈴|安養寺\s?姫芽|大賀美沙知|桂城\s?泉|セラス[・\s]?柳田[・\s]?リリエンフェルト|"
    # Love Live! Bluebird
    # NOTE: "Love High School" not included due to too many false positives
    r"いきづらい部|イキヅライブ|ikizu ?(live|raibu)|love学院|"
    r"高橋\s?ポルカ|麻布\s?麻衣|五桐\s?玲|駒形\s?花火|金澤\s?奇跡|調布\s?のりこ|春宮\s?ゆくり|"
    r"此花\s?輝夜|山田\s?真緑|佐々木\s?翔音|"
    r"\b(polka_lion|My_Mai_Eld|G_Akky304250|hanabistarmine|MiracleGoldSP|Noricco_U|"
    r"Yukuri_talk|Rollie_twinkle|LittlegreenCom|ShaunTheBunny)([^a-z]|$)|"
    # Concerts
    r"異次元フェス|ijigen\sfest?|#llsat_|"
    # Community stuff
    r"\b(team )?onib(e|ased)\b|schoolido\.lu|idol\.st(?!/user/\d+)|#HasuTH_Tran",
    re.IGNORECASE,
)
SUKUFEST_RE = re.compile(
    r"(^|[^マア])スクフェス(?!札幌|大阪|[福盛]岡|神奈川|新潟|仙台|三河|沖縄|金沢|香川)"
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
        ("Yoshiko", "Tsushima", False),
        ("Hanamaru", "Kunikida", False),
        ("Mari", "Ohara", False),
        # Saint Snow
        ("Kazuno", "Leah", True),
        # NOTE: Leah Kazuno included in pattern builder to try to skip posts about a
        # speedrunner named "LeahKazuno"
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
        # NOTE: Keke Tang included in pattern builder to prevent posts containing
        # "arxiv" anywhere in post from being added
        ("Tang", "Keke", True),
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
    # - I('d)/he/she/they/you (all)/y'all/you'll/we (all/both)/gotta/got to/who/people/
    #   [plural word] that
    r"\b((i|s?he|they)(['’]d)?|y(ou(['’]ll)?|(ou |['’])all)|we( (all|both))?|"
    r"got(ta| to)|who|people|[a-z]{3,}s( that)?)"
    # - *ing/*ly/bloody/also/always/do(es)/don't/happen(ed)/just/still/tend to/too/will/
    #   would('ve)/... and
    r"(,? ([a-z]{3,}(ing?|ly)|just|al(so|ways)|(st|w)ill|do(es)?|bloody|don['’]t|"
    r"((ha(ve|ppen(ed)?)|used?|grew) t|s|t(o|end t))o|would(['’]ve)?|even|"
    r"[a-z]+[a-z] (and|&))\,?)*"
    # - love live [something]/love liver(s)/love Live (as in Ableton Live software)
    r" ((love )+live((?! (so |and|but)\b),? &? ?#?\w+\b|rs?)|"
    r"love live($|[^\s\w]| \w+))|"
    # Anyone ... love live music?
    r"anyone( .+)? love live music\?|"
    # "love live music" at start of sentence or after "freaking/really/bloody/etc." but
    # not "love live music is"
    r"(^|([^\w ]|([a-z]+(ng?|ly)|bloody) ))love live music(?! is)\b|"
    # "and love live [something]" at end of sentence
    r"and love live [a-z]+[a-z]([^\w ]|$)|"
    # Words/phrases starting with "love live"
    r"\blove live ("
    # - love live action
    # - love Live A Live (video game title)
    # - love "LIVE and FALL" (album by Xdinary Heroes)
    r"a(ction|nd fall| live)|"
    # - Love Live Bleeding (typo of "Love Lies Bleeding")
    r"bleeding|"
    # - love live die
    # - love "Live and Let Die" (movie title)
    # - love "Live Die Repeat" (alt name of "Edge of Tomorrow" movie)
    r"((and|&) let )?die( repeat)?\b|"
    # - love live entertainment
    r"entertainment|"
    # - love live fact checking
    r"fact checking|"
    # - love live him
    r"him|"
    # - Love Live Italian
    # - love live within
    r"(italia|withi)n|"
    # - love live jazz
    r"jazz|"
    # - love live (and) laugh
    r"(and )?laugh|"
    # - love live life/local/long/loud (music)
    # - "love live love" but not "love live love wing bell"
    r"l(ife|o(cal|ng|ud( music)?|ve(?! wing bell)))|"
    # - "love live music" at end of sentence
    # - love live music at
    r"music ([^\w ]|$|at\b)|"
    # - love live oak(s)
    r"oaks?|"
    # - love live service
    # - love live streaming/streams
    r"s(ervice|tream(ing|s))|"
    # - love live tables/theater/TV/television
    # - love "Live to Tell" (song by Madonna)
    # - love "Live Through This" (usually an album by Hole)
    r"t(ables|elevision|h(eat(er|re)|rough this)|o tell|v)|"
    # - "love live the" as a typo of "long live the" but not "Love Live the School Idol"
    #   or "Love Live the Musical"
    r"the\b(?! school idol|musical)|"
    # - love live tour/your
    r"[ty]our|"
    # - love live bands/gigs/mealworms/performances/shows/sports
    # - "Love Live in/from Paris" (misspelling of "Lover (Live from Paris)" album by
    #   Taylor Swift)
    r"(band|gig|mealworm|performance|s(how|port)|(in|from) pari)s)|"
    # [Artist] - [song name ending with "love"] live
    r"\w+ [\-\u2013] .+ love live\b[^!]|"
    # that/just love liver (body part or food)
    r"\b(jus|tha)t ([a-z]+[a-z] )?love liver\b|"
    # Words/phrases ending with "love live"
    r"\b("
    # - about/confess(ed/es/ing) his/her/their love live (usually typo of "about his/
    #   her/their love life/lives")
    r"(about|confess[a-z]*) (h(er|is)|their)|"
    # - absolutely love live [something]
    # - "All Your Love" live (usually song by Otis Rush or any song name ending with
    #   that phrase)
    r"a(bsolutely|ll your)|"
    # Art(ist(s))/band(s)/music/people/[some plural word] I/you/etc. (... and) love live
    r"(art(ist)?|band|music|people|[a-z]+s) (i|you|they)( ([a-z]+[a-z],? )+(and|&))?|"
    # - "Can't Buy Me Love" live (usually song by the Beatles)
    # - "Can't Hide Love" live (different songs by different artists)
    # - "Computer Love" live (song by Kraftwerk)
    r"c(an['’]?t (buy me|hide)|omputer)|"
    # - "Dangerously in Love" live (album by Beyonce)
    # - "Drunk in Love" live (song by Beyonce)
    # - "I'm Not in Love" live (usually song by 10cc)
    # - who live in love live (1 John 4:16)
    r"(d(angerously|runk)|i['’]?m not|who live) in|"
    # - "Darker My Love" live (song by T.S.O.L.)
    # - "Darkness at the Heart of My Love" live (song by Ghost)
    # - does not/doesn't love live [something]
    r"d(ark(er my|ness at the heart of my)|o(es)?( not|n['’]t))|"
    # - fight love live (usually Filoli, California historical marker)
    # - "Fool for Love" live
    # - "Friday I'm In Love" live (usually song by The Cure)
    r"f(ight|ool for love|riday i['’]?m in)|"
    # - Gerry Love live (British live music performer)
    r"ger(ard|ry)|"
    # - his love live (usually typo of "his love life")
    r"his|"
    # - (that) I('d) love live [something] (all other cases not caught by the Great "I
    #   love live [something]" Hoarde pattern)
    r"(that)?\bI(['’]d)?|"
    # - "I Feel Love" live (usually song by Donna Summer)
    r"\bI feel|"
    # - laugh/let (that)/live love live
    # - "Lexicon of Love" live (album by ABC)
    r"l(augh|et( that)?|ive|exicon of)|"
    # - "life love live" but not "Link Life Love Live"
    r"(?<!link )life|"
    # - mad love live
    # - Mike Love live (some reggae artist)
    r"m(ad|ike)|"
    # - "No Loss, No Love" live (song by Spiritbox)
    r"\bno loss,? no|"
    # - "Prophecy x This Love" live (song by Taylor Swift)
    r"prophecy x this|"
    # - Radical Love Live (some religious podcast with a Bluesky presence)
    # - really love live [something]
    # - Rinku Love Live (NSFW/R18 AI artist sometimes featured on @mikubot.bsky.social)
    r"r(adical|eally|inku)|"
    # - Savage Love Live (sex advice podcast by Dan Savage)
    # - show some love live
    # - "Somebody to Love" live (usually song by Queen or Jefferson Airplane or any song
    #   name ending with that phrase)
    # - "Songs of Love Live" (album by Mark Eitzel)
    # - Stone Love live (usually Jamaican DJ group)
    r"s(avage|how some|o(mebody to|ngs of)|tone)|"
    # saw [artist name] perform [song name ending with "Love"] live
    r"\bsaw .+ perform .+|"
    # - that/what kind of love live (sometimes typo of "that/what kind of love life")
    r"[tw]hat kind of|"
    # - they love live [something] (all other cases not caught by the Great "I love
    #   live [something]" Hoarde pattern)
    # - "The House of Love" live (usually song by Christine)
    # - "The Book of Love" live (usually song by Peter Gabriel or The Magnetic Fields)
    r"the(y| (book|house) of)|"
    # - would love live [something] (all other cases not caught by the Great "I love
    #   live [something]" Hoarde pattern)
    # - "Wasted Love" live (song by JJ)
    # - "We Found Love" live (song by Rihanna feat. Calvin Harris or any song name
    #   ending with that phrase)
    # - "Whole Lotta Love" live (usually song by Led Zeppelin)
    r"w(asted|e found|hole lotta|ould)|"
    # - you are/you're in love live
    r"you( a|['’])re in) love live\b|"
    # perform(s/ed/ing/ance of)/sing(s/ing) [song name ending with "Love"] live at/on/
    # in(side)/outside
    r"(perform(ance of|ed|ing|s)?|sing(ing|s)) .+ (?<!from )love live"
    r"($| +(at|[io]n|(in|out)side)\b)|"
    # if you live in/near/around [place name] and love live music/comedy
    r"((you(\s+liv|['’]r)e\s+(in|near|around)\s+.+\s+)?and\s+|[^\w ]\s*)love live"
    r"( (music|comedy)|r)(?! ((i|wa)s)|are)\b|"
    # whether you('re) ... or (just) love live [something]
    r"whether you.+ or (just )?love live |"
    # "(and) love live [something]" as a typo of "long live [something]" or "love love
    # love love [something]" but not "(and) love live in/is/are/song(s)", "love liver"
    # at beginning of sentence
    r"(([^\w\s:]+? *?|^)(and )?(love )+liver?(?! (i[ns]|are|songs?) )|"
    r"([^\w\s'’,:]+?  ?|^)(love )+live,)( #?[a-z\-'’]+)+ ?([^\w ]|$)|"
    # "love love live" at beginning of sentence
    r"([^\w\s]+?  ?|^)love (love )+live\b|"
    # ... and love live(s) here/there
    r" (and|&) love lives? t?here\b|"
    # may your/his/her/their ... love live (on)
    r"\bmay (h(is|er)|(thei|you)r) (.+ )?love live |"
    # may/my love live in
    r"\bma?y love live in\b|"
    # her/his/our/their/who(se)/yet ... (and) love live in/on/with
    r"(h(er|is)|(y?ou|thei)r|who(se)?|yet|\w+['’]s)( ([a-z]+[a-z]|.+ (and|&)))?"
    r" love lives? ([io]n|with)|"
    # "his/her/their/you(r) (...ing) love live" (sometimes a typo of "love life/lives")
    # before period/comma/quote mark/"is/was" or at end of post
    r'\b(h(er|is)|their|your?)( [a-z]+ing)? love live([.,"”]|$| (i|wa)s\b)|'
    # playing [video game title ending with "Love"] live (on/at)
    r"\bplay(ing)? .+ love live (at|on)|"
    # I('d/'ve) got/need/etc. to/gotta hear/have heard [song name ending with "Love"] live
    r"\bI(['’]d|ve)? ((([a-z]+ ){,2}to|gotta) hear|(have )?heard) ([\w'’]+ )+love live|"
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
    # lovelive.com/net/org/etc.
    r"\blovelive\.[a-z]+[a-z]\b",
    re.IGNORECASE | re.MULTILINE,
)
NSFW_KEYWORDS_RE = re.compile(
    r"\b(bds&?m|c(ock(s|\b)|um(ming)?\b)|di(aper|ck|ldo)|(futanar|henta)i|GOP\b|n(sfw|ude)|"
    r"p(enis|regnant)|republicans?|sex\b|trump)",
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
        f"(?:^|[^@a-z])(?:{'|'.join(patterns)}|"
        r"^(?!(.|\n)*lazarus(.|\n)*$).*\b(?<!thank )you ?watanabe.*$|"
        r"\b(?<!momo )(?<!shinichiro )(?<!akio )watanabe ?you(?!['’][a-z]+[a-z]|"
        r" ([a-z]+[a-z]n['’]?t|are|have)\b)|leah kazuno|"
        r"(?<!^by )(?<!post by )mia taylor)\b|"
        r"^(?!(.|\n)*arxiv(.|\n)*$).*\bkeke ?tang\b.*$",
        re.IGNORECASE | re.MULTILINE,
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
