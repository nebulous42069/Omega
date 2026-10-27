"""Best-effort channel-name classification; explicit country labels precede brands."""
import re
import unicodedata

COUNTRIES = (
    ('USA', r'\b(?:USA|United States|US)\b'),
    ('UK', r'\b(?:UK|United Kingdom|Britain|British)\b'),
    ('Ireland', r'\b(?:Ireland|Irish)\b'),
    ('Canada', r'\bCanada\b|\bCA$'),
    ('Australia', r'\bAustralia\b|\bAU$'),
    ('New Zealand', r'\bNew Zealand\b|\bNZ$'),
    ('Germany', r'\b(?:Germany|Deutschland)\b|\bDE$'),
    ('Austria', r'\bAustria\b|\bAT$'),
    ('France', r'\bFrance\b|\bFR$'),
    ('Italy', r'\b(?:Italy|Italia)\b|\bIT$'),
    ('Spain', r'\b(?:Spain|Espana)\b|\bES$'),
    ('Portugal', r'\bPortugal\b|\bPT$'),
    ('Netherlands', r'\b(?:Netherlands|Holland)\b|\bNL$'),
    ('Belgium', r'\bBelgium\b|\bBE$'),
    ('Poland', r'\bPoland\b|\bPL$'),
    ('Czechia', r'\b(?:Czechia|Czech Republic|Czech)\b|\bCZ$'),
    ('Slovakia', r'\bSlovakia\b|\bSK$'),
    ('Denmark', r'\bDenmark\b|\bDK$'),
    ('Sweden', r'\bSweden\b|\b(?:SE|SW)$'),
    ('Norway', r'\bNorway\b|\bNO$'),
    ('Finland', r'\bFinland\b|\bFI$'),
    ('Serbia', r'\bSerbia\b|\bRS$'),
    ('Croatia', r'\bCroatia\b|\bHR$'),
    ('Bulgaria', r'\bBulgaria\b|\bBG$'),
    ('Romania', r'\bRomania\b|\bRO$'),
    ('Greece', r'\bGreece\b|\bGR$'),
    ('Hungary', r'\bHungary\b|\bHU$'),
    ('Turkey', r'\b(?:Turkey|Turkiye)\b|\bTR$'),
    ('Russia', r'\bRussia\b|\bRU$'),
    ('Ukraine', r'\bUkraine\b|\bUA$'),
    ('Brazil', r'\b(?:Brazil|Brasil)\b|\bBR$'),
    ('Mexico', r'\bMexico\b|\bMX$'),
    ('Argentina', r'\bArgentina\b|\bAR$'),
    ('Chile', r'\bChile\b|\bCL$'),
    ('Colombia', r'\bColombia\b|\bCO$'),
    ('India', r'\bIndia\b|\bIN$'),
    ('Pakistan', r'\bPakistan\b|\bPK$'),
    ('Bangladesh', r'\bBangladesh\b|\bBD$'),
    ('Malaysia', r'\bMalaysia\b|\bMY$'),
    ('South Africa', r'\bSouth Africa\b|\bZA$'),
    ('Saudi Arabia', r'\b(?:Saudi Arabia|Saudi)\b'),
    ('UAE', r'\b(?:UAE|United Arab Emirates|Abu Dhabi|Dubai)\b'),
    ('Qatar', r'\b(?:Qatar|Alkass)\b'),
    ('Israel', r'\bIsrael\b|\bIL$'),
)

BRANDS = (
    ('Ireland', r'\bRTE\b|\bVirgin Media (?:One|Two|Three)\b'),
    ('UK', r'\b(?:BBC|ITV|E4|S4C|MUTV)\b|\bSky (?:Sports|Cinema|News|Arts|Showcase)|\b(?:Film4|Channel [45]|Premier Sports)\b'),
    ('Canada', r'\b(?:TSN\s*\d*|Sportsnet|RDS|TVA|CBC|CTV)\b'),
    ('Australia', r'\b(?:Fox League|Fox Footy|Fox Cricket|Fox Sports [5][0-9]{2}|ABC Australia)\b'),
    ('New Zealand', r'\bSky Sport NZ\b'),
    ('Poland', r'Polsat|\bTVP\b|\bTVN(?:24)?\b|Motowizja'),
    ('France', r'\b(?:TF1|M6|RMC|BFM|CNews|LCI)\b|L.Equipe'),
    ('Spain', r'Movistar|LaLiga|Teledeporte|Mundotoro'),
    ('Portugal', r'\b(?:Sport TV|Benfica TV|Sporting TV|Porto Canal)\b'),
    ('Brazil', r'Globo|Bandsports|SporTV'),
    ('India', r'Star Sports|Sony Ten'),
    ('Pakistan', r'\bPTV\b|Ten Sports'),
    ('Bangladesh', r'\bT Sports\b'),
    ('Malaysia', r'\bAstro\b'),
    ('South Africa', r'SuperSport|\bDSTV\b'),
    ('USA', r'\b(?:ESPN(?:2|U|ews|News)?|ABC|NBC|CBS|FOX|MSNBC|CNBC|PBS|CW|Newsmax|NESN|MSG|SNY|MASN)\b|Fox Business|FanDuel|YES Network|Tennis Channel|C.SPAN'),
)

CATEGORIES = (
    ('Adult', r'\b(?:18\+|Adult|XXX|Playboy|Hustler|Penthouse)\b'),
    ('Music', r'\b(?:MTV|VH1|CMT|Music|Musik|Nick Music)\b'),
    ('Kids', r'Disney|Nickelodeon|Nicktoons|TeenNick|\bNick\b|Cartoon|Boomerang|\bKids\b|HBO Family|Discovery Family'),
    ('Sports', r'Sport|ESPN|beIN|DAZN|Deport|Calcio|Football|Fussball|Futebol|Soccer|Rugby|Basket|Hockey|Cricket|Willow|Tennis|Golf|Racing|Motorsport|Formula|MotoGP|\b(?:NFL|NBA|NHL|MLB|WWE|UFC|MMA|F1|TSN\d*|RDS|NESN|MSG|SNY|MASN|MUTV|TUDN|Alkass)\b|Fight|Boxing|FanDuel|YES Network|SEC Network|ACC Network|Big Ten|Liverpool TV|LFC TV|Benfica TV|Sporting TV|Porto Canal|LaLiga|Mundotoro|L.Equipe'),
    ('News', r'News|CNN|MSNBC|CNBC|Fox Business|Weather|Headline|BFM|\bLCI\b|CNews|TVN24|C.SPAN|Noticias|Nachrichten|BBC Parliament'),
    ('Movies', r'Sky Cinema|HBO|Showtime|Starz|Cinemax|\bTCM\b|Movies|Cinema|\bFilm\b|Film4|FilmBox|\bKino\b|MGM\+|Sundance|Hallmark'),
    ('Documentary & Lifestyle', r'Discovery|National Geographic|Nat Geo|Animal Planet|Smithsonian|History|Science|HGTV|Food Network|Cooking|Travel Channel|\bTLC\b|Investigation|Crime|Sky Arts|\bArte\b'),
    ('Entertainment', r'\b(?:ABC|NBC|CBS|FOX|PBS|CW|BBC|ITV|E4|RTE|CBC|CTV|TNT|TBS|USA Network|AMC|FX|FXX|Bravo|BET|A&E|Comedy Central|Lifetime|Dave|Gold|W|TF1|M6|TVP|TVN)\b|Channel [45]|Sky Showcase|Globo'),
)


def display_name(name):
    return re.sub(r'\s*[-|:]?\s*\bID\s*:\s*\d+\s*$', '', name, flags=re.I).strip()


def normalized(name):
    name = display_name(name)
    name = ''.join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c))
    # Remove quality labels and surrounding punctuation so country suffix tags match.
    name = re.sub(r'\b(?:FHD|UHD|HD|SD|4K|1080p|720p)\b', '', name, flags=re.I)
    return ' '.join(re.sub(r'[\[\]()|:]', ' ', name).split()).strip(' -')


def details(name):
    text = normalized(name)
    country = 'UK' if re.fullmatch(r'5 USA',text,re.I) else ('USA' if re.match(r'BBC America\b',text,re.I) else None)
    country = country or next((label for label,pattern in COUNTRIES if re.search(pattern,text,re.I)), None)
    if not country and re.search(r'\bInternational\b', text, re.I):
        country = 'International'
    if not country:
        country = next((label for label,pattern in BRANDS if re.search(pattern,text,re.I)), 'International')
    category = next((label for label,pattern in CATEGORIES if re.search(pattern,text,re.I)), 'Other')
    return category, country


def group_for(name):
    category, country = details(name)
    return ('Sports' if category == 'Sports' else 'Channels') + '-' + country + '-'


def sort_key(item):
    channel,name = item
    category,country = details(name)
    category = 'Sports' if category == 'Sports' else 'Channels'
    order = ('Channels', 'Sports')
    # Numeric fragments sort naturally within each group.
    natural = tuple((1,int(p)) if p.isdigit() else (0,p.casefold()) for p in re.split(r'(\d+)',name))
    return order.index(category), country.casefold(), natural, int(channel)
