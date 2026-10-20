#!/usr/bin/env python3
"""Site-wide dead-link gate (L21 / P1-fast).

Scans every HTML file under docs/ (the GitHub Pages site root) and verifies
that every internal href/src resolves to a real file, using Pages semantics:
  - docs/ is the site root (docs/.nojekyll present)
  - any ../ that escapes docs/ means the live URL 404s
  - ${...} template literals are dynamic and skipped
Exits 1 if any dead link is found. CI gate for the regression workflow.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse, unquote

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / 'docs'

ATTR_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)


def normalize(url: str) -> str | None:
    url = url.strip()
    if not url:
        return None
    if '${' in url or url.startswith('javascript:'):
        return None  # JS template literal - resolved at runtime
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https', 'mailto', 'javascript', 'data'):
        return None
    path = unquote(parsed.path)
    if not path or path.startswith('#'):
        return None
    return path


def main() -> int:
    html_files = sorted(DOCS.rglob('*.html'))
    real_files = {str(p.relative_to(DOCS)) for p in DOCS.rglob('*') if p.is_file()}

    dead = []
    checked = 0
    for f in html_files:
        rel_dir = f.parent.relative_to(DOCS)
        text = f.read_text(encoding='utf-8', errors='replace')
        for m in ATTR_RE.finditer(text):
            tgt = normalize(m.group(1))
            if tgt is None:
                continue
            checked += 1
            resolved = (rel_dir / tgt).as_posix() if str(rel_dir) != '.' else tgt
            escaped_root = False
            parts = []
            for seg in resolved.split('/'):
                if seg == '..':
                    if parts:
                        parts.pop()
                    else:
                        escaped_root = True
                elif seg in ('.', ''):
                    continue
                else:
                    parts.append(seg)
            if escaped_root:
                dead.append((f.relative_to(REPO), m.group(1), 'ESCAPED_SITE_ROOT'))
                continue
            resolved = '/'.join(parts)
            if resolved not in real_files:
                dead.append((f.relative_to(REPO), m.group(1), resolved))

    print(f'[link-check] html files: {len(html_files)}  internal links: {checked}  dead: {len(dead)}')
    for src, raw, res in dead[:30]:
        print(f'[link-check] DEAD  {src}  ->  {raw}  ({res})')
    if len(dead) > 30:
        print(f'[link-check] ... and {len(dead) - 30} more')
    if dead:
        print('[link-check] FAIL: dead links detected')
        return 1
    print('[link-check] PASS: no dead links')
    return 0


if __name__ == '__main__':
    sys.exit(main())
