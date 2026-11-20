#!/usr/bin/env python3
"""Regenerate entirely synthetic, public-safe example trades (not market data)."""
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parents[1] / 'examples' / 'synthetic_round_trips.csv'


def main():
    start = datetime(2026, 9, 1, 10, 0, tzinfo=ZoneInfo('Asia/Tokyo'))
    rows=[]
    for i in range(64):
        day = i // 2
        minute = i % 2 * 150
        en = start + timedelta(days=day, minutes=minute)
        is_win = i % 7 not in (0, 2, 5)
        qty = 2 if i>0 and (i-1)%7 in (0,2,5) and i%4==0 else 1
        side = 'LONG' if i%3 else 'SHORT'
        duration = (8+(i*3)%25) if is_win else (52+(i*7)%85)
        ex = en+timedelta(minutes=duration)
        # Synthetic P&L, not a backtest; contract point value explicitly 100 JPY.
        raw_points = (12 + i%8) if is_win else -(20+i%12)
        entry_price=48000+(day*7)+(i%9)*3
        exit_price=entry_price+(raw_points if side=='LONG' else -raw_points)
        fees=60*qty
        gross=raw_points*100*qty
        net=gross-fees
        rows.append({'trade_id':f'SYN-{i+1:03d}','instrument':'JP225_CFD_SYNTHETIC',
                     'side':side,'entry_time':en.isoformat(),'exit_time':ex.isoformat(),
                     'entry_price':entry_price,'exit_price':exit_price,'quantity':qty,
                     'gross_pnl':gross,'fees':fees,'net_pnl':net,'currency':'JPY'})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(f'Wrote {len(rows)} fully synthetic trades: {OUT}')


if __name__=='__main__':
    main()
