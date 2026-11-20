#!/usr/bin/env python3
"""Create a GitHub-ready ZIP from public artifacts only; excludes local/private results.

Run validate_release.py and unit tests separately before publishing.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_ROOT='trade-behavior-research'
BLOCK_DIRS={'private','data','raw','outputs','tmp','secrets','.git','__pycache__','.venv','venv','.pytest_cache'}
BLOCK_SUFFIXES={'.pyc','.pyo','.zip','.tmp','.bak','.db','.sqlite','.pem','.key','.p12','.pfx'}
BLOCK_FILES={'.DS_Store','Thumbs.db','MANIFEST.sha256','MANIFEST.json'}


def included_paths():
    items=[]
    for p in ROOT.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(ROOT)
        if any(part in BLOCK_DIRS for part in rel.parts):continue
        if p.suffix.lower() in BLOCK_SUFFIXES or p.name in BLOCK_FILES:continue
        if p.name.startswith('~$') or p.name.startswith('.env'):continue
        items.append(p)
    return sorted(items,key=lambda x:str(x.relative_to(ROOT)))


def main():
    outfile=ROOT.parent/'trade-behavior-research_github-public_v1.0.0.zip'
    paths=included_paths()
    metadata={
        'project':'Trade Behavioral Research for CFD/FX',
        'version':'1.0.0',
        'as_of_utc':'2026-11-20T00:00:00Z',
        'research_status':'RESEARCH_ONLY',
        'contains_real_broker_data':False,
        'contains_real_trader_performance':False,
        'synthetic_examples_only':True,
        'metric_count_full':379,
        'metric_count_lite':76,
        'category_count':29,
        'quant_omega':'hypothetical normative-process benchmark; not actual PnL or returns',
        'file_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
    }
    manifest_json=ROOT/'MANIFEST.json'
    manifest_hash=ROOT/'MANIFEST.sha256'
    manifest_json.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest_hash.write_text(''.join(f"{sha}  {p}\n" for p,sha in metadata['file_sha256'].items()),encoding='utf-8')
    paths.extend((manifest_json,manifest_hash))
    with zipfile.ZipFile(outfile,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(paths,key=lambda x:str(x.relative_to(ROOT))):
            z.write(p,arcname=f'{PUBLIC_ROOT}/{p.relative_to(ROOT).as_posix()}')
    with zipfile.ZipFile(outfile) as z:
        bad=z.testzip()
        if bad:raise RuntimeError(f'ZIP integrity error: {bad}')
        names=z.namelist()
        if not all(name.startswith(f'{PUBLIC_ROOT}/') for name in names):
            raise RuntimeError('Archive contains files outside the repo root')
        if any('/outputs/' in name or '/private/' in name or '/.git/' in name for name in names):
            raise RuntimeError('Private output included in archive')
        repo_json=json.loads(z.read(f'{PUBLIC_ROOT}/MANIFEST.json'))
        for rel,sha in repo_json['file_sha256'].items():
            val=hashlib.sha256(z.read(f'{PUBLIC_ROOT}/{rel}')).hexdigest()
            if val!=sha:raise RuntimeError(f'Hash mismatch: {rel}')
    print(f'OK release: {outfile} | files={len(paths)} | bytes={outfile.stat().st_size}')
    print('Verify public Git staging and commit history manually before push; this ZIP contains no .git metadata.')

if __name__=='__main__':
    sys.exit(main())
