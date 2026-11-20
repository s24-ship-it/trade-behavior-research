#!/usr/bin/env python3
"""Public, deterministic CFD/FX trade-history screening.

The script intentionally does NOT diagnose mental states, infer traits from trades,
produce live trading orders, or invent unsupported metrics. It exports a complete
379/76-row evaluation with explicit missing-evidence statuses and reviewable gaps.
"""
from __future__ import annotations

import argparse
import hashlib
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
import json
import math
from pathlib import Path
import re
import statistics
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / 'registry' / 'metrics_full_379.json'
SELECTION_PATH = ROOT / 'registry' / 'priority_lite_selection.json'
IDEAL_PATH = ROOT / 'benchmark' / 'quant-omega' / 'ideal_model_full_379.json'

# Standard input is one COMPLETE round-trip per row. Individual fills must first
# be paired using the broker's position accounting rules, not guessed here.
ALIASES = {
    'trade_id': ['trade_id', 'id', 'position_id', 'tradeid', '取引id', '建玉id'],
    'instrument': ['instrument', 'symbol', 'ticker', '銘柄', '商品', '取引銘柄'],
    'side': ['side', 'direction', 'buy_sell', '売買', '方向', '新規売買'],
    'entry_time': ['entry_time', 'open_time', 'opened_at', 'entry_datetime', '新規日時', '建日時', '建玉日時', '新規約定日時'],
    'exit_time': ['exit_time', 'close_time', 'closed_at', 'exit_datetime', '決済日時', '決済約定日時'],
    'entry_price': ['entry_price', 'open_price', '建値', '新規約定価格'],
    'exit_price': ['exit_price', 'close_price', '決済価格', '決済約定価格'],
    'quantity': ['quantity', 'qty', 'lots', 'volume', '数量', '取引数量', 'ロット'],
    'net_pnl': ['net_pnl', 'realized_net_pnl', 'net_profit', '純損益', '損益（円）', '確定損益円'],
    'gross_pnl': ['gross_pnl', 'gross_profit', 'gross_result', '粗損益'],
    'fees': ['fees', 'total_fees', 'commission', 'costs', '手数料', '諸費用'],
    'currency': ['currency', 'pnl_currency', '損益通貨', '決済通貨', '通貨'],
}
MANDATORY = ('instrument', 'side', 'entry_time', 'exit_time', 'quantity')
VALUES_REQUIRED_ONE_OF = ('net_pnl', 'gross_pnl')
VALUE_FIELDS = ('entry_price', 'exit_price', 'quantity', 'net_pnl', 'gross_pnl', 'fees')
OUTPUT_FIELDS = [
    'dataset_id', 'priority', 'category_id', 'category', 'metric_id', 'metric_name',
    'required_data', 'inference_type', 'assessment_class', 'numeric_value', 'unit',
    'qualitative_finding', 'effective_n', 'evidence_level', 'assessment_status',
    'ideal_process_quality_target', 'ideal_behavior', 'verification_method',
    'falsification', 'score_1_5', 'score_source', 'process_gap', 'gap_status',
    'alternative_explanations', 'uncertainty', 'next_validation', 'candidate_action',
    'source_reference', 'data_asof_utc', 'source_sha256',
]


class DataError(ValueError):
    """Data is not valid enough to analyze without assumptions."""


@dataclass(frozen=True)
class Trade:
    trade_id: str
    instrument: str
    side: str
    entry_time: datetime
    exit_time: datetime
    quantity: float
    net_pnl: float
    currency: str
    fees: float | None
    gross_pnl: float | None
    entry_price: float | None
    exit_price: float | None

    @property
    def hold_minutes(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds() / 60


def norm_key(value: str) -> str:
    return re.sub(r'[\s_\-（）()]', '', str(value)).casefold()


def resolve_columns(header: list[str], column_mapping: dict | None) -> dict[str, str]:
    indexed = {norm_key(k): k for k in header}
    out = {}
    overrides = column_mapping or {}
    extra = set(overrides) - set(ALIASES)
    if extra:
        raise DataError(f'Unknown mapping keys: {sorted(extra)}')
    for key, names in ALIASES.items():
        user_col = overrides.get(key)
        if user_col:
            if user_col not in header:
                raise DataError(f'Column {key} maps to missing column {user_col!r}')
            out[key] = user_col
            continue
        for candidate in names:
            if norm_key(candidate) in indexed:
                out[key] = indexed[norm_key(candidate)]
                break
    missing = [k for k in MANDATORY if k not in out]
    if missing:
        raise DataError(f'Missing required columns {missing}. See config/columns.example.json.')
    if not any(k in out for k in VALUES_REQUIRED_ONE_OF):
        raise DataError('net_pnl or gross_pnl (with fees) is required; raw fills are not round-trips.')
    return out


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    if not path.is_file():
        raise DataError(f'Missing input file: {path}')
    if path.suffix.lower() == '.csv':
        errors = []
        for encoding in ('utf-8-sig', 'cp932'):
            try:
                with path.open('r', encoding=encoding, newline='') as f:
                    dr = csv.DictReader(f)
                    header = dr.fieldnames or []
                    rows = list(dr)
                break
            except UnicodeError as ex:
                errors.append(f'{encoding}: {ex}')
        else:
            raise DataError(f'Cannot decode CSV: {errors}')
    elif path.suffix.lower() == '.xlsx':
        try:
            from openpyxl import load_workbook
        except ImportError as e:
            raise DataError('Install openpyxl to read XLSX: pip install -r requirements.txt') from e
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        ws.reset_dimensions()
        it = ws.iter_rows(values_only=True)
        header = [str(v or '') for v in next(it)]
        rows = [dict(zip(header, [v if v is not None else '' for v in row])) for row in it]
        wb.close()
    else:
        raise DataError(f'Unsupported format {path.suffix}; supported: CSV, XLSX')
    if not header:
        raise DataError('No header')
    if len(header) != len(set(header)):
        raise DataError('Duplicate header names; select unique columns')
    return header, rows


def number(v, key, rownum, optional=False):
    if v is None or str(v).strip() in ('', '-', 'NA', 'N/A'):
        if optional:
            return None
        raise DataError(f'Row {rownum}: missing number: {key}')
    s = str(v).replace(',', '').replace('¥', '').replace('￥', '').replace(' ', '').strip()
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        x = float(s)
    except (ValueError, TypeError) as ex:
        raise DataError(f'Row {rownum}: non-numeric {key}={v!r}') from ex
    if not math.isfinite(x):
        raise DataError(f'Row {rownum}: non-finite {key}')
    return x


def parse_dt(value, rownum, key, tz_name):
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip().replace('/', '-')
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        try:
            dt = datetime.fromisoformat(s)
        except ValueError as e:
            raise DataError(f'Row {rownum}: invalid {key}={value!r}. Use ISO 8601.') from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(tz_name))
    return dt.astimezone(timezone.utc)


def read_trades(path: Path, columns: dict | None, tz_name: str, default_currency: str | None) -> tuple[list[Trade], list[str]]:
    header, rows = read_rows(path)
    mapping = resolve_columns(header, columns)
    if 'currency' not in mapping and not default_currency:
        raise DataError('Currency not declared. Add currency column or --currency JPY (explicit assumption).')
    if 'gross_pnl' in mapping and 'net_pnl' not in mapping and 'fees' not in mapping:
        raise DataError('gross_pnl without fees cannot be treated as net pnl; add fees or net_pnl.')
    warnings = []
    if any(k in mapping for k in ('net_pnl', 'gross_pnl')) and ('entry_price' not in mapping or 'exit_price' not in mapping):
        warnings.append('No entry/exit price: trade-level outcomes only; execution price quality not evaluated.')
    if 'entry_time' in mapping and 'exit_time' in mapping:
        warnings.append(f'Naive timestamps (if any) interpreted in {tz_name}; check DST and broker timezone.')
    trades = []
    seen = set()
    for idx, record in enumerate(rows, 2):
        if all(not str(v).strip() for v in record.values()):
            continue
        get = lambda k: record.get(mapping[k]) if k in mapping else None
        instr = str(get('instrument') or '').strip()
        if not instr:
            raise DataError(f'Row {idx}: missing instrument')
        raw_side = norm_key(str(get('side') or ''))
        if raw_side in ('buy', 'long', '買', '買い', '買建', '新規買', '1', 'b'):
            side = 'LONG'
        elif raw_side in ('sell', 'short', '売', '売り', '売建', '新規売', '-1', 's'):
            side = 'SHORT'
        else:
            raise DataError(f'Row {idx}: unknown side {get("side")!r}; use LONG/SHORT, buy/sell.')
        en = parse_dt(get('entry_time'), idx, 'entry_time', tz_name)
        ex = parse_dt(get('exit_time'), idx, 'exit_time', tz_name)
        if ex < en:
            raise DataError(f'Row {idx}: exit before entry')
        qty = number(get('quantity'), 'quantity', idx)
        if qty <= 0:
            raise DataError(f'Row {idx}: quantity must be positive')
        net = number(get('net_pnl'), 'net_pnl', idx, optional=True)
        gross = number(get('gross_pnl'), 'gross_pnl', idx, optional=True)
        fees = number(get('fees'), 'fees', idx, optional=True)
        if net is None:
            if gross is None or fees is None:
                raise DataError(f'Row {idx}: need net_pnl or both gross_pnl and fees')
            net = gross - fees
        if fees is not None and fees < 0:
            raise DataError(f'Row {idx}: fees must be >=0')
        if net is not None and gross is not None and fees is not None:
            tol = max(0.01, abs(gross) * 1e-7)
            if abs(net - (gross - fees)) > tol:
                raise DataError(f'Row {idx}: net_pnl disagrees with gross_pnl minus fees. Declare consistent basis.')
        curr = str(get('currency') or default_currency or '').strip().upper()
        if not curr:
            raise DataError(f'Row {idx}: currency is missing')
        identifier = str(get('trade_id') or f'ROW_{idx-1}').strip()
        if identifier in seen:
            raise DataError(f'Row {idx}: repeated trade_id={identifier!r}; check duplicate or partial fills')
        seen.add(identifier)
        entry_price = number(get('entry_price'), 'entry_price', idx, optional=True)
        exit_price = number(get('exit_price'), 'exit_price', idx, optional=True)
        trades.append(Trade(identifier, instr, side, en, ex, qty, net, curr, fees, gross, entry_price, exit_price))
    if not trades:
        raise DataError('No completed trade rows found')
    currencies = {t.currency for t in trades}
    if len(currencies) > 1:
        raise DataError('Mixed P&L currencies; convert all to one verified base currency at each trade date first: ' + ', '.join(sorted(currencies)))
    trades.sort(key=lambda x: (x.exit_time, x.entry_time, x.trade_id))
    return trades, warnings


def mean(xs):
    return statistics.mean(xs) if xs else None


def med(xs):
    return statistics.median(xs) if xs else None


def pf(xs):
    win = sum(x for x in xs if x > 0)
    loss = -sum(x for x in xs if x < 0)
    return win / loss if loss > 0 else None


def pct(xs, fraction):
    if not xs:
        return None
    a = sorted(xs)
    p = (len(a) - 1) * fraction
    lo, hi = math.floor(p), math.ceil(p)
    return a[lo] * (hi - p) + a[hi] * (p - lo)


def run_lengths(outcomes, sign):
    counts = []
    c = 0
    for v in outcomes:
        if (v > 0 if sign == 1 else v < 0):
            c += 1
        elif c:
            counts.append(c)
            c = 0
    if c:
        counts.append(c)
    return counts


def fmt(v):
    if v is None:
        return 'NA'
    if isinstance(v, (int, float)):
        return f'{v:,.4f}'
    return str(v)


def measurements(trades: list[Trade]) -> dict[str, dict]:
    """Only measurements independently supported by round-trip trade records."""
    res = {}
    n = len(trades)
    xs = [t.net_pnl for t in trades]
    wins = [x for x in xs if x > 0]
    losses = [x for x in xs if x < 0]
    pos = [t for t in trades if t.net_pnl > 0]
    neg = [t for t in trades if t.net_pnl < 0]
    currency = trades[0].currency

    def put(mid, value, unit='', note='', sample=None, status='MEASURED', alternative='', validation=''):
        if value is None or value == {}:
            return
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            status = 'DESCRIPTIVE'
        res[mid] = dict(value=value, unit=unit, note=note, n=sample if sample is not None else n,
                        status=status, alternative=alternative,
                        validation=validation or 'Validate against broker statements and hold-out periods.')

    money = currency
    put('D01-009', 0, 'normalized-row duplicate IDs',
        '入力した完結取引行のtrade_idは重複なし。原始約定の網羅性・重複は別途監査が必要', status='PARTIAL')
    put('D01-010', 0, 'timestamp order errors', 'すべての行でentry_time <= exit_timeを検査。タイムゾーン元データは要照合', status='PARTIAL')
    put('D02-001', sum(xs), money, '口座入出金・含み損益を含まない実現純損益合計')
    put('D02-002', {'gross_winnings':sum(wins), 'gross_losses':sum(losses)}, money, '実現純損益の正負別集計')
    put('D02-003', len(wins) / n, 'ratio', f'勝:{len(wins)} / 負:{len(losses)} / 建値:{n-len(wins)-len(losses)}')
    put('D02-004', {'avg_win':mean(wins), 'avg_loss':mean(losses)}, money, '利益・損失別の平均')
    if wins and losses:
        put('D02-005', mean(wins)/abs(mean(losses)), 'multiple', '平均利益÷平均損失の絶対値')
    if losses:
        put('D02-006', pf(xs), 'multiple', '純利益合計÷純損失絶対値合計')
    elif wins:
        res['D02-006'] = dict(value=None, unit='multiple', note='損失未観測のためPFは有限値として推定不可。無敗を意味しない。', n=n,
                              status='NOT_ESTIMABLE',alternative='sample selection / lucky sequence',validation='Increase independent sample and stress test')
    put('D02-007', mean(xs), money+'/trade', '取引独立性と変動相場を考慮して期間外検証が必要')
    if wins and losses:
        put('D02-008', abs(mean(losses))/(mean(wins)+abs(mean(losses))), 'ratio', '固定損益分布での損益分岐勝率')
    put('D02-009', med(xs), money, '純損益の中央値')
    put('D02-011', {d: round(sum(t.net_pnl for t in trades if t.exit_time.date().isoformat()==d), 4)
                       for d in sorted({t.exit_time.date().isoformat() for t in trades})}, money+'/day', 'UTC決済日ベース')
    put('D02-012', sum(xs), money, '実現損益の累積終値。口座資産曲線や真のドローダウンではない',status='PARTIAL')
    if all(t.fees is not None for t in trades):
        put('D02-014', sum(t.fees for t in trades), money, '表示済み純損益に含まれる明示費用の合計。追加控除しない')
    if n>=2:
        put('D03-001', statistics.stdev(xs), money+'/trade', '標本標準偏差')
    if n>=3:
        sd = statistics.pstdev(xs)
        if sd>0:
            skew = sum(((x-mean(xs))/sd)**3 for x in xs)/n
            put('D03-002', skew, 'skewness', '非補正母モーメントによる記述的歪度',status='DESCRIPTIVE')
    if n>=4:
        sd = statistics.pstdev(xs)
        if sd>0:
            kurt = sum(((x-mean(xs))/sd)**4 for x in xs)/n - 3
            put('D03-003', kurt, 'excess kurtosis', '非補正母モーメントによる超過尖度',status='DESCRIPTIVE')
    put('D03-004', {'p05':pct(xs,.05),'p25':pct(xs,.25),'p50':pct(xs,.5),'p75':pct(xs,.75),'p95':pct(xs,.95)},money,'線形補間分位点')
    put('D03-005', {'max_win':max(xs),'max_loss':min(xs)},money,'1取引ごとの極端値')
    if n>=15:
        sorted_x=sorted(xs)
        trimmed=sorted_x[1:-1]
        if any(x<0 for x in trimmed):
            put('D03-006', pf(trimmed), 'multiple', '最大損失・最大利益を各1件除外した感度確認（任意切捨てではない）')
    if wins:
        put('D03-007', sum(sorted(wins,reverse=True)[:10])/sum(wins),'ratio','純利益取引の上位10件による獲得利益寄与')
    if losses:
        put('D03-008', abs(sum(sorted(losses)[:min(5,len(losses))])) / abs(sum(losses)),'ratio','ワースト最大5取引による総損失寄与')
    if wins and losses:
        put('D03-011', {'mean_win':mean(wins),'mean_loss_abs':abs(mean(losses))},money,'損益の非対称性')

    instruments=defaultdict(list)
    for t in trades:
        instruments[t.instrument].append(t)
    by_inst = lambda fn: {k:fn(v) for k,v in sorted(instruments.items())}
    put('D06-001', by_inst(lambda g:round(sum(x.net_pnl for x in g),4)), money, '銘柄別実現純損益')
    put('D06-002', by_inst(lambda g:round(sum(x.net_pnl>0 for x in g)/len(g),4)), 'ratio', '銘柄別勝率')
    put('D06-003', by_inst(lambda g:round(mean([x.net_pnl for x in g]),4)),money+'/trade','銘柄別期待損益；銘柄横断では契約倍率・リスク資産額を要調整')
    put('D06-004', {k:round(pf([x.net_pnl for x in v]),4) if pf([x.net_pnl for x in v]) is not None else None for k,v in sorted(instruments.items())},'multiple','銘柄別PF；損失ゼロの群はnull')
    put('D06-005', by_inst(len), 'trades', '銘柄別取引件数')
    put('D06-006', by_inst(lambda g:round(mean([x.hold_minutes for x in g]),4)), 'minutes', '銘柄別平均保有時間')
    put('D06-007', by_inst(lambda g:{k:round(mean([t.net_pnl for t in g if t.side==k]),4) if any(t.side==k for t in g) else None for k in ['LONG','SHORT']}),money+'/trade','銘柄×方向の平均実現損益')
    if losses:
        put('D06-010', {k:round(abs(sum(x.net_pnl for x in v if x.net_pnl<0))/abs(sum(losses)),4) for k,v in sorted(instruments.items())},'ratio','銘柄別・全損失への寄与')

    direction={s:[t for t in trades if t.side==s] for s in ('LONG','SHORT')}
    for side,mid in (('LONG','D07-001'),('SHORT','D07-002')):
        if direction[side]:put(mid,sum(t.net_pnl>0 for t in direction[side])/len(direction[side]),'ratio',f'{side}のみ')
    if direction['LONG'] and direction['SHORT']:
        put('D07-003',mean([t.net_pnl for t in direction['LONG']])-mean([t.net_pnl for t in direction['SHORT']]),money+'/trade','LONG- SHORT平均損益差；相場環境を未調整')
    put('D07-004', {side:round(abs(mean([t.net_pnl for t in direction[side] if t.net_pnl<0])),4) if any(t.net_pnl<0 for t in direction[side]) else None for side in ('LONG','SHORT')},money,'方向別平均損失')
    put('D07-005', {side:round(mean([t.hold_minutes for t in direction[side]]),4) if direction[side] else None for side in ('LONG','SHORT')},'minutes','方向別平均保有時間')

    put('D10-001', {'mean':mean([t.hold_minutes for t in trades]),'median':med([t.hold_minutes for t in trades])},'minutes','完結取引のみ。未決済は対象外')
    if pos:
        put('D10-002', mean([t.hold_minutes for t in pos]), 'minutes', '勝ち取引平均保有時間（損切り遅延の証拠とは限らない）',sample=len(pos))
    if neg:
        put('D10-003', mean([t.hold_minutes for t in neg]), 'minutes', '負け取引平均保有時間（戦略条件の調整が必要）',sample=len(neg))
    bins=[('0-5m',0,5),('5-15m',5,15),('15-60m',15,60),('60m+',60,float('inf'))]
    groups={name:[x for x in trades if lo<=x.hold_minutes<hi] for name,lo,hi in bins}
    put('D10-004', {k:round(sum(t.net_pnl>0 for t in v)/len(v),4) if v else None for k,v in groups.items()},'ratio','保有時間帯別勝率。結果から時間帯が決まるため因果・予測には使えない')
    put('D10-005', {k:round(mean([t.net_pnl for t in v]),4) if v else None for k,v in groups.items()},money+'/trade','保有時間帯別損益。事後条件付けのためルール効果は未確認')
    total_hold = sum(t.hold_minutes for t in trades)
    if total_hold>0:
        put('D10-006', sum(xs)/(total_hold/60),money+'/position-hour','総実現損益÷全ポジション保有時間；重複保有を除去していない')

    hour=defaultdict(list); weekday=defaultdict(list); month=defaultdict(list)
    for t in trades:
        dt=t.entry_time.astimezone(ZoneInfo('Asia/Tokyo'))
        hour[dt.hour].append(t)
        weekday[dt.strftime('%a')].append(t)
        month[dt.strftime('%Y-%m')].append(t)
    pack=lambda g,fn:{str(k):fn(v) for k,v in sorted(g.items(),key=lambda q:str(q[0]))}
    put('D11-001',pack(hour,lambda v:round(sum(t.net_pnl>0 for t in v)/len(v),4)),'ratio','JSTエントリー時間帯別勝率。複数比較補正前')
    put('D11-002',pack(hour,lambda v:round(mean([t.net_pnl for t in v]),4)),money+'/trade','JSTエントリー時間帯別期待損益。複数比較補正前')
    put('D11-003',pack(weekday,lambda v:round(sum(t.net_pnl>0 for t in v)/len(v),4)),'ratio','JSTエントリー曜日別勝率。複数比較補正前')
    put('D11-004',pack(weekday,lambda v:round(pf([t.net_pnl for t in v]),4) if pf([t.net_pnl for t in v]) is not None else None),'multiple','曜日別PF。損失ゼロの群はnull')
    put('D11-005',pack(month,lambda v:round(sum(t.net_pnl for t in v),4)),money,'JSTエントリー月ごとの実現純損益')
    put('D11-012',sum(t.entry_time.date()!=t.exit_time.date() for t in trades),'trades','UTC日付を跨いだ件数。営業日・週跨ぎの厳密な判定とは異なる',status='PARTIAL')

    yn=[t.net_pnl for t in trades]
    put('D16-001', {'max_win_streak':max(run_lengths(yn,1),default=0),'max_loss_streak':max(run_lengths(yn,-1),default=0)},'trades','決済日時順。分割決済や重複取引の独立性には注意')
    put('D16-002', {'avg_win_streak':mean(run_lengths(yn,1)),'avg_loss_streak':mean(run_lengths(yn,-1))},'trades','連勝・連敗長の平均')
    after_win=[trades[i].net_pnl>0 for i in range(1,n) if trades[i-1].net_pnl>0]
    after_loss=[trades[i].net_pnl>0 for i in range(1,n) if trades[i-1].net_pnl<0]
    if after_win:put('D16-003',sum(after_win)/len(after_win),'ratio','直前の完結取引が勝ちだった場合の次回勝率',sample=len(after_win))
    if after_loss:put('D16-004',sum(after_loss)/len(after_loss),'ratio','直前の完結取引が負けだった場合の次回勝率',sample=len(after_loss))
    # A streak of at least two consecutive losses (wins) is distinct from one loss.
    after_loss_streak=[];after_win_streak=[];after_loss_single=[]
    for i in range(1,n):
        if trades[i-1].net_pnl<0:
            after_loss_single.append(trades[i].quantity)
        if i>=2 and all(trades[j].net_pnl<0 for j in (i-2,i-1)):
            after_loss_streak.append(trades[i].quantity)
        if i>=2 and all(trades[j].net_pnl>0 for j in (i-2,i-1)):
            after_win_streak.append(trades[i].quantity)
    if len(instruments)==1:
        base_size=mean([t.quantity for t in trades])
        if after_loss_streak:
            put('D16-006',mean(after_loss_streak)/base_size,'multiple',
                '2連敗以上の直後の平均ロット÷全取引の平均ロット。銘柄単一だが市場ボラは未調整',
                status='DESCRIPTIVE',sample=len(after_loss_streak))
        if after_win_streak:
            put('D16-007',mean(after_win_streak)/base_size,'multiple',
                '2連勝以上の直後の平均ロット÷全取引の平均ロット。銘柄単一だが市場ボラは未調整',
                status='DESCRIPTIVE',sample=len(after_win_streak))
        if after_loss_single:
            put('P03-005',mean(after_loss_single)/base_size,'multiple',
                '単発損失後の平均取引数量÷全取引平均。行動の代理指標であり心理の証明ではない',
                status='DESCRIPTIVE',sample=len(after_loss_single))
    elif after_loss_streak:
        res['D16-006'] = dict(value=None,unit='',note='異銘柄の数量単位は比較不可。銘柄別・リスク額に標準化後に再計測',n=n,status='NEEDS_NORMALIZATION',alternative='',validation='Normalize per instrument contract multiplier and stop risk')
    gaps = []
    after_loss_gap = []
    after_loss_reentry_count=0
    for i in range(1,n):
        prev=trades[i-1];curr=trades[i]
        lag=(curr.entry_time - prev.exit_time).total_seconds()/60
        if lag<0:
            continue # overlapping trades cannot be treated as sequential decisions
        gaps.append((lag,curr.net_pnl))
        if prev.net_pnl<0:
            after_loss_gap.append(lag)
            if lag<=10: after_loss_reentry_count+=1
    if after_loss_gap:
        put('D16-008',med(after_loss_gap),'minutes','損失確定後の次の非重複参入までの中央値。感情は推定不可',sample=len(after_loss_gap))
    if gaps:
        put('P03-003',sum(lag<=10 for lag,_ in gaps)/len(gaps),'ratio',
            '全ての非重複取引で決済後10分以内に再参入する割合。動機は推定不可',
            sample=len(gaps),status='DESCRIPTIVE')
        put('D16-009',{'0-10m':mean([y for x,y in gaps if x<=10]),'10m+':mean([y for x,y in gaps if x>10])},money+'/trade','次エントリーまでの間隔別結果。後決済順は時間重複のため非重複のみ')
    if len(trades)>=2:
        entry_days=len(set(t.entry_time.date() for t in trades))
        put('D16-012',len(trades)/entry_days,'trades/active_day','取引のあった日だけの頻度。無取引日を含まない')
    return res


def output_rows(dataset_id, trades, registry, ideal, lite_ids, mode, rating_by_id, path_names, source_hashes=None):
    values=measurements(trades)
    benchmark_by_id={m['metric_id']:m for m in ideal['full_metrics']}
    out=[]
    categories=set()
    for k,m in enumerate(registry['metrics']):
        if mode=='lite' and m['id'] not in lite_ids:
            continue
        bid=m['id'];bm=benchmark_by_id[bid]
        categories.add(m['category_id'])
        inference=m['inference_level']
        evidence=values.get(bid)
        if inference=='not_identifiable':
            status='NOT_IDENTIFIABLE_FROM_TRADES'
        elif inference=='hypothesis':
            status='HYPOTHESIS_ONLY'
        elif inference=='counterfactual':
            status='NEEDS_PRICE_PATH_AND_REPLAY'
        elif inference=='inference':
            status='NEEDS_STATISTICAL_VALIDATION'
        else:
            status='NEEDS_DATA'
        if evidence:
            status=evidence['status']
        cls=bm['assessment_class'];target=bm['ideal_process_quality_target']
        rating=rating_by_id.get((dataset_id,bid),{})
        score=rating.get('score_1_5')
        ref=rating.get('evidence_reference','')
        scored=cls=='規範的な運用品質' and isinstance(score,int) and bool(ref) and rating.get('evidence_level') in ('L1','L2','L3','L4')
        gap=(target-score) if scored and isinstance(target,(int,float)) else None
        gap_status='RATED_PROCESS_GAP_REVIEW_REQUIRED' if scored else ('NOT_SCOREABLE' if target is None else 'EVIDENCE_GAP')
        note=evidence['note'] if evidence else ''
        alt=evidence.get('alternative','') if evidence else '相場・手法・銘柄・取引サイズ等の交絡要因を点検'
        uncertainty='独立性・費用・契約条件・サンプル選択・期間外検証未確認'
        if inference=='not_identifiable':
            uncertainty='取引履歴から個人の脳状態・神経特性・生育歴は同定できない。推定・採点禁止。'
        elif inference=='hypothesis':
            uncertainty='行動上の手掛かりは心理状態や人格の診断にはならない。代替説明が必要。'
        elif evidence and evidence['status']=='PARTIAL':
            uncertainty='一部観測のみ。原始記録と追加データによる裏付けが必要。'
        out.append({
            'dataset_id':dataset_id, 'priority':bm['priority'],'category_id':m['category_id'],
            'category':m['category'], 'metric_id':bid,'metric_name':m['metric'],
            'required_data':','.join(m['required_data']),'inference_type':inference,'assessment_class':cls,
            'numeric_value':evidence['value'] if evidence else None,'unit':evidence['unit'] if evidence else '',
            'qualitative_finding':note,'effective_n':evidence['n'] if evidence else None,
            'evidence_level':'L1' if evidence and evidence['value'] is not None else '',
            'assessment_status':status,'ideal_process_quality_target':target,
            'ideal_behavior':bm['ideal_behavior'],'verification_method':bm['verification_method'],
            'falsification':bm['falsification_and_failure'],
            'score_1_5':score if scored else None,'score_source':ref if scored else '',
            'process_gap':gap,'gap_status':gap_status,
            'alternative_explanations':alt,
            'uncertainty':uncertainty,
            'next_validation':evidence['validation'] if evidence else bm['verification_method'],
            'candidate_action':bm['ideal_behavior'] if cls=='規範的な運用品質' else '探索的な分析を事前登録して検証。' if cls!='売買履歴から識別不可' else '取引履歴による評価を行わない。',
            'source_reference':';'.join(path_names),
            'data_asof_utc':max(t.exit_time for t in trades).isoformat(),
            'source_sha256':';'.join(f'{k}:{v}' for k,v in sorted((source_hashes or {}).items())),
        })
    expected=76 if mode=='lite' else 379
    if len(out)!=expected or len(categories)!=29:
        raise RuntimeError(f'Integrity failure: metrics={len(out)} categories={len(categories)}')
    return out


def read_ratings(path):
    if not path:
        return {}
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        rdr=csv.DictReader(f)
        needed={'dataset_id','metric_id','score_1_5','evidence_level','evidence_reference'}
        if not needed.issubset(set(rdr.fieldnames or [])):
            raise DataError(f'ratings CSV requires {sorted(needed)}')
        out={}
        for r in rdr:
            if not str(r.get('score_1_5') or '').strip():
                continue
            try:
                score=int(r['score_1_5'])
            except ValueError as e:
                raise DataError('Ratings must be integers 1..5') from e
            if score not in (1,2,3,4,5):
                raise DataError('Ratings must be integers 1..5')
            if not r['evidence_reference'] or r['evidence_level'] not in ('L1','L2','L3','L4'):
                raise DataError('Ratings need evidence level and nonblank source_reference')
            out[(r['dataset_id'],r['metric_id'])]={**r,'score_1_5':score}
        return out


def safe_spreadsheet_value(value):
    if isinstance(value,str) and value and value.lstrip().startswith(('=','+','-','@')):
        return "'" + value
    return value


def write_csv(path,records,fields=None):
    fields=fields or list(records[0].keys())
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        w.writeheader()
        w.writerows([{k:safe_spreadsheet_value(v) for k,v in row.items()} for row in records])


def make_gap_rows(evaluation_rows):
    """Do not subtract numeric P&L from a normative 1..5 rubric target."""
    out=[]
    for r in evaluation_rows:
        val=r['numeric_value']
        if r['assessment_class']=='売買履歴から識別不可':
            description='比較不可: 売買履歴から脳・生育・神経特性は同定できない'
        elif val is None:
            description=f"証拠不足: {r['required_data']} を確認し、判断時点の情報として測定する"
        elif r['assessment_class']=='条件依存の評価軸':
            description=f'観測値 {fmt(val)} {r["unit"]}。優劣の一律判断不可、比較条件・費用・OOSを確認'
        elif r['assessment_class']=='心理・認知仮説':
            description='観測は心理仮説の証明ではない。反対仮説を保持し、本人の同意なく診断しない'
        else:
            description=f'観測値 {fmt(val)} {r["unit"]}。理想運用プロセスとの適合は別途監査'
        out.append({
            'dataset_id':r['dataset_id'],'metric_id':r['metric_id'],'category':r['category'],
            'metric_name':r['metric_name'],'assessment_class':r['assessment_class'],
            'observed_value':val,'observed_unit':r['unit'],
            'observed_status':r['assessment_status'], 'observed_finding':r['qualitative_finding'],
            'ideal_quality_target':r['ideal_process_quality_target'],
            'ideal_behavior':r['ideal_behavior'],'comparison_interpretation':description,
            'user_process_score':r['score_1_5'],'process_gap_points':r['process_gap'],
            'gap_status':r['gap_status'],'evidence_source':r['score_source'],
            'verification':r['next_validation'],'candidate_action':r['candidate_action'],
            'caution':r['uncertainty'],
        })
    return out


def make_suggestions(trades, outputs):
    by_id={r['metric_id']:r for r in outputs}
    n=len(trades)
    suggestions=[]
    def add(level,topic,ids,observation,alt,action,check):
        suggestions.append({'priority':level,'topic':topic,'metric_ids':','.join(ids),'observation':observation,
                            'alternative_explanation':alt,'candidate_control':action,'falsification_test':check})
    expectancy=by_id['D02-007']['numeric_value']
    if expectancy is not None and expectancy<=0:
        add('P1','費用控除後期待値の検証',['D02-007','D02-006'],
            f'観測平均損益 {fmt(expectancy)} {trades[0].currency}/trade（{n}件）。',
            '少数の大きな損失・特定相場・サンプル選択。',
            '取引対象・時間帯・条件を事前固定してOOSを再検証。負の期待値が続く場合は取引停止を検討。',
            '費用と実現/未実現損益を照合し、先行期間で規則を固定して後続期間で確認。')
    if n<30:
        add('P1','サンプル不足',['D21-002','D21-015'],
            f'{n}件の完結取引しかなく統計的優位性は未確立。',
            '分割約定の誤カウント、同一イベントに依存する多数取引。',
            '独立した意思決定イベント数と市場状態のカバレッジを確認。過剰最適化しない。',
            '事前定義した次期間で測定を継続し信頼区間を提示。')
    win_h=by_id['D10-002']['numeric_value'];lose_h=by_id['D10-003']['numeric_value']
    if isinstance(win_h,(int,float)) and isinstance(lose_h,(int,float)) and win_h>0 and lose_h>1.5*win_h:
        add('P2','損失保有時間の相対的長期化',['D10-002','D10-003','D09-007'],
            f'平均保有時間：利益 {fmt(win_h)} 分 / 損失 {fmt(lose_h)} 分。',
            '損失保有の長期化は損切り遅延とは限らず、時間帯・銘柄・予定ストップが影響。',
            '初期SL・注文変更履歴・MFE/MAEを入手し、事前ストップ遵守率を検証。',
            '銘柄×方向×相場別に保有時間をマッチングして比較。')
    if len({t.instrument for t in trades})==1:
        ratio=measurements(trades).get('P03-005',{}).get('value')
        if isinstance(ratio,(int,float)) and ratio>1.3:
            add('P2','損失後のロット増加',['P03-005','D17-007','P04-001'],
                f'損失後の数量平均比 {fmt(ratio)} 倍（説明仮説であり心理診断ではない）。',
                '戦略上のピラミッディング、ボラ調整、資産増減の影響。',
                'リスク額基準に換算し、連敗時の最大建玉増加を抑えるルールを比較。',
                '当時の戦略仕様と初期ストップ位置を照合。')
    loss_conc=by_id['D03-008']['numeric_value']
    if isinstance(loss_conc,(int,float)) and n>=30 and sum(t.net_pnl<0 for t in trades)>=10 and loss_conc>0.65:
        add('P2','損失の少数取引集中',['D03-008','D04-012'],
            f'ワースト5取引で全実現損失の {loss_conc:.1%} を占める。',
            '厚い裾の市場特性、取引サイズ不一致、契約倍率。',
            '1取引の想定損失額・日次リスク上限・流動性ギャップ対策を監査。',
            '費用・含み損・ロットを含めてストレステスト。')
    if not suggestions:
        add('P2','追加データでのエントリー／決済検証',['D08-001','D09-003','D09-004'],
            '取引単位の成績は確認可能だが、売買時点の価格経路は未提供。',
            '改善すべき条件が存在しない可能性もある。',
            'ティックまたは適切な分足・注文履歴を収集し、MFE/MAE・約定品質を監査。',
            '価格経路のタイムスタンプと意思決定時点を検証。')
    add('P3','学術的な心理・生育推定の制限',['P06-003','P07-004'],
        '取引履歴から脳機能や生育歴は特定できない。',
        '取引頻度は戦略仕様や取引環境の影響を受ける。',
        '本人の同意のない個人情報収集や診断をしない。意思決定の行動傾向だけを記述する。',
        '心理仮説の検証には任意の自己記録と適切な設計が必要。')
    return suggestions


def write_report(path, dataset_id, trades, outputs, suggestions, warnings, mode):
    b={r['metric_id']:r for r in outputs}
    measured=sum(r['numeric_value'] is not None for r in outputs)
    not_id=sum(r['assessment_status']=='NOT_IDENTIFIABLE_FROM_TRADES' for r in outputs)
    text=[f'# 売買履歴評価レポート | Dataset {dataset_id}', '',
          '**判定：RESEARCH_ONLY / 投資助言・取引指示ではない**',
          '',f'- 評価版：{mode.upper()} / 指標数：{len(outputs)} / カテゴリ数：29',
          f'- 完結取引数：{len(trades)} / 損益通貨：{trades[0].currency}',
          f'- 定量値あり：{measured} 指標 / 履歴だけでは同定不能：{not_id} 指標',
          f'- 評価開始UTC：{min(t.entry_time for t in trades).isoformat()}',
          f'- 評価終了UTC：{max(t.exit_time for t in trades).isoformat()}',
          '- 未決済建玉・残高・注文履歴・市場価格・日誌・経済イベントは未確認',
          '', '## 主要な計測値',
          '', '| 指標ID | 指標 | 観測値 | 状態 |', '|---|---|---:|---|']
    for mid in ['D02-001','D02-003','D02-006','D02-007','D03-008','D10-002','D10-003','D16-008']:
        if mid not in b: continue
        row=b[mid]
        text.append(f"| {mid} | {row['metric_name']} | {fmt(row['numeric_value'])} {row['unit']} | {row['assessment_status']} |")
    text.extend(['','## 主要な改善研究候補',''])
    for i,s in enumerate(suggestions,1):
        text.extend([f"### {i}. {s['topic']} ({s['priority']})",f"- 観測：{s['observation']}",
                     f"- 代替説明：{s['alternative_explanation']}",f"- 対策仮説：{s['candidate_control']}",
                     f"- 反証・検証：{s['falsification_test']}", f"- 関連指標：{s['metric_ids']}", ''])
    text.extend(['## 証拠・品質の制約', ''])
    text.extend([f'- {x}' for x in warnings])
    text.extend(['- 表示された統計的関連は因果関係や個人の性格の診断ではありません。',
                 '- PF・勝率・期待値の高低だけで戦略の有効性を保証しません。',
                 '- 理想モデルの5点はプロセス品質の規範であり、実現された利益率や勝率ではありません。',
                 '- 未評価行の数値やスコアを推測で補完せず、必要データを明示します。',
                 '- 仮説を採用する前に決定時点の情報可用性、スプレッド、金利・スリッページ、銘柄・時期分布、OOSを検証します。'])
    path.write_text('\n'.join(text)+'\n',encoding='utf-8')


def write_behavior(path, dataset_id, outputs):
    b={r['metric_id']:r for r in outputs}
    keys=['D10-002','D10-003','D16-003','D16-004','D16-006','D16-008','P03-003']
    lines=[f'# Dataset {dataset_id}｜行動分析（非診断）','',
           '売買行動の反復傾向を記述する研究メモです。心理状態・人格・神経発達・幼少期は判定しません。','',
           '| 関連指標 | 行動上の観測 | 留保 |','|---|---|---|']
    for k in keys:
        if k not in b:continue
        x=b[k]
        lines.append(f"| {k} {x['metric_name']} | {fmt(x['numeric_value'])} {x['unit']} | {x['uncertainty']} |")
    lines.extend(['','## 競合仮説の検証','',
                  '1. 損失後に取引が増えた場合：感情的な取り戻し行動のほか、機械的戦略、ボラティリティ上昇、シグナルの連続発生が説明候補です。',
                  '2. 損失の保有時間が長い場合：損切りの先延ばしのほか、ストップ設計・市場ごとの保有方針・強制決済条件が説明候補です。',
                  '3. 確認したい追加情報：注文変更履歴、当初SL/TP、戦略シグナル、当時の判断記録、銘柄別の契約倍率。',
                  '4. 神経機能・性格・生育環境は、売買履歴のみでは同定不能です。'])
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def excel_review_status(machine_status):
    # Excel dashboard uses Japanese controlled vocabulary; raw machine state is
    # retained in the note and CSV. Measurement != causal or psychological proof.
    if machine_status in ('MEASURED', 'DESCRIPTIVE'):
        return '評価済'
    if machine_status == 'PARTIAL':
        return 'レビュー待ち'
    if machine_status == 'HYPOTHESIS_ONLY':
        return '仮説段階'
    if machine_status == 'NOT_IDENTIFIABLE_FROM_TRADES':
        return '識別不可'
    if machine_status in ('NEEDS_DATA','NOT_ESTIMABLE','NEEDS_PRICE_PATH_AND_REPLAY','NEEDS_STATISTICAL_VALIDATION'):
        return '要追加データ'
    return 'レビュー待ち'


def fill_excel_sheet(sheet, rows):
    by_id={r['metric_id']:r for r in rows}
    filled=0
    for line in range(7,sheet.max_row+1):
        mid=sheet.cell(line,4).value
        if mid not in by_id:
            continue
        row=by_id[mid]
        raw=row['numeric_value']
        if isinstance(raw,str) and (raw.startswith('{') or raw.startswith('[')):
            val=None
        else:
            val=raw if isinstance(raw,(int,float)) and math.isfinite(raw) else None
        if val is not None:
            sheet.cell(line,11,val)
            filled+=1
        sheet.cell(line,12,row['unit'])
        sheet.cell(line,14,excel_review_status(row['assessment_status']))
        note=(row['qualitative_finding'] or '数値未測定')
        note += f" | 機械判定: {row['assessment_status']} (評価済は定量記述が存在する意味。方法・比較可能性の承認ではない)"
        if isinstance(raw,str) and (raw.startswith('{') or raw.startswith('[')):
            note += f' | 内訳: {raw}'
        sheet.cell(line,15,safe_spreadsheet_value(note))
        if row['effective_n'] is not None:sheet.cell(line,16,row['effective_n'])
        sheet.cell(line,19,row['evidence_level'])
        sheet.cell(line,20,safe_spreadsheet_value(row['source_reference']))
        sheet.cell(line,22,row['alternative_explanations'])
        sheet.cell(line,23,row['uncertainty'])
        sheet.cell(line,24,row['next_validation'])
        sheet.cell(line,25,row['candidate_action'])
        if isinstance(row['score_1_5'],int):sheet.cell(line,13,row['score_1_5'])
    return filled


def write_xlsx(mode,rows,outpath,dataset_id,trades):
    try:
        from openpyxl import load_workbook
    except ImportError:
        return False
    template=ROOT / 'templates' / f'evaluation_{"lite_76" if mode=="lite" else "full_379"}.xlsx'
    wb=load_workbook(template)
    # Single-file workbooks deliberately use A_評価, retaining original behavior.
    filled=fill_excel_sheet(wb['A_評価'],rows)
    meta=wb['データセット設定']
    meta['B6']=f'{dataset_id} / input round-trip trades'
    meta['B7']=min(r.entry_time for r in trades).date().isoformat()
    meta['B8']=max(r.exit_time for r in trades).date().isoformat()
    wb.calculation.fullCalcOnLoad=True
    wb.save(outpath)
    return filled


def write_comparison_xlsx(mode, all_rows, outpath):
    """Create one A-D reviewable workbook, not isolated A sheets for each group."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        return False
    template=ROOT / 'templates' / f'evaluation_{"lite_76" if mode=="lite" else "full_379"}.xlsx'
    wb=load_workbook(template)
    by_dataset=defaultdict(list)
    for r in all_rows:
        by_dataset[r['dataset_id']].append(r)
    for dataset_id, rows in by_dataset.items():
        fill_excel_sheet(wb[f'{dataset_id}_評価'], rows)
    # Comparison gate Q remains 未確認 until user validates comparable
    # instruments, fees, contract units, regimes and observation windows.
    wb.calculation.fullCalcOnLoad=True
    wb.save(outpath)
    return True

def main(argv=None):
    p=argparse.ArgumentParser(description='Evaluate CFD/FX completed trade history against 379/76 registry; no trade orders or diagnoses.')
    p.add_argument('--input',action='append',help='CSV/XLSX completed round-trips; repeated inputs merge into A')
    p.add_argument('--dataset',action='append',help='Data group e.g. A:trades.csv or B:trades2.csv; max A/B/C/D')
    p.add_argument('--mode',choices=('lite','full'),default='lite')
    p.add_argument('--out',required=True,help='Local output path (ignored by Git)')
    p.add_argument('--columns',help='JSON mapping of canonical column name to original CSV header')
    p.add_argument('--currency',help='Explicit default P&L currency if column absent')
    p.add_argument('--timezone',default='Asia/Tokyo',help='Interpret naive timestamps in this timezone')
    p.add_argument('--ratings',help='Optional expert scoring CSV with evidence references (process metrics only)')
    args=p.parse_args(argv)
    if not args.input and not args.dataset:
        p.error('One or more --input or --dataset arguments required')
    try:ZoneInfo(args.timezone)
    except Exception as e: p.error(f'Invalid timezone {args.timezone}: {e}')
    grouping=defaultdict(list)
    for name in args.input or []:grouping['A'].append(Path(name))
    for desc in args.dataset or []:
        if ':' not in desc:raise DataError('--dataset format must be A:path')
        id_,path=desc.split(':',1)
        if id_ not in ('A','B','C','D'):raise DataError('dataset IDs must be A/B/C/D')
        grouping[id_].append(Path(path))
    mapping=json.loads(Path(args.columns).read_text(encoding='utf-8')) if args.columns else None
    ratings=read_ratings(args.ratings)
    registry=json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    selection=json.loads(SELECTION_PATH.read_text(encoding='utf-8'))
    ideal=json.loads(IDEAL_PATH.read_text(encoding='utf-8'))
    lite_ids=set(selection['lite_metric_ids'])
    assert len(registry['metrics'])==379 and len(lite_ids)==76
    output_root=Path(args.out).resolve()
    output_root.mkdir(parents=True,exist_ok=True)
    all_dataset_rows=[]
    recorded=[]
    for id_,paths in sorted(grouping.items()):
        trades=[];warn=[];source_hashes={}
        for path in paths:
            ts,ws=read_trades(path,mapping,args.timezone,args.currency)
            source_hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
            trades.extend(ts);warn.extend(ws)
        if len({t.trade_id for t in trades})!=len(trades):
            raise DataError('Duplicate trade_id across files; deduplicate or remap and retry')
        if len({t.currency for t in trades})>1:
            raise DataError('Mixed currencies across files: convert before analyzing.')
        trades.sort(key=lambda t:(t.exit_time,t.entry_time,t.trade_id))
        rows=output_rows(id_,trades,registry,ideal,lite_ids,args.mode,ratings,[p.name for p in paths],source_hashes)
        folder=output_root/id_
        folder.mkdir(exist_ok=True)
        write_csv(folder/f'evaluation_{args.mode}.csv',rows,OUTPUT_FIELDS)
        write_csv(folder/f'gap_analysis_{args.mode}.csv',make_gap_rows(rows))
        suggestions=make_suggestions(trades,rows)
        write_csv(folder/'candidate_actions.csv',suggestions)
        write_report(folder/'analysis_report.md',id_,trades,rows,suggestions,warn,args.mode)
        write_behavior(folder/'behavior_analysis.md',id_,rows)
        write_xlsx(args.mode,rows,folder/f'evaluation_{args.mode}.xlsx',id_,trades)
        record={'dataset_id':id_,'paths':[x.name for x in paths],'n_trades':len(trades),'base_currency':trades[0].currency,
                'time_range_utc':[min(t.entry_time for t in trades).isoformat(),max(t.exit_time for t in trades).isoformat()],
                'assumed_naive_timezone':args.timezone,'metric_count':len(rows),'category_count':len({r['category_id'] for r in rows}),
                'count_numeric':sum(r['numeric_value'] is not None for r in rows),'status':'RESEARCH_ONLY',
                'data_asof_utc':max(t.exit_time for t in trades).isoformat(),
                'source_sha256':source_hashes,
                'reference_ideal':'QUANT-OMEGA; normative process benchmark, NOT observed returns',
                'risks':warn}
        recorded.append(record)
        all_dataset_rows.extend(rows)
    with (output_root/'provenance.json').open('w',encoding='utf-8') as f:
        json.dump({'schema':'evaluation-output-v1','datasets':recorded,'metric_source':'registry/metrics_full_379.json',
                   'ideal_source':'benchmark/quant-omega/ideal_model_full_379.json',
                   'public_repository_safe':False,
                   'notice':'Outputs may reveal private trade performance; never commit to public GitHub.'},f,ensure_ascii=False,indent=2)
    if len(recorded)>1:
        write_csv(output_root/f'cross_dataset_{args.mode}.csv',all_dataset_rows,OUTPUT_FIELDS)
        write_comparison_xlsx(args.mode, all_dataset_rows, output_root/f'comparison_{args.mode}.xlsx')
        (output_root/'COMPARISON_REVIEW.md').write_text(
            '# 横断比較の注意\n\n時期・銘柄・損益通貨・契約倍率・費用・市場状態の差を人が検証するまで数値差を改善と判定しません。'
            ' 指標IDで突合し、交絡因子を調整してください。\n',encoding='utf-8')
    for item in recorded:
        print(f"{item['dataset_id']}: {item['n_trades']} trades, {item['metric_count']} rows, {item['count_numeric']} numeric values, 29 categories")
    print(f'Files written under {output_root}')
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (DataError,ValueError) as e:
        print(f'ERROR: {e}',file=sys.stderr)
        sys.exit(2)
