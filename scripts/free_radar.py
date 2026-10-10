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
    if source == 'Hacker News' and not any(term in title.lower() for term in PRIORITY_TERMS):
        return
    if source.startswith('X ·'):
        import re
        match = re.search(r'/status/(\d+)', link)
        handle = {'X · Sam Altman': 'sama', 'X · OpenAI': 'OpenAI', 'X · Anthropic': 'AnthropicAI', 'X · Andrej Karpathy': 'karpathy', 'X · Vitalik Buterin': 'VitalikButerin', 'X · CZ': 'cz_binance'}.get(source)
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
    ('X · Sam Altman', 'https://fxtwitter.com/sama/feed.xml'),
    ('X · OpenAI', 'https://fxtwitter.com/OpenAI/feed.xml'),
    ('X · Anthropic', 'https://fxtwitter.com/AnthropicAI/feed.xml'),
    ('X · Andrej Karpathy', 'https://fxtwitter.com/karpathy/feed.xml'),
    ('X · Vitalik Buterin', 'https://fxtwitter.com/VitalikButerin/feed.xml'),
    ('X · CZ', 'https://fxtwitter.com/cz_binance/feed.xml'),
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
lines = [f'# 一手信息雷达｜{today}', '', f'采集时间：{now:%Y-%m-%d %H:%M}（北京时间）', '', '仅收录近 72 小时可解析时间的候选线索；无法解析发布时间的条目仍保留并标记待核实。排序按来源发布时间，不等于全网首发。', '', f'候选总数：{len(entries)}', '', '## 来源状态', '']
for source, url in feeds:
    lines.append(f'- {source}：{source_stats.get(source, 0)} 条（0 条不代表没有新闻，也可能是源失效）')
lines += ['', '## 暂未自动接入的平台', '', '- [币安广场](https://www.binance.com/en/square)：尚无已验证的稳定公开抓取接口，需人工核验原帖。', '- [OKX 欧易星球](https://www.okx.com/)：尚无已验证的稳定公开抓取接口，需人工核验原帖。', '- X：当前为第三方公开 RSS 尝试，能否采集以实际结果为准；不要把 0 条当作没有新帖。', '', '## 最新候选线索', '']
for source, title, link, published, age_hours in entries:
    title = title.replace('[', '［').replace(']', '］')
    freshness = f'{age_hours:.1f} 小时前' if age_hours is not None else '时间待核验'
    lines.append(f'- [{title}]({link})｜{source}｜{freshness}｜来源时间：{published or "未知"}')
lines += ['', '## 采集异常', '']
lines += [f'- {e}' for e in errors] if errors else ['无']
out = pathlib.Path('radar') / f'{today}.md'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Created {out}, {len(entries)} candidates')
if not entries:
    raise SystemExit('All sources returned zero items')
