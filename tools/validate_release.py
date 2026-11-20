#!/usr/bin/env python3
"""Pre-publication integrity and high-signal secret scanning (heuristic, not a guarantee)."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TEXT_SUFFIX={'.md','.py','.json','.csv','.txt','.yml','.yaml','.toml'}
PATTERNS={
    'Discord webhook':re.compile(r'https?://discord\.com/api/webhooks/\d+/\S+',re.I),
    'Slack webhook':re.compile(r'https?://hooks\.slack\.com/services/[A-Z0-9/]+',re.I),
    'GitHub token':re.compile(r'gh[opsu]_[a-zA-Z0-9]{20,}'),
    'Slack token':re.compile(r'xox[baprs]-[a-zA-Z0-9-]{12,}'),
    'Google API key':re.compile(r'AIza[0-9A-Za-z_-]{30,}'),
    'AWS access key':re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'Bearer credential':re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}',re.I),
    'PEM private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Email address':re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'),
}


def run():
    reg=json.loads((ROOT/'registry/metrics_full_379.json').read_text(encoding='utf-8'))
    sel=json.loads((ROOT/'registry/priority_lite_selection.json').read_text(encoding='utf-8'))
    ideal=json.loads((ROOT/'benchmark/quant-omega/ideal_model_full_379.json').read_text(encoding='utf-8'))
    fullids=[m['id'] for m in reg['metrics']]
    liteids=sel['lite_metric_ids']
    idealids=[m['metric_id'] for m in ideal['full_metrics']]
    assert len(fullids)==len(set(fullids))==379
    assert len(liteids)==len(set(liteids))==76
    assert set(liteids).issubset(set(fullids))
    assert set(fullids)==set(idealids)
    assert set(ideal['lite_metric_ids'])==set(liteids)
    assert len({m['category_id'] for m in reg['metrics']})==29
    assert len({m['category_id'] for m in reg['metrics'] if m['id'] in liteids})==29
    for name,expected in [('full',379),('lite',76)]:
        f=ROOT/'examples'/'ideal-trader'/f'ideal_{name}_{expected}.csv'
        with f.open(encoding='utf-8-sig',newline='') as r:
            rows=list(csv.DictReader(r))
        ids=[row['metric_id'] for row in rows]
        assert len(ids)==expected and len(set(ids))==expected
        assert set(ids)==(set(fullids) if name=='full' else set(liteids))
        t=ROOT/'templates'/f'evaluation_{name}_{expected}x4.csv'
        with t.open(encoding='utf-8-sig',newline='') as r:
            ids2={row['metric_id'] for row in csv.DictReader(r)}
        assert ids2==set(ids)
    found=[]
    ignored_parts={'private','data','raw','outputs','tmp','secrets','.git','__pycache__','.venv','venv','.pytest_cache'}
    paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and not set(p.relative_to(ROOT).parts).intersection(ignored_parts))
    for p in paths:
        if p.suffix.lower() in TEXT_SUFFIX or p.name in ('LICENSE','.gitignore'):
            try: txt=p.read_text(encoding='utf-8-sig')
            except UnicodeDecodeError: continue
            for name,pattern in PATTERNS.items():
                if pattern.search(txt):
                    found.append((str(p.relative_to(ROOT)),name))
        if p.suffix.lower() in ('.xlsx','.docx'):
            # The Office files are user-editable but must not embed macros / remote connections.
            with zipfile.ZipFile(p) as z:
                names=set(z.namelist())
                if any('vbaProject' in n or 'externalLinks/' in n for n in names):
                    found.append((str(p.relative_to(ROOT)),'VBA/external link'))
                if 'docProps/core.xml' in names:
                    core=z.read('docProps/core.xml').decode('utf-8',errors='ignore')
                    for pattern_name,pat in PATTERNS.items():
                        if pat.search(core):found.append((str(p.relative_to(ROOT)),f'Office metadata: {pattern_name}'))
    if found:
        for f,msg in found:print('FAIL',f,msg,file=sys.stderr)
        return 2
    print(f'OK: 379 FULL / 76 LITE / 29 categories; ideal IDs and template IDs match; scanned {len(paths)} distributable public files.')
    print('NOTE: Automated secret checks are heuristic; inspect Git staging and file history manually before making a public repo.')
    return 0


if __name__=='__main__':
    sys.exit(run())
