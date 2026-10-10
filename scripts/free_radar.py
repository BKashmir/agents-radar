#!/usr/bin/env python3
"""No-key daily original-source radar."""
import datetime as dt
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import quote

now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
today = now.strftime('%Y-%m-%d')
entries, errors, seen = [], [], set()

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
    from urllib.parse import urlparse
    host = (urlparse(link).hostname or '').lower()
    if host in BLOCKED_HOSTS:
        return
    if source == 'Hacker News' and not any(term in title.lower() for term in PRIORITY_TERMS):
        return
    seen.add(link)
    entries.append((source, title.strip(), link, published))

feeds = [
    ('Hacker News', 'https://hnrss.org/newest?q=AI'),
    ('arXiv AI', 'https://export.arxiv.org/rss/cs.AI'),
    ('arXiv ML', 'https://export.arxiv.org/rss/cs.LG'),
    ('OpenAI 官方', 'https://openai.com/news/rss.xml'),
    ('Google Research', 'https://research.google/blog/rss/'),
    ('Hugging Face 博客', 'https://huggingface.co/blog/feed.xml'),
    ('Ethereum Research', 'https://ethresear.ch/latest.rss'),
    ('Binance 官方公告', 'https://www.binance.com/en/support/announcement/rss'),
]
for name, url in feeds:
    try:
        root = ET.fromstring(fetch(url))
        for item in root.findall('.//item')[:20]:
            add(name, item.findtext('title', ''), item.findtext('link', ''), item.findtext('pubDate', ''))
    except Exception as exc:
        errors.append(f'{name}: {type(exc).__name__}: {exc}')

# Public GitHub repository search: recent activity from original builders.
try:
    url = 'https://api.github.com/search/repositories?q=' + quote('topic:ai-agent pushed:>2026-10-01') + '&sort=updated&order=desc&per_page=12'
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

lines = [f'# 一手信息雷达｜{today}', '', f'采集时间：{now:%Y-%m-%d %H:%M}（北京时间）', '', '自动采集的候选线索，尚未核实真实性、最早发布时间和重要性。', '', f'候选总数：{len(entries)}', '']
for source, title, link, published in entries:
    title = title.replace('[', '［').replace(']', '］')
    lines.append(f'- [{title}]({link})｜{source}｜来源时间：{published or "未知"}')
lines += ['', '## 采集异常', '']
lines += [f'- {e}' for e in errors] if errors else ['无']
out = pathlib.Path('radar') / f'{today}.md'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'Created {out}, {len(entries)} candidates')
if not entries:
    raise SystemExit('All sources returned zero items')
