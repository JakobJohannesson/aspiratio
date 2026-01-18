"""
Helpers for searching and validating investor relations URLs.
"""
import re
from urllib.parse import urlparse, urlunparse
import requests
from bs4 import BeautifulSoup
import unicodedata
from ddgs import DDGS

PATH_PATTERNS = [
    r"/investors",
    r"/investor-relations",
    r"/investerare",
    r"/shareholders",
    r"/investors-media",
    r"/investerare-och-media",
    r"/financial-data",
    r"/investor"
]

IR_KEYWORDS = ["investor", "ir", "investerare", "shareholder", "investors-media", "group"]

# Page content validation - terms that should appear on a real IR page
IR_PAGE_CONTENT_TERMS = [
    # English
    'annual report', 'financial report', 'quarterly report', 'investor relations',
    'shareholders', 'stock', 'share price', 'dividend', 'earnings', 'financial statements',
    'corporate governance', 'board of directors', 'annual general meeting', 'agm',
    'press release', 'financial calendar', 'reports and presentations',
    # Swedish
    'årsredovisning', 'kvartalsrapport', 'investerare', 'aktieägare', 'aktiekurs',
    'utdelning', 'bolagsstyrning', 'styrelse', 'årsstämma', 'finansiell kalender',
    'rapporter', 'pressmeddelande'
]

# TLD configuration for Swedish company search
PREFERRED_TLDS = ['se', 'com']  # Heavy boost
ACCEPTABLE_TLDS = ['net', 'org', 'eu', 'io']  # Small boost
SUSPICIOUS_TLDS = ['cn', 'ru', 'fr', 'de', 'jp', 'kr', 'tw', 'tr', 'mx', 'ar', 'cl', 
                   'co', 'in', 'br', 'hk', 'pl', 'ua', 'it', 'es', 'pt', 'nl', 'be',
                   'at', 'ch', 'cz', 'hu', 'ro', 'bg', 'gr', 'th', 'vn', 'id', 'my', 'ph']

BAD_DOMAINS = [
    # Financial aggregators
    'wikipedia.org', 'quartr.com', 'placera.se', 'researchpool.com',
    'marketscreener.com', 'bloomberg.com', 'reuters.com', 'yahoo.com',
    'morningstar.com', 'nasdaq.com', 'investing.com', 'shareholdersfoundation.com',
    'alphaspread.com', 'annualreports.com', 'businesswirechina.com', 'businesswire.com',
    'prnewswire.com', 'globenewswire.com', 'news.cision.com', 'finanzen.net', 'marketwatch.com',
    'thewallstreetjournal.com', 'forbes.com', 'ft.com', 'financialtimes.com', 'wsj.com', 'barrons.com', 'inderes.se',
    'capitoltrades.com', 'seekingalpha.com', 'financialreports.eu', 'grokipedia.com', 'slidegenius.com',
    'simplywall.st', 'wallstreetzen.com', 'tipranks.com', 'zacks.com', 'fool.com',
    'tracxn.com', 'zaubacorp.com', 'dnb.com', 'tradingview.com', 'allabolag.se', 'hitta.se', 'eniro.se',
    'proff.se', 'bolagsfakta.se', 'finanznachrichten.de', 'advfn.com', 'investorshub.advfn.com', 'aum13f.com',
    'watchlistnews.com', 'telegraph.co.uk', 'thelincolnianonline.com', 'marketwirenews.com', 'trendspider.com',
    'investorshangout.com', 'startuprise.co.uk', 'aktiedysten.dk', 'esgnews.com', 'stockopedia.com', 'finanzen100.de',
    'nyemissioner.se', 'trivano.com', 'dagensps.se', 'affarsvarlden.se', 'webbinvestor.se', 'borsvarlden.com',
    'nordnet.se', 'rapidus.se', 'cotf.se', 'daytrading.se', 'hello-safe.se', 'borskollen.se', 'vfb.be',
    'centralcharts.com', 'cybo.com', 'onemainfinancial.com', 'nissanfinance.com', 'atmeta.com', 'valuespectrum.com',
    'epicos.com', 'gurufocus.com', 'stockinvest.us', 'walletinvestor.com', 'maritime-executive.com', 'referenceforbusiness.com',
    'fiscal.ai', 'invvest.co', 'etoro.com', 'spectrumone.com', 'sweatyourassets.biz', 'breadfinancial.com', '3blmedia.com',
    'focus.ua', 'guggenheiminvestments.com', 'croyezimmigration.com', 'biggerpockets.com', 'dendera.se', 'kthholding.se',
    'seafireab.com', 'igrene.se', 'finansnyheterna.se', 'ectinresearch.com', 'guventures.com', 'tadviser.com', 'telecomlead.com',
    'avanza.se', 'di.se', 'ariva.de', 'stockpicker.se',
    
    # Search engines and portals
    'google.com', 'google.se', 'google.fr', 'google.de', 'google.co.uk', 'google.nl', 'google.fi', 'google.no', 'google.dk',
    'bing.com', 'duckduckgo.com', 'baidu.com', 'yandex.com', 'yandex.ru',
    'facebook.com', 'twitter.com', 'x.com', 'linkedin.com', 'instagram.com', 'youtube.com', 'tiktok.com',
    
    # Chinese Q&A and forums
    'zhihu.com', 'zhidao.baidu.com', 'muchong.com', 'bbs.vivo.com.cn', 'tieba.baidu.com',
    
    # Forums and communities
    'reddit.com', 'quora.com', 'stackoverflow.com', 'stackexchange.com',
    'forum.', 'community.', 'kundforum.', 'bbs.', 'boards.',
    
    # App stores, tech support, accounts
    'apps.apple.com', 'play.google.com', 'support.google.com', 'accounts.google.com',
    'support.microsoft.com', 'answers.microsoft.com', 'support.apple.com',
    'chrome.google.com', 'web.whatsapp.com', 'office.com', 'brave.com',
    
    # News and media
    'bbc.com', 'bbc.co.uk', 'cnn.com', 'nytimes.com', 'theguardian.com',
    'netflix.com', 'hulu.com', 'spotify.com', 'britannica.com',
    
    # Travel and booking
    'airbnb.com', 'booking.com', 'tripadvisor.com', 'expedia.com',
    'virginvoyages.com', 'airport-london-heathrow.com',
    
    # Gaming and entertainment
    'crazygames.com', 'steam.com', 'twitch.tv', 'discord.com',
    
    # Random noise sites
    'cleancss.com', 'programmetele.com', 'gratistravtips.se', 'onthisday.com',
    'dictionary.cambridge.org', 'scienceshumaines.com', 'commentouvrir.com',
    'hausbau-forum.de', 'byggahus.se', 'agrofoto.pl', 'unchi-co.com',
    'es.ccm.net', 'mufhras.com', 'sourcinghaus.com', 'newplacehotel.co.uk',
    'github.com', 'gitlab.com', 'bitbucket.org',
    
    # Finance infrastructure (not company IR)
    'ir.financialhearings.com',
]

# Pattern to catch all Google country domains (google.XX)
GOOGLE_DOMAIN_PATTERN = re.compile(r'^(www\.)?google\.[a-z]{2,3}$', re.IGNORECASE)

# Adult/porn sites - should never appear as IR URLs
ADULT_DOMAINS = [
    'onlyfans.com', 'pornhub.com', 'xvideos.com', 'xnxx.com', 'xhamster.com',
    'redtube.com', 'youporn.com', 'tube8.com', 'spankbang.com', 'chaturbate.com',
    'stripchat.com', 'cam4.com', 'livejasmin.com', 'bongacams.com', 'myfreecams.com',
    'fansly.com', 'manyvids.com', 'clips4sale.com', 'iwantclips.com',
]

# Patterns to detect adult content in URLs
ADULT_PATH_PATTERNS = [
    r'/r/\w*porn\w*', r'/r/\w*nsfw\w*', r'/r/\w*xxx\w*', r'/r/\w*nude\w*',
    r'/r/\w*gonewild\w*', r'/r/\w*sex\w*', r'/r/\w*hentai\w*',
]

PRESS_KEYWORDS = ['/news/', '/press-release', '/pr/', '/press/', '/article/', '/stories/', '/media/', '/blog/', '/announcement/', '/medya/', '/hikayeler/', '/tiedotteet/']

EVENT_KEYWORDS = ['call', 'webcast', 'presentation', 'q1', 'q2', 'q3', 'q4', '2023', '2024', '2025', 'agm', 'egm', 'nomination-committee', 'contacts-information', 'key-ratios', 'financial-reports']

def normalize_text(text):
    # Convert to lowercase and replace accented characters with base characters
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                  if unicodedata.category(c) != 'Mn')
    # Replace common Swedish characters that might not be handled by NFD correctly in all environments
    text = text.replace('ä', 'a').replace('ö', 'o').replace('å', 'a')
    return re.sub(r'[^a-z0-9]', '', text)

def simplify_ir_url(url):
    try:
        parsed = urlparse(url)
        path = parsed.path
        # Common IR root segments
        ir_roots = ['/investor-relations', '/investors', '/investerare', '/ir', '/shareholders', '/investor']
        
        # Find the first occurrence of any IR root in the path
        best_root_end = -1
        for root in ir_roots:
            idx = path.lower().find(root)
            if idx != -1:
                # We want to keep the root segment itself
                # e.g. /investor-relations/foo -> /investor-relations/
                end_idx = idx + len(root)
                # If there's a slash after it, include it
                if end_idx < len(path) and path[end_idx] == '/':
                    end_idx += 1
                
                if best_root_end == -1 or idx < best_root_end:
                    best_root_end = end_idx
        
        if best_root_end != -1:
            new_path = path[:best_root_end]
            if new_path != path:
                return urlunparse(parsed._replace(path=new_path, query='', fragment=''))
    except:
        pass
    return None

def get_score(url, company_name):
    score = 0
    details = []
    try:
        # Pre-process company name
        norm_name = re.sub(r'\s+(?<![Aa])[ab]$', '', company_name, flags=re.IGNORECASE)
        match_name = re.sub(r'\s+(ab|ltd|corp|inc|group|abp|as|asa|sa|nv|plc)$', '', norm_name, flags=re.IGNORECASE)
        norm_name_simple = normalize_text(match_name)

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        domain_simple = re.sub(r'[^a-z0-9]', '', domain)
        path = parsed.path.lower()
        
        # Immediately reject Google domains with massive penalty
        if GOOGLE_DOMAIN_PATTERN.match(parsed.netloc):
            score -= 500
            details.append("Google domain penalty (-500)")
            return score, details
        
        # Immediately reject adult/porn sites with massive penalty
        if any(adult in domain for adult in ADULT_DOMAINS):
            score -= 200
            details.append(f"Adult site penalty ({domain}) (-200)")
            return score, details
        
        # Check for adult content in path (e.g., reddit.com/r/tiktokporn)
        if any(re.search(pat, path, re.IGNORECASE) for pat in ADULT_PATH_PATTERNS):
            score -= 200
            details.append("Adult content path penalty (-200)")
            return score, details
        
        # Penalize PDFs
        if path.endswith('.pdf'):
            score -= 80
            details.append("PDF penalty (-80)")
            
        # Penalize known aggregators/news sites
        if any(bad in domain for bad in BAD_DOMAINS):
            score -= 100
            details.append(f"Aggregator penalty ({domain}) (-100)")
        
        # TLD scoring - heavily favor Swedish companies on .se and .com
        tld = domain.split('.')[-1]
        
        # Heavy boost for preferred TLDs (.se, .com)
        if tld in PREFERRED_TLDS:
            score += 50
            details.append(f"Preferred TLD boost (.{tld}) (+50)")
            # Extra boost for .se since we're searching Swedish companies
            if tld == 'se':
                score += 30
                details.append("Swedish .se TLD extra boost (+30)")
        # Small boost for acceptable TLDs
        elif tld in ACCEPTABLE_TLDS:
            score += 15
            details.append(f"Acceptable TLD boost (.{tld}) (+15)")
        # Heavy penalty for suspicious TLDs
        elif tld in SUSPICIOUS_TLDS:
            score -= 80
            details.append(f"Suspicious TLD penalty (.{tld}) (-80)")
        
        # Boost for "group" in domain or path
        if 'group' in domain or '/group/' in path:
            score += 30
            details.append("Group boost (+30)")
        
        # Boost for specific subdomains
        if any(domain.startswith(sub) for sub in ['ir.', 'investors.', 'group.', 'global.']):
            score += 40
            details.append(f"Subdomain boost ({domain.split('.')[0]}) (+40)")
        
        # Penalize press release/news/article URLs
        if any(kw in path for kw in PRESS_KEYWORDS):
            score -= 80
            details.append("Press/News penalty (-80)")
        
        # Penalize specific event/report keywords
        if any(kw in path for kw in EVENT_KEYWORDS):
            score -= 40
            details.append("Event/Report specific path penalty (-40)")
        
        # Penalize dates in path
        if re.search(r'/\d{4}/', path):
            score -= 50
            details.append("Date in path penalty (-50)")
        
        # Boost for exact domain match or ir. subdomain
        if domain_simple == norm_name_simple:
            score += 70
            details.append("Exact domain match (+70)")
        elif domain_simple.startswith('ir'+norm_name_simple):
            score += 60
            details.append("IR subdomain match (+60)")
        
        # Special case for "Investor"
        if norm_name_simple == 'investor' and 'investorab' in domain:
            score += 80
            details.append("Investor AB specific boost (+80)")
        
        # Boost for any domain segment containing company name
        domain_segments = [re.sub(r'[^a-z0-9]', '', seg) for seg in domain.split('.')]
        if any(norm_name_simple == seg for seg in domain_segments):
            score += 45
            details.append("Domain segment exact match (+45)")
        elif any(norm_name_simple in seg for seg in domain_segments):
            score += 40
            details.append("Domain segment substring match (+40)")
        
        # IR path or ir. subdomain
        if any(re.search(pat, path) for pat in PATH_PATTERNS) or domain.startswith('ir.'):
            score += 40
            details.append("IR path/subdomain boost (+40)")
            # Extra boost for /shareholders
            if '/shareholders' in path:
                score += 30
                details.append("Shareholders path boost (+30)")
            # Massive boost for exact path match
            clean_path = re.sub(r'^/(en|sv|en-gb|en-us)/', '/', path)
            if any(re.fullmatch(pat + r'(\.html|\.aspx|\.php)?/?', clean_path) for pat in PATH_PATTERNS):
                score += 60
                details.append("Exact IR path match (+60)")
        
        # Prefer short URLs
        if len(path) > 80:
            score -= 30
            details.append("Very long path penalty (-30)")
        elif len(path) > 60:
            score -= 20
            details.append("Long path penalty (-20)")
        elif len(path) > 40 or parsed.query:
            score -= 10
            details.append("Medium path/query penalty (-10)")
        
        # Fetch page and validate content - this is the most important check
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            if resp.status_code == 200 and 'text/html' in resp.headers.get('content-type', ''):
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_text = soup.get_text().lower()
                title = soup.title.string.lower() if soup.title and soup.title.string else ''
                desc = ''
                desc_tag = soup.find('meta', attrs={'name': 'description'})
                if desc_tag and desc_tag.get('content'):
                    desc = desc_tag['content'].lower()
                if not desc:
                    og_desc = soup.find('meta', attrs={'property': 'og:description'})
                    if og_desc and og_desc.get('content'):
                        desc = og_desc['content'].lower()
                
                # Company name checks
                if norm_name_simple in re.sub(r'[^a-z0-9]', '', title):
                    score += 20
                    details.append("Company in title (+20)")
                if norm_name_simple in re.sub(r'[^a-z0-9]', '', desc):
                    score += 10
                    details.append("Company in desc (+10)")
                
                if any(kw in title for kw in IR_KEYWORDS):
                    score += 15
                    details.append("IR keyword in title (+15)")
                if any(kw in desc for kw in IR_KEYWORDS):
                    score += 10
                    details.append("IR keyword in desc (+10)")
                
                # CRITICAL: Validate page actually contains IR content
                ir_terms_found = sum(1 for term in IR_PAGE_CONTENT_TERMS if term in page_text)
                
                if ir_terms_found >= 5:
                    score += 60
                    details.append(f"Strong IR content validation (+60, {ir_terms_found} terms)")
                elif ir_terms_found >= 3:
                    score += 30
                    details.append(f"Moderate IR content validation (+30, {ir_terms_found} terms)")
                elif ir_terms_found >= 1:
                    score += 10
                    details.append(f"Weak IR content validation (+10, {ir_terms_found} terms)")
                else:
                    # Page has NO IR-related content - this is likely garbage
                    score -= 80
                    details.append("No IR content found on page (-80)")
            else:
                score -= 20
                details.append(f"HTTP {resp.status_code} or non-HTML penalty (-20)")
        except Exception:
            score -= 10
            details.append("Fetch failed penalty (-10)")
    except Exception:
        pass
    return score, details

def search_ir_url(company_name: str):
    """Search DuckDuckGo for investor relations page URL for a company using ddgs. Returns best match from top 10 results, using scoring."""
    # Remove share class suffixes (B, A, etc.) and also strip "AB" for matching
    norm_name = re.sub(r'\s+(?<![Aa])[ab]$', '', company_name, flags=re.IGNORECASE)
    match_name = re.sub(r'\s+(ab|ltd|corp|inc|group|abp|as|asa|sa|nv|plc)$', '', norm_name, flags=re.IGNORECASE)
    norm_name_simple = normalize_text(match_name)
    
    queries = [
        f"{norm_name} investor relations",
        f"{match_name} investors",
        f"{match_name} investor relations site",
        f"{match_name} financial reports",
        f"{match_name} investerare",
        f"{norm_name} investors official site",
        f'"{match_name}" investor relations',  # Exact match query
        f"{match_name} årsredovisning",  # Swedish annual report
    ]
    if " AB" in norm_name or any(x in norm_name.lower() for x in ["bank", "industri", "fastighet"]):
        queries.append(f"{match_name} investerare")
        
    print(f"Searching for IR URL with queries: {queries}")
    candidates = []
    
    # Primary search: DuckDuckGo
    print("Searching with DuckDuckGo...")
    ddgs = DDGS()
    for q in queries:
        try:
            results = ddgs.text(q, max_results=5)
            for r in results:
                url = r.get('href') or r.get('url')
                if url and url not in candidates:
                    candidates.append(url)
        except Exception as e:
            print(f"DuckDuckGo search error for query '{q}': {e}")
            continue
    
    # Fallback search: Use DuckDuckGo with different region settings if we got few results
    if len(candidates) < 5:
        print("Few results, trying DuckDuckGo with Swedish region...")
        for q in queries[:3]:  # Just first 3 queries
            try:
                results = ddgs.text(q, region='se-sv', max_results=5)
                for r in results:
                    url = r.get('href') or r.get('url')
                    if url and url not in candidates:
                        candidates.append(url)
            except Exception as e:
                print(f"DuckDuckGo SE search error: {e}")
                continue
    
    candidates = candidates[:15]  # Increased from 10
    
    extra_candidates = []
    for url in candidates:
        simplified = simplify_ir_url(url)
        if simplified and simplified not in candidates:
            extra_candidates.append(simplified)
            
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]
            if len(path_parts) <= 1 and not parsed.query:
                domain = parsed.netloc.lower().replace('www.', '')
                if norm_name_simple in domain.replace('.', ''):
                    for pat in ["/investors", "/investor-relations", "/investerare", "/shareholders", "/ir", "/investors-media", "/investor"]:
                        extra_candidates.append(f"{parsed.scheme}://{parsed.netloc}{pat}")
                        extra_candidates.append(f"{parsed.scheme}://{parsed.netloc}{pat}/")
                        extra_candidates.append(f"{parsed.scheme}://{parsed.netloc}/en{pat}")
                        extra_candidates.append(f"{parsed.scheme}://{parsed.netloc}/en{pat}/")
        except:
            continue
    
    for c in extra_candidates:
        if c not in candidates:
            candidates.append(c)
    
    best_url = ''
    best_score = -999
    for url in candidates:
        score, details = get_score(url, company_name)
        print(f"Scored {url}: {score} ({', '.join(details)})")
        if score > best_score:
            best_score = score
            best_url = url
        
        if score >= 100:
            print(f"Found high-confidence match (score {score}), stopping search.")
            break
    
    # Only return the best URL if it meets a minimum quality threshold
    # With content validation, we can be stricter - require positive scores for good matches
    MIN_SCORE_THRESHOLD = 0
    
    if best_url and best_score >= MIN_SCORE_THRESHOLD:
        print(f"Best IR URL: {best_url} (score {best_score})")
        return best_url, best_score
    elif best_url:
        print(f"Best URL {best_url} rejected - score {best_score} below threshold {MIN_SCORE_THRESHOLD}")
    
    # Fallback: check if any candidate validates as IR URL
    for url in candidates:
        # Skip low-scoring URLs in fallback too
        score, _ = get_score(url, company_name)
        if score < MIN_SCORE_THRESHOLD:
            continue
        if validate_ir_url(url):
            print(f"Fallback IR URL: {url} (score {score})")
            return url, score
    
    print(f"No valid IR URL found for {company_name}")
    return '', -999

def validate_ir_url(url: str) -> bool:
    """Return True if URL matches common IR patterns or contains IR keywords."""
    url_lc = url.lower()
    keywords = [r"investor", r"ir", r"investerare", r"shareholder"]
    if any(re.search(kw, url_lc) for kw in keywords):
        return True
    path_patterns = [
        r"/investors/?$",
        r"/investor-relations/?$",
        r"/en-gb/investors/?$",
        r"/investerare/?$",
        r"/shareholders/?$"
    ]
    path = urlparse(url).path.lower()
    if any(re.search(pat, path) for pat in path_patterns):
        return True
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("ir."):
        return True
    return False
