"""v1.1.0 regression tests for public release, comparison and cautious inference."""
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import evaluate_trades as ev
from tools.validate_release import verify_manifest

class V110RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample=ROOT/'examples/synthetic_round_trips.csv'
        cls.trades,_=ev.read_trades(cls.sample,None,'Asia/Tokyo',None)
        cls.registry=json.loads(ev.REGISTRY_PATH.read_text(encoding='utf-8'))
        cls.selection=json.loads(ev.SELECTION_PATH.read_text(encoding='utf-8'))
        cls.ideal=json.loads(ev.IDEAL_PATH.read_text(encoding='utf-8'))

    def test_excel_machine_status_maps_to_template_vocabulary(self):
        self.assertEqual(ev.excel_review_status('MEASURED'),'評価済')
        self.assertEqual(ev.excel_review_status('DESCRIPTIVE'),'評価済')
        self.assertEqual(ev.excel_review_status('PARTIAL'),'レビュー待ち')
        self.assertEqual(ev.excel_review_status('HYPOTHESIS_ONLY'),'仮説段階')
        self.assertEqual(ev.excel_review_status('NOT_ESTIMABLE'),'要追加データ')
        self.assertEqual(ev.excel_review_status('NOT_IDENTIFIABLE_FROM_TRADES'),'識別不可')

    def test_lite_xlsx_mapped_status_and_raw_status_trace(self):
        rows=ev.output_rows('A',self.trades,self.registry,self.ideal,set(self.selection['lite_metric_ids']),'lite',{},['s.csv'])
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'out.xlsx'
            ev.write_xlsx('lite',rows,path,'A',self.trades)
            from openpyxl import load_workbook
            w=load_workbook(path)
            s=w['A_評価'];loc=next(r for r in range(7,s.max_row+1) if s.cell(r,4).value=='D02-003')
            self.assertEqual(s.cell(loc,14).value,'評価済')
            self.assertIn('MEASURED',s.cell(loc,15).value)
            self.assertEqual(s.cell(loc,11).value,36/64)

    def test_multi_dataset_exports_one_A_B_comparison_book(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'output'
            cp=subprocess.run([sys.executable,str(ROOT/'tools/evaluate_trades.py'),
               '--dataset',f'A:{self.sample}','--dataset',f'B:{self.sample}',
               '--mode','lite','--out',str(out)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertTrue((out/'comparison_lite.xlsx').exists())
            from openpyxl import load_workbook
            w=load_workbook(out/'comparison_lite.xlsx')
            for sh in ['A_評価','B_評価']:
                s=w[sh];loc=next(r for r in range(7,s.max_row+1) if s.cell(r,4).value=='D02-003')
                self.assertEqual(s.cell(loc,14).value,'評価済')
            self.assertEqual(w['比較一覧']['Q10'].value,'未確認')
            with (out/'A'/'evaluation_lite.csv').open(encoding='utf-8-sig',newline='') as f:
                r=next(csv.DictReader(f))
                self.assertEqual(r['source_sha256'],f'{self.sample.name}:{hashlib.sha256(self.sample.read_bytes()).hexdigest()}')
                self.assertTrue(r['data_asof_utc'].endswith('+00:00'))

    def test_small_loss_count_does_not_trigger_tail_warning(self):
        # The bottom five naturally include both losing trades: 100% is trivial.
        trades=[replace(t,net_pnl=abs(t.net_pnl)+1) for t in self.trades[:12]]
        for i in [1,4]:trades[i]=replace(trades[i],net_pnl=-100)
        rows=ev.output_rows('A',trades,self.registry,self.ideal,set(self.selection['lite_metric_ids']),'lite',{},['synthetic.csv'])
        ideas=ev.make_suggestions(trades,rows)
        self.assertNotIn('損失の少数取引集中',[item['topic'] for item in ideas])

    def test_missing_dotfiles_and_tampered_manifest_are_detected(self):
        self.assertGreater(verify_manifest(ROOT),35)
        with tempfile.TemporaryDirectory() as td:
            dst=Path(td)/'repo'
            shutil.copytree(ROOT,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            (dst/'.gitignore').unlink()
            with self.assertRaisesRegex(ValueError,'Missing required'):verify_manifest(dst)
            shutil.copy2(ROOT/'.gitignore',dst/'.gitignore')
            (dst/'README.md').write_text('tampered',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):verify_manifest(dst)

if __name__=='__main__':unittest.main()
