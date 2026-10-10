#!/usr/bin/env python3
"""No-key daily original-source radar."""
import datetime as dt
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
today = now.strftime('%Y-%m-%d')
entries, errors, seen = [], [], set()
MAX_AGE_HOURS = 72
source_stats = {}

# Focus on original sources, not generic AI SEO blogs.
BLOCKED_HOSTS = {'phpscientist.com'}
PRIORITY_TERMS = ('openai', 'anthropic', 'claude', 'gpt', 'gemini', 'deepseek', 'qwen', 'agent', 'model', 'llm', 'arxiv', 'research', 'release', 'github', 'transformer', 'benchmark')

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'FirsthandRadar/1.0', 'Accept': 'application/json, application/xml, text/xml, */*'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read()

def add(source, title, link, published=''):
    if not title or not link or not link.startswith('https://') or link in seen:
        return
    host = (urlparse(link).hostname or '').lower()
    if host in BLOCKED_HOSTS:
        return
    if source.startswith('Hacker News') and not any(term in title.lower() for term in PRIORITY_TERMS):
        return
    if source.startswith('X ·'):
        import re
        match = re.search(r'/status/(\d+)', link)
        handle = {"X · Sam Altman":"sama","X · OpenAI":"OpenAI","X · Anthropic":"AnthropicAI","X · Andrej Karpathy":"karpathy","X · Vitalik Buterin":"VitalikButerin","X · CZ":"cz_binance","X · Elon Musk":"elonmusk","X · Google DeepMind":"GoogleDeepMind","X · Google AI":"GoogleAI","X · Demis Hassabis":"demishassabis","X · Sundar Pichai":"sundarpichai","X · Jeff Dean":"JeffDean","X · Yann LeCun":"ylecun","X · Andrew Ng":"AndrewYNg","X · Hugging Face":"huggingface","X · Clement Delangue":"ClementDelangue","X · Mistral AI":"MistralAI","X · Meta AI":"AIatMeta","X · GitHub":"github","X · GitHub Copilot":"GitHubCopilot","X · LangChain":"LangChainAI","X · Cursor":"cursor_ai","X · Perplexity":"perplexity_ai","X · Satya Nadella":"satyanadella","X · Microsoft Research":"MSFTResearch","X · Cloudflare":"Cloudflare","X · Vercel":"vercel","X · Solana":"solana","X · Anatoly Yakovenko":"aeyakovenko","X · Ethereum Foundation":"ethereumfndn","X · Coinbase":"coinbase","X · Brian Armstrong":"brian_armstrong","X · Binance":"binance","X · OKX":"okx","X · Star Xu":"star_okx","X · Jesse Pollak":"jessepollak","X · DefiLlama":"DefiLlama","X · a16z crypto":"a16zcrypto","X · Paradigm":"paradigm","X · Balaji Srinivasan":"balajis","X · Arthur Hayes":"CryptoHayes","X · Justin Sun":"justinsuntron"}.get(source)
        if match and handle:
            link = f'https://x.com/{handle}/status/{match.group(1)}'
    # Reject stale content, rather than resurfacing old announcements as breaking news.
    age_hours = None
    if published:
        try:
            stamp = dt.datetime.fromisoformat(published.replace('Z', '+00:00')) if 'T' in published else parsedate_to_datetime(published)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=dt.timezone.utc)
            age_hours = (now - stamp.astimezone(now.tzinfo)).total_seconds() / 3600
            if age_hours > MAX_AGE_HOURS or age_hours < -2:
                return
        except (ValueError, TypeError, OverflowError):
            pass
    seen.add(link)
    entries.append((source, title.strip(), link, published, age_hours))
    source_stats[source] = source_stats.get(source, 0) + 1

feeds = [
    ('Hacker News', 'https://hnrss.org/newest?q=AI'),
    ('arXiv AI', 'https://export.arxiv.org/rss/cs.AI'),
    ('arXiv ML', 'https://export.arxiv.org/rss/cs.LG'),
    ('OpenAI 官方', 'https://openai.com/news/rss.xml'),
    ('Google Research', 'https://research.google/blog/rss/'),
    ('Hugging Face 博客', 'https://huggingface.co/blog/feed.xml'),
    ('Ethereum Research', 'https://ethresear.ch/latest.rss'),
    ('Product Hunt', 'https://www.producthunt.com/feed'),
    ('Hacker News 最新', 'https://hnrss.org/newest'),
    ('X · Sam Altman', 'https://fxtwitter.com/sama/feed.xml'),
    ('X · OpenAI', 'https://fxtwitter.com/OpenAI/feed.xml'),
    ('X · Anthropic', 'https://fxtwitter.com/AnthropicAI/feed.xml'),
    ('X · Andrej Karpathy', 'https://fxtwitter.com/karpathy/feed.xml'),
    ('X · Vitalik Buterin', 'https://fxtwitter.com/VitalikButerin/feed.xml'),
    ('X · CZ', 'https://fxtwitter.com/cz_binance/feed.xml'),
    ('X · Elon Musk', 'https://fxtwitter.com/elonmusk/feed.xml'),
    ('X · Google DeepMind', 'https://fxtwitter.com/GoogleDeepMind/feed.xml'),
    ('X · Google AI', 'https://fxtwitter.com/GoogleAI/feed.xml'),
    ('X · Demis Hassabis', 'https://fxtwitter.com/demishassabis/feed.xml'),
    ('X · Sundar Pichai', 'https://fxtwitter.com/sundarpichai/feed.xml'),
    ('X · Jeff Dean', 'https://fxtwitter.com/JeffDean/feed.xml'),
    ('X · Yann LeCun', 'https://fxtwitter.com/ylecun/feed.xml'),
    ('X · Andrew Ng', 'https://fxtwitter.com/AndrewYNg/feed.xml'),
    ('X · Hugging Face', 'https://fxtwitter.com/huggingface/feed.xml'),
    ('X · Clement Delangue', 'https://fxtwitter.com/ClementDelangue/feed.xml'),
    ('X · Mistral AI', 'https://fxtwitter.com/MistralAI/feed.xml'),
    ('X · Meta AI', 'https://fxtwitter.com/AIatMeta/feed.xml'),
    ('X · GitHub', 'https://fxtwitter.com/github/feed.xml'),
    ('X · GitHub Copilot', 'https://fxtwitter.com/GitHubCopilot/feed.xml'),
    ('X · LangChain', 'https://fxtwitter.com/LangChainAI/feed.xml'),
    ('X · Cursor', 'https://fxtwitter.com/cursor_ai/feed.xml'),
    ('X · Perplexity', 'https://fxtwitter.com/perplexity_ai/feed.xml'),
    ('X · Satya Nadella', 'https://fxtwitter.com/satyanadella/feed.xml'),
    ('X · Microsoft Research', 'https://fxtwitter.com/MSFTResearch/feed.xml'),
    ('X · Cloudflare', 'https://fxtwitter.com/Cloudflare/feed.xml'),
    ('X · Vercel', 'https://fxtwitter.com/vercel/feed.xml'),
    ('X · Solana', 'https://fxtwitter.com/solana/feed.xml'),
    ('X · Anatoly Yakovenko', 'https://fxtwitter.com/aeyakovenko/feed.xml'),
    ('X · Ethereum Foundation', 'https://fxtwitter.com/ethereumfndn/feed.xml'),
    ('X · Coinbase', 'https://fxtwitter.com/coinbase/feed.xml'),
    ('X · Brian Armstrong', 'https://fxtwitter.com/brian_armstrong/feed.xml'),
    ('X · Binance', 'https://fxtwitter.com/binance/feed.xml'),
    ('X · OKX', 'https://fxtwitter.com/okx/feed.xml'),
    ('X · Star Xu', 'https://fxtwitter.com/star_okx/feed.xml'),
    ('X · Jesse Pollak', 'https://fxtwitter.com/jessepollak/feed.xml'),
    ('X · DefiLlama', 'https://fxtwitter.com/DefiLlama/feed.xml'),
    ('X · a16z crypto', 'https://fxtwitter.com/a16zcrypto/feed.xml'),
    ('X · Paradigm', 'https://fxtwitter.com/paradigm/feed.xml'),
    ('X · Balaji Srinivasan', 'https://fxtwitter.com/balajis/feed.xml'),
    ('X · Arthur Hayes', 'https://fxtwitter.com/CryptoHayes/feed.xml'),
    ('X · Justin Sun', 'https://fxtwitter.com/justinsuntron/feed.xml'),
]
for name, url in feeds:
    try:
        root = ET.fromstring(fetch(url))
        items = root.findall('.//item')
        if not items:
            items = root.findall('.//{http://www.w3.org/2005/Atom}entry')
        for item in items[:20]:
            title = item.findtext('title', '') or item.findtext('{http://www.w3.org/2005/Atom}title', '')
            link = item.findtext('link', '')
            if not link:
                element = item.find('{http://www.w3.org/2005/Atom}link')
                link = element.get('href', '') if element is not None else ''
            published = item.findtext('pubDate', '') or item.findtext('{http://www.w3.org/2005/Atom}published', '')
            add(name, title, link, published)
    except Exception as exc:
        errors.append(f'{name}: {type(exc).__name__}: {exc}')

# Additional public discovery endpoints; each is independently error-isolated.
try:
    data = json.loads(fetch('https://huggingface.co/api/daily_papers?limit=30'))
    for paper in data:
        p = paper.get('paper', {})
        pid = p.get('id') or paper.get('id', '')
        title = p.get('title') or paper.get('title', '')
        published = paper.get('publishedAt') or p.get('publishedAt', '')
        if pid:
            add('Hugging Face Papers', title, 'https://huggingface.co/papers/' + pid, published)
except Exception as exc:
    errors.append(f'Hugging Face Papers: {type(exc).__name__}: {exc}')

try:
    data = json.loads(fetch('https://huggingface.co/api/models?sort=createdAt&direction=-1&limit=40'))
    for model in data:
        mid = model.get('id', '')
        if mid:
            add('Hugging Face 新模型', mid, 'https://huggingface.co/' + mid, model.get('createdAt', ''))
except Exception as exc:
    errors.append(f'Hugging Face 新模型: {type(exc).__name__}: {exc}')

try:
    import re
    html = fetch('https://github.com/trending?since=daily').decode('utf-8', errors='replace')
    paths = re.findall(r'<h2[^>]*class="[^"]*h3[^"]*"[^>]*>\\s*<a[^>]*href="/([^"/]+/[^"/?#]+)"', html, re.I)
    for path in dict.fromkeys(paths):
        add('GitHub Trending', path.replace('/', ' / ', 1), 'https://github.com/' + path, '')
except Exception as exc:
    errors.append(f'GitHub Trending: {type(exc).__name__}: {exc}')

try:
    data = json.loads(fetch('https://api.coingecko.com/api/v3/search/trending'))
    for coin in data.get('coins', [])[:15]:
        item = coin.get('item', {})
        cid = item.get('id', '')
        if cid:
            add('CoinGecko 热门', item.get('name', cid), 'https://www.coingecko.com/en/coins/' + cid, '')
except Exception as exc:
    errors.append(f'CoinGecko 热门: {type(exc).__name__}: {exc}')

try:
    data = json.loads(fetch('https://api.llama.fi/protocols'))
    protocols = sorted((p for p in data if isinstance(p.get('change_1d'), (float, int)) and (p.get('tvl') or 0) > 10000000), key=lambda p: p['change_1d'], reverse=True)
    for protocol in protocols[:12]:
        slug = protocol.get('slug', '')
        if slug:
            add('DefiLlama 资金异动', f"{protocol.get('name', slug)} TVL 24h {protocol['change_1d']:+.1f}%", 'https://defillama.com/protocol/' + slug, '')
except Exception as exc:
    errors.append(f'DefiLlama 资金异动: {type(exc).__name__}: {exc}')

# SEC EDGAR official RSS search feed: public filings are not necessarily AI news.
try:
    url = 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&owner=include&count=20&output=atom'
    root = ET.fromstring(fetch(url))
    ns = '{http://www.w3.org/2005/Atom}'
    for item in root.findall('.//' + ns + 'entry')[:20]:
        title = item.findtext(ns + 'title', '')
        link_el = item.find(ns + 'link')
        link = link_el.get('href', '') if link_el is not None else ''
        published = item.findtext(ns + 'updated', '')
        add('SEC EDGAR 8-K', title, link, published)
except Exception as exc:
    errors.append(f'SEC EDGAR 8-K: {type(exc).__name__}: {exc}')

# Public GitHub repository search: recent activity from original builders.
try:
    since = (now - dt.timedelta(days=3)).strftime('%Y-%m-%d')
    url = 'https://api.github.com/search/repositories?q=' + quote('topic:ai-agent pushed:>' + since) + '&sort=updated&order=desc&per_page=12'
    result = json.loads(fetch(url))
    for project in result.get('items', []):
        add('GitHub 开发者动态', project.get('full_name', ''), project.get('html_url', ''), project.get('pushed_at', ''))
except Exception as exc:
    errors.append(f'GitHub 开发者动态: {type(exc).__name__}: {exc}')

for project in ['openai/openai-python', 'anthropics/anthropic-sdk-python', 'huggingface/transformers']:
    try:
        releases = json.loads(fetch(f'https://api.github.com/repos/{project}/releases?per_page=5'))
        for release in releases:
            add('GitHub Release', f"{project}: {release.get('name') or release.get('tag_name')}", release.get('html_url', ''), release.get('published_at', ''))
    except Exception as exc:
        errors.append(f'{project}: {type(exc).__name__}: {exc}')

entries.sort(key=lambda row: (row[4] is None, row[4] if row[4] is not None else 9999))

# Transparent, rule-based editorial triage; NOT an AI fact-check.
OFFICIAL = ('X · OpenAI', 'X · Anthropic', 'X · Google DeepMind', 'X · Google AI', 'X · Mistral AI', 'X · Meta AI', 'X · Binance', 'X · OKX', 'OpenAI 官方', 'Google Research', 'Hugging Face 博客')
FOUNDERS = ('X · Sam Altman', 'X · Elon Musk', 'X · Demis Hassabis', 'X · Sundar Pichai', 'X · Vitalik Buterin', 'X · CZ', 'X · Star Xu', 'X · Brian Armstrong', 'X · Anatoly Yakovenko')
PROMO = ('giveaway', 'airdrop', 'referral', 'promo code', 'limited offer', 'discount', 'sponsored', 'win $', 'free money', '抽奖', '返佣', '空投领取')
LAUNCH = ('launch', 'introduc', 'announc', 'releas', 'open sourc', 'ship', 'unveil', 'new model', 'new api', '上线', '发布', '开源', '推出', '升级')
RESEARCH = ('paper', 'research', 'benchmark', 'arxiv', 'study', 'technical report', '论文', '研究', '基准测试')
MARKET = ('listing', 'delist', 'token', 'mainnet', 'upgrade', 'security', 'exploit', 'hack', 'etf', '上币', '下架', '主网', '漏洞')
REPOST = ('rt @', 'repost', 'retweeted', '转发', 'via @')

def triage(row):
    source, title, link, published, age = row
    low = title.lower()
    if any(word in low for word in PROMO):
        return ('广告/营销候选', 0, '含营销关键词，需人工复核')
    if any(low.startswith(word) for word in REPOST):
        return ('转发/二手线索', 1, '可能不是首发，需追溯原帖')
    original = source.startswith('X ·') or source in OFFICIAL or source in ('GitHub Release', 'arXiv AI', 'arXiv ML')
    if source in OFFICIAL and any(word in low for word in LAUNCH):
        return ('重点：官方发布', 5, '官方渠道 + 发布关键词；尚未核实内容')
    if source in FOUNDERS:
        return ('重点：创始人原话', 4, '创始人账号候选，需核验是否原创及上下文')
    if source in ('arXiv AI', 'arXiv ML') or any(word in low for word in RESEARCH):
        return ('研究/论文', 3, '研究线索，需检查论文原文')
    if any(word in low for word in MARKET):
        return ('Web3/市场动态', 3, '市场关键词，非交易建议')
    if original:
        return ('原始渠道动态', 3, '官方或开发者来源，未核验首发')
    if source in ('Product Hunt', 'Hugging Face 新模型', 'GitHub Trending', 'Hugging Face Papers'):
        return ('产品/开源新发现', 3, '新项目或论文线索，需核对发布时间和实用性')
    if source in ('CoinGecko 热门', 'DefiLlama 资金异动'):
        return ('Web3/市场动态', 2, '市场指标快照，不等于消息或投资建议')
    if source == 'SEC EDGAR 8-K':
        return ('官方监管披露', 2, '监管文件需确认公司及事项是否相关')
    if source == 'GitHub 开发者动态':
        return ('开发者活动', 2, '代码活跃不等于重大产品发布')
    return ('普通线索', 1, '需要寻找原始出处')

def render(row):
    source, title, link, published, age_hours = row
    category, score, reason = triage(row)
    safe_title = title.replace('[', '［').replace(']', '］').replace('\\n', ' ')
    freshness = f'{age_hours:.1f} 小时前' if age_hours is not None else '时间待核验'
    return f'- [{safe_title}]({link})｜{source}｜{freshness}｜{reason}｜来源时间：{published or "未知"}'

lines = [f'# 一手信息雷达｜{today}', '', f'采集时间：{now:%Y-%m-%d %H:%M}（北京时间）', '', '规则分级不是事实核查；分类基于账号和关键词，转发与广告可能漏判。只看近 72 小时可解析时间的候选，时间不明者待核验。', '', f'候选总数：{len(entries)}', '', '## 优先查看：最多 15 条', '']
ranked = sorted(entries, key=lambda r: (-triage(r)[1], r[4] is None, r[4] if r[4] is not None else 9999))
for row in ranked[:15]:
    lines.append(render(row))
lines += ['', '## 按新闻性质分类', '']
for category in ('重点：官方发布', '重点：创始人原话', '研究/论文', 'Web3/市场动态', '原始渠道动态', '产品/开源新发现', '官方监管披露', '开发者活动', '普通线索', '转发/二手线索', '广告/营销候选'):
    subset = [row for row in ranked if triage(row)[0] == category]
    lines += [f'### {category}（{len(subset)}）', '']
    lines += [render(row) for row in subset] if subset else ['暂无']
    lines.append('')
lines += ['## 来源健康状态', '']
for source, url in feeds:
    lines.append(f'- {source}：{source_stats.get(source, 0)} 条（0 条可能是没更新，也可能是采集失效）')
lines += ['', '## 未完成的来源', '', '- [币安广场](https://www.binance.com/en/square)：未验证公开采集接口，尚未自动接入。', '- [OKX 欧易星球](https://www.okx.com/)：未验证公开采集接口，尚未自动接入。', '- X 依赖第三方 FxTwitter RSS，来源返回 0 条不代表账号没有发帖。', '']
lines += ['', '## 采集异常', '']
lines += [f'- {e}' for e in errors] if errors else ['无']
out = pathlib.Path('radar') / f'{today}.md'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Created {out}, {len(entries)} candidates')
if not entries:
    raise SystemExit('All sources returned zero items')
