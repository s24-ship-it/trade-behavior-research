#!/usr/bin/env python3
"""Produce public GitHub browser-import release_bundle.zip (no private data)."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.validate_release import included_files, verify_ontology, verify_public_content

ARCHIVE_PREFIX='trade-behavior-research'
VERSION='1.1.0'


def package(outfile=None):
    verify_ontology(ROOT)
    verify_public_content(ROOT)
    files=included_files(ROOT)
    metadata={
        'project':'Trade Behavioral Research for CFD/FX',
        'version':VERSION,
        'as_of_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'research_status':'RESEARCH_ONLY',
        'contains_real_broker_data':False,
        'contains_real_trader_performance':False,
        'synthetic_examples_only':True,
        'metric_count_full':379,
        'metric_count_lite':76,
        'category_count':29,
        'browser_workflow_not_hash_pinned':'.github/workflows/check.yml',
        'quant_omega':'hypothetical normative-process benchmark; not actual PnL or returns',
        'file_sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(files.items())},
    }
    (ROOT/'MANIFEST.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'MANIFEST.sha256').write_text(''.join(f'{sha}  {name}\n' for name,sha in metadata['file_sha256'].items()),encoding='utf-8')
    from tools.validate_release import verify_manifest
    assert verify_manifest(ROOT)
    target=Path(outfile) if outfile else ROOT.parent/'release_bundle.zip'
    files={**files,**{name:ROOT/name for name in ('MANIFEST.json','MANIFEST.sha256')}}
    files['.github/workflows/check.yml']=ROOT/'.github/workflows/check.yml'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for name,path in sorted(files.items()):
            z.write(path,arcname=f'{ARCHIVE_PREFIX}/{name}')
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
    print(f'RELEASE OK: {target}, files={len(files)}, bytes={target.stat().st_size}')
    return target


if __name__=='__main__':
    package(sys.argv[1] if len(sys.argv)>1 else None)
