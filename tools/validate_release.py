#!/usr/bin/env python3
"""Validate metric ontology, release manifest and basic public-safety hygiene.

This is a heuristic public-release check, not a guarantee of privacy or trade efficacy.
The browser-installed .github/workflows/check.yml is deliberately not hash-pinned:
GitHub's default GITHUB_TOKEN cannot update workflow files on push.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
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
BANNED_DIRS={'private','data','raw','outputs','tmp','secrets','.git','__pycache__','.venv','venv','.pytest_cache'}
BANNED_SUFFIXES={'.pyc','.pyo','.zip','.tmp','.bak','.db','.sqlite','.pem','.key','.p12','.pfx'}
# GitHub workflow must exist but is created by a human in GitHub browser; excluded from ZIP overwrite/hash.
BROWSER_MANAGED={'.github/workflows/check.yml'}
MANIFEST_FILES={'MANIFEST.json','MANIFEST.sha256'}
REQUIRED={'.gitignore','.github/workflows/check.yml','README.md','AGENTS.md',
          'tools/evaluate_trades.py','tools/validate_release.py',
          'registry/metrics_full_379.json','registry/priority_lite_selection.json',
          'benchmark/quant-omega/ideal_model_full_379.json',
          'templates/evaluation_lite_76.xlsx','templates/evaluation_full_379.xlsx',
          'docs/GITHUB_BROWSER_UPLOAD.md'}


def included_files(root):
    """Public repo files that should be SHA-pinned by MANIFEST.json."""
    output={}
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        rel=p.relative_to(root).as_posix()
        if any(part in BANNED_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() in BANNED_SUFFIXES or p.name in MANIFEST_FILES:
            continue
        if rel in BROWSER_MANAGED or p.name in ('.DS_Store','Thumbs.db'):
            continue
        if p.name.startswith('~$') or p.name.startswith('.env'):
            continue
        output[rel]=p
    return output


def verify_manifest(root=ROOT):
    """Strictly compare path set and SHA-256 checksums with on-disk release."""
    missing=[p for p in sorted(REQUIRED|MANIFEST_FILES) if not (root/p).is_file()]
    if missing:
        raise ValueError(f'Missing required public files: {missing}')
    manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    expected=manifest.get('file_sha256')
    if not isinstance(expected,dict) or not expected:
        raise ValueError('Manifest lacks file_sha256')
    paths=included_files(root)
    undeclared=sorted(set(paths)-set(expected))
    missing_declared=sorted(set(expected)-set(paths))
    if undeclared or missing_declared:
        raise ValueError(f'Manifest path mismatch; extra={undeclared}; missing={missing_declared}')
    for name, digest in expected.items():
        actual=hashlib.sha256(paths[name].read_bytes()).hexdigest()
        if digest!=actual:
            raise ValueError(f'SHA-256 mismatch: {name}')
    lines=''.join(f'{digest}  {name}\n' for name,digest in expected.items())
    if (root/'MANIFEST.sha256').read_text(encoding='utf-8')!=lines:
        raise ValueError('MANIFEST.sha256 is inconsistent with MANIFEST.json')
    # An imported release archive is removed by Actions before validation;
    # local ZIPs are excluded from the release as before.
    return len(paths)


def test_public_no_tracked_private(root=ROOT):
    """If an actual Git checkout is available, block already tracked private files."""
    if not (root/'.git').exists():
        return
    import subprocess
    r=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True)
    if r.returncode:
        raise ValueError('Unable to inspect tracked files')
    forbidden=[]
    for raw in r.stdout.split(b'\x00'):
        if not raw:
            continue
        name=raw.decode('utf-8','replace')
        if any(part in BANNED_DIRS for part in Path(name).parts) or Path(name).name.startswith('.env'):
            forbidden.append(name)
    if forbidden:
        raise ValueError(f'Private files are already Git-tracked: {forbidden}')


def verify_public_content(root=ROOT):
    found=[]
    paths=included_files(root)
    for rel,p in paths.items():
        if p.suffix.lower() in TEXT_SUFFIX or p.name in ('LICENSE','.gitignore'):
            try:txt=p.read_text(encoding='utf-8-sig')
            except UnicodeDecodeError:continue
            for name,pattern in PATTERNS.items():
                if pattern.search(txt):
                    found.append((rel,name))
        if p.suffix.lower() in ('.xlsx','.docx'):
            with zipfile.ZipFile(p) as z:
                members=set(z.namelist())
                if any('vbaProject' in n or 'externalLinks/' in n for n in members):
                    found.append((rel,'VBA/external link'))
                if 'docProps/core.xml' in members:
                    core=z.read('docProps/core.xml').decode('utf-8',errors='ignore')
                    for name,pat in PATTERNS.items():
                        if pat.search(core):found.append((rel,f'Office metadata: {name}'))
    if found:
        raise ValueError(f'Potential private/sensitive content: {found}')


def verify_ontology(root=ROOT):
    reg=json.loads((root/'registry/metrics_full_379.json').read_text(encoding='utf-8'))
    sel=json.loads((root/'registry/priority_lite_selection.json').read_text(encoding='utf-8'))
    ideal=json.loads((root/'benchmark/quant-omega/ideal_model_full_379.json').read_text(encoding='utf-8'))
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
        f=root/'examples'/'ideal-trader'/f'ideal_{name}_{expected}.csv'
        with f.open(encoding='utf-8-sig',newline='') as r:
            rows=list(csv.DictReader(r))
        ids=[row['metric_id'] for row in rows]
        assert len(ids)==expected and len(set(ids))==expected
        assert set(ids)==(set(fullids) if name=='full' else set(liteids))
        t=root/'templates'/f'evaluation_{name}_{expected}x4.csv'
        with t.open(encoding='utf-8-sig',newline='') as r:
            ids2={row['metric_id'] for row in csv.DictReader(r)}
        assert ids2==set(ids)


def run():
    try:
        n=verify_manifest()
        test_public_no_tracked_private()
        verify_ontology()
        verify_public_content()
    except (AssertionError,ValueError,KeyError,OSError) as e:
        print('FAIL:',str(e),file=sys.stderr)
        return 2
    print(f'OK: 379 FULL / 76 LITE / 29 categories, manifest {n} SHA-256 files, required browser workflow exists.')
    print('NOTE: Secret scanning is heuristic; inspect public Git history and check artifacts manually.')
    return 0


if __name__=='__main__':
    sys.exit(run())
