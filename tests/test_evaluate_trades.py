import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import evaluate_trades as ev


class TradeResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample=ROOT/'examples'/'synthetic_round_trips.csv'
        cls.trades,_=ev.read_trades(cls.sample,None,'Asia/Tokyo',None)
        cls.registry=json.loads(ev.REGISTRY_PATH.read_text(encoding='utf-8'))
        cls.sel=json.loads(ev.SELECTION_PATH.read_text(encoding='utf-8'))
        cls.ideal=json.loads(ev.IDEAL_PATH.read_text(encoding='utf-8'))

    def test_complete_registry_and_lite_subset(self):
        full={m['id'] for m in self.registry['metrics']}
        lite=set(self.sel['lite_metric_ids'])
        self.assertEqual(len(full),379)
        self.assertEqual(len(lite),76)
        self.assertEqual(len(self.registry['categories']),29)
        self.assertTrue(lite.issubset(full))
        self.assertEqual(set(m['metric_id'] for m in self.ideal['full_metrics']),full)
        self.assertEqual(set(self.ideal['lite_metric_ids']),lite)
        self.assertEqual(len(set(m['category_id'] for m in self.registry['metrics'] if m['id'] in lite)),29)

    def test_lite_rows_and_partial_evidence(self):
        rows=ev.output_rows('A',self.trades,self.registry,self.ideal,set(self.sel['lite_metric_ids']),'lite',{},[self.sample.name])
        self.assertEqual(len(rows),76)
        self.assertEqual(len(set(r['category_id'] for r in rows)),29)
        by={r['metric_id']:r for r in rows}
        self.assertEqual(by['D02-003']['effective_n'],64)
        self.assertEqual(by['D09-003']['numeric_value'],None)  # MFE needs a price path
        self.assertEqual(by['P06-003']['assessment_status'],'NOT_IDENTIFIABLE_FROM_TRADES')
        self.assertEqual(by['P07-004']['score_1_5'],None)
        self.assertEqual(by['D02-007']['score_1_5'],None)
        self.assertEqual(by['D02-007']['process_gap'],None)

    def test_full_exact_count(self):
        rows=ev.output_rows('A',self.trades,self.registry,self.ideal,set(self.sel['lite_metric_ids']),'full',{},[self.sample.name])
        self.assertEqual(len(rows),379)
        self.assertEqual(len({r['metric_id'] for r in rows}),379)
        self.assertEqual(len({r['category_id'] for r in rows}),29)

    def test_pnl_and_profit_factor_reproducible(self):
        v=ev.measurements(self.trades)
        self.assertEqual(v['D02-001']['value'],sum(t.net_pnl for t in self.trades))
        self.assertAlmostEqual(v['D02-003']['value'],sum(t.net_pnl>0 for t in self.trades)/len(self.trades))
        self.assertAlmostEqual(v['D02-006']['value'],ev.pf([t.net_pnl for t in self.trades]))

    def test_no_losses_not_fake_infinite_pf(self):
        positives=[self.trades[1],self.trades[3],self.trades[4]]
        self.assertTrue(all(t.net_pnl>0 for t in positives))
        v=ev.measurements(positives)
        self.assertIsNone(v['D02-006']['value'])
        self.assertEqual(v['D02-006']['status'],'NOT_ESTIMABLE')

    def test_gap_requires_process_evidence_and_not_profitable_score(self):
        rating={('A','D01-009'):{'score_1_5':3,'evidence_reference':'review-123','evidence_level':'L1'},
                ('A','P06-003'):{'score_1_5':5,'evidence_reference':'bad-inference','evidence_level':'L4'}}
        rows=ev.output_rows('A',self.trades,self.registry,self.ideal,set(self.sel['lite_metric_ids']),'lite',rating,['synthetic.csv'])
        by={r['metric_id']:r for r in rows}
        self.assertEqual(by['D01-009']['process_gap'],2)
        self.assertEqual(by['P06-003']['score_1_5'],None)
        self.assertEqual(by['P06-003']['gap_status'],'NOT_SCOREABLE')
        self.assertIsNone(by['D02-007']['process_gap'])
        d=ev.make_gap_rows(rows)
        self.assertEqual(len(d),76)
        self.assertIn('理想運用プロセス',next(x for x in d if x['metric_id']=='D02-007')['comparison_interpretation'])

    def test_missing_currency_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'sample.csv'
            src.write_text('instrument,side,entry_time,exit_time,quantity,net_pnl\nEURJPY,LONG,2026-11-20 10:00,2026-11-20 10:05,1,42\n',encoding='utf-8')
            with self.assertRaisesRegex(ev.DataError,'Currency'):
                ev.read_trades(src,None,'Asia/Tokyo',None)

    def test_mixed_currency_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'mixed.csv'
            src.write_text('instrument,side,entry_time,exit_time,quantity,net_pnl,currency\nEURJPY,LONG,2026-11-20 10:00,2026-11-20 10:05,1,42,JPY\nEURUSD,SHORT,2026-11-20 10:10,2026-11-20 10:15,1,-5,USD\n',encoding='utf-8')
            with self.assertRaisesRegex(ev.DataError,'Mixed'):
                ev.read_trades(src,None,'Asia/Tokyo',None)

    def test_duplicate_ids_and_invalid_time_are_rejected(self):
        template='trade_id,instrument,side,entry_time,exit_time,quantity,net_pnl,currency\n'
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data.csv'
            p.write_text(template+'A,X,LONG,2026-01-01 10:00,2026-01-01 10:05,1,100,JPY\nA,X,SHORT,2026-01-01 10:10,2026-01-01 10:15,1,-100,JPY\n')
            with self.assertRaisesRegex(ev.DataError,'repeated trade_id'):
                ev.read_trades(p,None,'Asia/Tokyo',None)
            p.write_text(template+'A,X,LONG,2026-01-01 10:10,2026-01-01 10:05,1,100,JPY\n')
            with self.assertRaisesRegex(ev.DataError,'exit before entry'):
                ev.read_trades(p,None,'Asia/Tokyo',None)

    def test_cli_creates_all_expected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            cp=subprocess.run([sys.executable,str(ROOT/'tools/evaluate_trades.py'),'--input',str(self.sample),'--mode','lite','--out',str(out)],capture_output=True,text=True)
            self.assertEqual(cp.returncode,0,cp.stderr)
            self.assertTrue((out/'A'/'evaluation_lite.xlsx').exists())
            self.assertTrue((out/'A'/'gap_analysis_lite.csv').exists())
            self.assertTrue((out/'A'/'analysis_report.md').exists())
            self.assertTrue((out/'A'/'behavior_analysis.md').exists())
            with (out/'A'/'gap_analysis_lite.csv').open(encoding='utf-8-sig',newline='') as f:
                self.assertEqual(len(list(csv.DictReader(f))),76)
            with (out/'provenance.json').open(encoding='utf-8') as f:
                self.assertEqual(json.load(f)['datasets'][0]['metric_count'],76)

    def test_cli_column_mapping_with_japanese_aliases(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'jp.csv'
            p.write_text('銘柄,売買,新規日時,決済日時,数量,純損益,通貨\nUSDJPY,買,2026-11-01 10:00,2026-11-01 10:05,1,250,JPY\n',encoding='utf-8-sig')
            ts,_=ev.read_trades(p,None,'Asia/Tokyo',None)
            self.assertEqual(len(ts),1)
            self.assertEqual(ts[0].side,'LONG')


if __name__=='__main__':
    unittest.main()
