---
id: TRADE-BEHAVIOR-RESEARCH-2026-11-20
version: 1.0.0
as_of: 2026-11-20
language: ja-JP
artifact_type: research_protocol_for_ai
research_type: conceptual_methodology_not_empirical
research_status: RESEARCH_ONLY
has_real_trade_results: false
metrics: 379
categories: 29
registry_file: registry/metrics_full_379.json
---

# TRADE-BEHAVIOR-RESEARCH | AI用研究プロトコル

## 0. 読み込み契約（最優先）

**GOAL:** 売買履歴を使い、利益・損失・市場状態・意思決定行動を測定して、説明可能な仮説を生成し、期間外で反証検証する。人格、認知、神経、発達史に関する断定をしない。

**DOCUMENT CLASS:** 学術文献を踏まえた方法論と検証計画。個別売買の実測結果、統計的有意差、診断、将来収益を含まない。

**OPERATIONAL MODE:** RESEARCH_ONLY。データやエビデンス不十分時は NEEDS_DATA または NO_TRADE を返す。取引執行不可。

**ALWAYS SEPARATE:** `RAW_FACT / DERIVED_METRIC / ASSOCIATION / HYPOTHESIS / COUNTERFACTUAL / CORROBORATED / CANNOT_INFER / UNKNOWN`。

**NEVER:** 取引結果から脳機能、神経伝達物質、ADHD/自閉スペクトラム等、幼少期の家庭環境、貧困、トラウマ、性格診断を推測・断定しない。心理動機を確定せず、仮説には競合説明を付す。見えていない市場データやCSVを「確認済み」と書かない。ルール違反や資金超過を助長しない。

**IMPORTANT:** この文書内の研究仮説は検証前。先行研究の一般知見を個別のトレーダーにそのまま帰属させない。

## 1. モデルの概念定義

- `unit_fill`: broker execution one fill
- `unit_order`: original/modified/cancelled order
- `unit_trade`: reconstructed round-trip position episode; preserve partial close and scale-in/out
- `unit_decision`: independently motivated trading decision, not necessarily one fill
- `unit_day`: time-weighted equity observations and daily PnL; adjust deposits/withdrawals
- `decision_time_utc`: decision timestamp
- `feature_available_at_utc`: timestamp when each market feature was actually observable
- `as_of`: never use information later than decision_time_utc
- `net_pnl`: realized PnL converted to chosen base currency, less all relevant fees/funding
- `market_state`: regime defined without future information
- `behavior_signature`: P(action | condition, past outcome, market regime, strategy and constraints)
- `latent_trait`: hypothetical psychometric construct; cannot be identified uniquely from trades

**Causal sketch:** background/exposure (unobserved) → possibly traits/skills (latent); market regime+strategy+constraints+skills → decision; decision+execution+costs → outcome; outcome → later decisions. NEVER invert arrows without external evidence.

## 2. Data source codes

- `H`: 約定・ポジション履歴
- `P`: 価格・市場時系列（決定時点の利用可能性を保持）
- `O`: 注文・取消・修正・約定履歴
- `A`: 口座残高・含み損益・入出金・証拠金
- `J`: 事前戦略・取引日誌・本人の任意報告
- `X`: 外部指標・経済イベント・取引所仕様

## 3. 判定階層と真偽制約

| level | decision use | permitted language | not permitted |
|---|---|---|---|
| L0 | source-audited raw event | 「記録上は」 | 原因を断定 |
| L1 | reproducible formula | 「計算結果は」 | 未来の期待値と混同 |
| L2 | estimated association | 「この条件で差を観測」 | 因果・人格確定 |
| L3 | falsifiable hypothesis | 「仮説は…、代替説明は…」 | 診断・因果断定 |
| L4 | prospective/corroborated | 「限定条件で支持」 | 普遍化・永久優位 |
| NI | unavailable construct | 「履歴のみでは特定不可」 | 推論・類推による確定 |

Data sufficiency: `H` alone computes trade-time/PNL-related indicators only if open-close episodes are reconstructable. `P` required for price paths/MFE/MAE; `O` for original stop and order intent; `A` for MTM drawdown and capital-based risks; `J` for intention/traits as hypotheses; `X` for external conditioning. Some registry categories use a conservative superset of data sources; item-specific checks always override.

## 4. Canonical formulas and edge cases

```text
net_pnl_i = gross_pnl_i - commission_i - spread_cost_i - slippage_i - funding_i - other_fees_i
win_rate_ex_zero = n(net_pnl>0) / [n(net_pnl>0)+n(net_pnl<0)]
breakeven_rate = n(net_pnl=0) / n(all closed independent trades)
expectancy_net = sum_i(net_pnl_i) / n(all closed independent trades)
profit_factor = sum(max(net_pnl_i,0)) / abs(sum(min(net_pnl_i,0)))
mean_win_loss_ratio = mean(net_pnl_i | >0) / abs(mean(net_pnl_i | <0))
max_drawdown_mtm = max_t((max_{s<=t} equity_adjusted_s - equity_adjusted_t) / max_{s<=t} equity_adjusted_s)
r_multiple_i = net_pnl_i / initial_defined_risk_amount_i
```

- `profit_factor` denominator zero => undefined/+infinity according to explicit convention; DO NOT silently impute.
- Closed-trade win rate is not the same as mark-to-market hit rate; open trades are censored.
- `MFE/MAE`: side-adjusted intrahold extreme moves, with contract multiplier and scale-in/scale-out reconstruction. Require price resolution adequate to stop/target ordering; OHLC candles may be ambiguous.
- `MFE_capture_ratio`: define gross vs net numerator and denominator consistently; define for profitable trades with positive MFE and comparable exposures only.
- `R`: original risk must be available at decision time; not an ex-post stop estimate.
- `DD`: if only realized PnL available report `realized_only_DD`, never pretend MTM.
- `Kelly`: theoretical only, avoid direct sizing prescription from uncertain stationary estimates.
- `session`: convert UTC into exchange local zone, adjust DST, preserve Tokyo local display.
- `counterfactual`: simulation is hypothetical and must include spread, slippage, partial fills, borrow/funding, margin, trade interactions.

## 5. Required analysis workflow

1. `AUDIT`: verify hashes, provenance, duplicates, timezone, currency, product contract specifications, partial closes, position matching, open trades, price availability. Stop on critical inconsistencies.
2. `DEFINE`: universe, as-of information, evaluated strategy, split date, cost assumptions, account/risk caps and baseline; pre-register hypotheses.
3. `RECONSTRUCT`: fills→orders→positions→decisions; keep imputation and uncertainty logs.
4. `DESCRIBE`: metric dictionary D01-D22, each result with n, time window, fees, CIs if relevant; stratify symbol/side/session/hold time/regime.
5. `BEHAVIOR`: conditional actions (re-entry, lot escalation, stop moved), contrast pre-specified competing explanations, avoid personality labels as facts.
6. `INFERENCE`: hierarchical/clustered uncertainty, block bootstrap where serial dependence, multiple-testing controls.
7. `SIMULATE`: deterministic counterfactual rules and correct execution, baseline and no-trade alternative.
8. `VALIDATE`: chronological out-of-sample/walk-forward, no leakage; record number of searched variants and DSR/FDR as appropriate.
9. `DECIDE`: RESEARCH_ONLY / NEEDS_DATA / SUPPORTED_WITH_LIMITATIONS / REJECTED / NO_TRADE; preserve hard risk limits; no live trading actions.

## 6. Priority research hypotheses (not tested)

- `H01` **早すぎる利確**: 仮説=決済後価格の有利継続。検証=決済後同一時点比較・取引費用。反証=費用控除後に消滅、期間外再現なし。status=`PROPOSED`; evidence=`NONE`。
- `H02` **損切り遅延**: 仮説=事前ストップの不利変更。検証=注文履歴と尾部損失の比較。反証=変更が事前ルールで説明される。status=`PROPOSED`; evidence=`NONE`。
- `H03` **参入直後の逆行**: 仮説=MAEが参入判断の失敗を示す可能性。検証=同じ相場での比較・方向調整価格経路。反証=ノイズ幅内で期待値差なし。status=`PROPOSED`; evidence=`NONE`。
- `H04` **連敗後のリスク拡大**: 仮説=リスク額や注文頻度が連敗に条件付く。検証=市場・信号強度・戦略制御。反証=通常の戦略サイズ調整で説明。status=`PROPOSED`; evidence=`NONE`。
- `H05` **曜日・時間帯の損益差**: 仮説=特定条件に損失集中。検証=銘柄/レジーム交絡補正と多重検定。反証=補正後/期間外に消失。status=`PROPOSED`; evidence=`NONE`。
- `H06` **相場レジーム適合**: 仮説=トレンド/レンジで期待値が違う。検証=決定時点に利用可能なレジーム分類。反証=事後分類でしか優位性がない。status=`PROPOSED`; evidence=`NONE`。
- `H07` **ロット変動の害**: 仮説=一部のリスク拡大が尾部損失を増す。検証=標準化サイズとのコスト込み比較。反証=余力/複利を考慮すると差なし。status=`PROPOSED`; evidence=`NONE`。
- `H08` **長時間保有の損失**: 仮説=保有開始時点からタイムストップが有効。検証=検閲考慮・価格経路で比較。反証=勝敗後分類による見かけの差。status=`PROPOSED`; evidence=`NONE`。
- `H09` **手法変更の効果**: 仮説=2026-11-06で取引特性が変化。検証=同じ指標・調整後比較。反証=市場構成/標本不足で差が説明。status=`PROPOSED`; evidence=`NONE`。
- `H10` **状況依存の行動署名**: 仮説=特定状況で再参入等が反復。検証=期間間安定性と競合説明。反証=戦略変更で行動署名が消える。status=`PROPOSED`; evidence=`NONE`。
- `H11` **心理尺度の増分妥当性**: 仮説=心理尺度が行動のみモデルを改善する。検証=同意取得・外部尺度・期間外比較。反証=増分予測力なし。status=`PROPOSED`; evidence=`NONE`。
- `H12` **形式知化された停止規律**: 仮説=定義済みストップ/休止が尾部損失を縮める。検証=介入別に費用込み比較。反証=期待値を損ねる/期間外不再現。status=`PROPOSED`; evidence=`NONE`。

## 7. Outcome contract (one research question per record)

```json
{
  "task_type": "knowledge_review|experiment|audit|strategy_spec",
  "as_of": "YYYY-MM-DDTHH:MM:SSZ or null",
  "universe": [],
  "data_quality": {"status":"PASS|WARN|FAIL", "issues":[]},
  "known_facts": [{"claim":"...", "provenance":"...", "evidence_level":"L0|L1"}],
  "metric_results": [{"metric_id":"D##-###", "sample_size":null, "estimate":null, "ci":null, "unit":null, "cost_model":"..."}],
  "hypotheses": [{"id":"H##", "mechanism":"...", "alternatives":[], "falsification":"...", "status":"PROPOSED|TESTING|REJECTED|SUPPORTED_WITH_LIMITATIONS"}],
  "limits": {"insufficient_data":[], "cannot_infer":[], "leakage_checks":[], "multiple_testing":null},
  "validation": {"chronological_split":null, "baseline":null, "walk_forward":null, "out_of_sample":null},
  "decision": "RESEARCH_ONLY|NEEDS_DATA|REJECTED|SUPPORTED_WITH_LIMITATIONS|NO_TRADE",
  "remaining_unknowns": []
}
```

- Ban outputs claiming diagnosed personality, childhood conditions, brain activity, personal mental disorders, criminality, IQ, moral character, or individual identity.
- When metric not computable set `estimate:null`, `reason:missing_data`; do not fill with zero.
- An improvement hypothesis is not approved without a baseline, cost model, leakage controls and OOS performance.

## 8. Instrument and method-change scope (conversation-derived task parameters; not measured)

- `method_change_cutoff`: 2026-11-06, compare pre/post if same-account full records and enough observations are supplied.
- `future_exclusions`: 米国株、VIX、天然ガス（future research universe only）。Historical trade inclusion should remain unchanged when evaluating past performance.
- `market_selection`: DO NOT assume any specific instrument, timeframe, broker, leverage, or initial capital unless supplied in the current dataset/protocol.
- `hard_risk_policy`: Take current user's explicit policy from a provided source; NEVER substitute another project's tournament settings.

## 9. Research registry: 29 groups, 379 stable metrics

Each record: `ID | name | research question`. Academic disciplines, conservative required sources and inference type are at category header; full machine records in `registry/metrics_full_379.json`.

### D01 / データ品質・取引構造 / type=observed / sources=H,O / academic=データ工学・金融会計
- `D01-001` 約定件数と取引件数 — 分割約定と完結取引を混同していないか
- `D01-002` ポジション再構成 — 新規建てから最終決済への対応を復元できるか
- `D01-003` FIFO・平均法による対応差 — 建玉対応方式により計算結果が変わるか
- `D01-004` 分割エントリー — 複数回に分けて建てる頻度
- `D01-005` 分割決済 — 一部利確・一部損切りの頻度
- `D01-006` ドテン取引 — 決済直後に反対方向の建玉を持つ割合
- `D01-007` 未決済・部分決済建玉 — 含み損益と実現損益を区別できるか
- `D01-008` 損益計算の照合 — 契約倍率・為替・手数料を反映した整合性
- `D01-009` 欠損・重複・異常値 — 時刻・価格・数量の不正データ検出
- `D01-010` 時刻の整合性 — UTC・JST・DST・取引所時刻の整合性
- `D01-011` 銘柄コードの名寄せ — 同一原資産・商品を一貫して集計できるか

### D02 / 基本成績・期待値 / type=observed / sources=H / academic=確率論・金融統計
- `D02-001` 総損益・純損益 — 期間の実現損益と費用控除後損益
- `D02-002` 総利益・総損失 — 勝ち取引と負け取引の金額の合計
- `D02-003` 勝率・敗率・建値率 — 勝敗とゼロ損益の構成
- `D02-004` 平均勝ち・平均負け — 典型的な利益額と損失額
- `D02-005` ペイオフレシオ — 平均勝ちに対する平均負けの大きさ
- `D02-006` プロフィットファクター — 総利益と総損失の比
- `D02-007` 期待損益 — 一取引当たりの費用控除後平均損益
- `D02-008` 損益分岐勝率 — 平均損益幅の下で必要な勝率
- `D02-009` 損益中央値 — 少数の外れ値に左右されない典型値
- `D02-010` 利益貢献率 — 特定取引が総利益をどれほど支えるか
- `D02-011` 期間別損益 — 日・週・月の収益変遷
- `D02-012` 累積損益曲線 — 成績改善・悪化の時間的経路
- `D02-013` 資金効率 — 使用資金・拘束時間に対する収益
- `D02-014` 経費比率 — 費用の損益に占める割合

### D03 / 損益分布・極端値 / type=observed / sources=H / academic=数理統計・極値理論
- `D03-001` 標準偏差・分散 — 取引単位の損益のばらつき
- `D03-002` 歪度 — 大勝ち型か大負け型かという分布の非対称性
- `D03-003` 尖度 — 裾の厚さと極端な値への感応
- `D03-004` 損益分位点 — 下位1・5・10％などの損失水準
- `D03-005` 最大利益・最大損失 — 観測された極端値
- `D03-006` 外れ値除去後PF — 少数の極端値への依存度
- `D03-007` トップ10取引寄与 — 上位の取引が総利益を支える程度
- `D03-008` 損失集中度 — 少数の大損失が全体を支配するか
- `D03-009` 多峰性 — 異なる戦略・相場の混在兆候
- `D03-010` 厚い裾の推定 — 正規分布では説明しにくい損益
- `D03-011` 利益と損失の非対称性 — 小勝ち大負けの構造

### D04 / リスク・ドローダウン / type=observed / sources=H,A / academic=リスク計量・保険数理
- `D04-001` 最大ドローダウン — 時価評価資産のピークからの最大落ち込み
- `D04-002` 平均ドローダウン — 日常的な資産減少幅
- `D04-003` 回復期間 — 過去最高資産への復帰に要する時間
- `D04-004` 水面下期間割合 — 過去最高資産を下回る時間割合
- `D04-005` Ulcer Index — 資産減少の深さ・長さ
- `D04-006` Sharpe Ratio — 超過リターンに対する総リスク
- `D04-007` Sortino Ratio — 下方変動に対する収益効率
- `D04-008` Calmar Ratio — 最大DDに対する年率リターン
- `D04-009` VaR — 所定期間の損失分位点
- `D04-010` Expected Shortfall — 悪い尾部での条件付き平均損失
- `D04-011` 破産確率のシナリオ推定 — 資金枯渇の条件付きリスク
- `D04-012` 日次損失集中度 — 特定日への損失偏在
- `D04-013` 連続DDエピソード — 複数の大きな資産減少の発生
- `D04-014` 含み損益由来DD — 実現損益だけでは見えない資産変動

### D05 / ロット・資金管理 / type=observed / sources=H,O,A / academic=最適制御・ポートフォリオ理論
- `D05-001` 平均ロット・変動係数 — 建玉規模の一貫性
- `D05-002` 勝敗別ロット差 — 勝つ時と負ける時の建玉規模の違い
- `D05-003` リスク資産比率 — 予定損失額の口座資産に対する比
- `D05-004` 実効レバレッジ — 資産に対する総ポジション倍率
- `D05-005` 初期ストップ距離 — 参入時の損失限定幅
- `D05-006` R-Multiple — 初期想定損失に対する実現損益
- `D05-007` Kelly比率の参考値 — 仮定した分布下の理論的成長率最大化比率
- `D05-008` ロット増額後の成績 — 増額行動と結果の関係
- `D05-009` ナンピン頻度・影響 — 逆行中の追加建ての影響
- `D05-010` ピラミッディング影響 — 順行中の追加建ての影響
- `D05-011` 余力フロア違反 — 最低証拠金余力を守ったか
- `D05-012` 損失上限違反 — 日次・取引別の損失制約の順守

### D06 / 銘柄・商品別適性 / type=observed / sources=H,P / academic=資産価格理論・比較統計
- `D06-001` 銘柄別純損益 — 銘柄ごとの利益と損失
- `D06-002` 銘柄別勝率 — 銘柄による勝敗の違い
- `D06-003` 銘柄別期待値 — 取引当たりの収益効率
- `D06-004` 銘柄別PF — 利益と損失の釣り合い
- `D06-005` 銘柄別取引頻度 — 特定銘柄への偏り
- `D06-006` 銘柄別保有時間 — 商品特性と保有時間の関係
- `D06-007` 銘柄別方向適性 — 買い・売り方向ごとの成績
- `D06-008` 銘柄別ボラティリティ適性 — 変動率による成績差
- `D06-009` 銘柄別手数料・資金調達費 — 商品条件による利益減少
- `D06-010` 銘柄別大損失寄与度 — 全体のテール損失への寄与
- `D06-011` 資産クラス別比較 — 指数・FX・貴金属などの比較

### D07 / ロング・ショート適性 / type=observed / sources=H,P / academic=方向性戦略・条件付き統計
- `D07-001` ロング勝率 — 買い方向で勝つ確率
- `D07-002` ショート勝率 — 売り方向で勝つ確率
- `D07-003` 方向別期待値差 — 買いと売りの期待損益の差
- `D07-004` 方向別平均損失 — 一方向で損失が肥大化するか
- `D07-005` 方向別保有時間 — 買い・売りで決済行動が異なるか
- `D07-006` 方向別トレンド適合 — 市場方向への追随の成績
- `D07-007` 逆張り・順張り比率 — トレンドに逆行・追随する頻度
- `D07-008` 方向反転後の成績 — ドテン判断が有効か

### D08 / エントリーの質 / type=observed / sources=H,P,O / academic=イベントスタディ・時系列予測
- `D08-001` エントリー直後リターン — 5・15・60分後の方向調整後損益
- `D08-002` 直後逆行率 — 参入直後に不利な方向へ進む割合
- `D08-003` 当日レンジ内の位置 — 高値・安値のどの位置で入るか
- `D08-004` 直前トレンド一致度 — 価格傾向に順行しているか
- `D08-005` ブレイクアウト参入成功率 — 価格突破直後の成績
- `D08-006` 押し目・戻り目参入成功率 — 調整後のエントリー効果
- `D08-007` 指標シグナル一致度 — MA・RSI等の既知情報との整合
- `D08-008` 複数時間足一致度 — 上位足と下位足の方向一致
- `D08-009` エントリー遅延影響 — 時刻変更による反実仮想損益
- `D08-010` 参入後最大逆行 — 保有期間中のMAE
- `D08-011` 参入後最大順行 — 保有期間中のMFE
- `D08-012` 失敗パターンの再現性 — 負けエントリーの共通条件
- `D08-013` 参入理由の再現性 — 記録した判断理由と実際のシグナルの一致

### D09 / 決済・利確・損切り / type=observed / sources=H,P,O / academic=最適停止・動的意思決定
- `D09-001` 利確タイミング — 含み益に対する決済時点
- `D09-002` 損切りタイミング — 含み損に対する決済時点
- `D09-003` MFE — 保有中の最大有利価格変化
- `D09-004` MAE — 保有中の最大不利価格変化
- `D09-005` MFE捕捉率 — 最大含み益のうち実現した割合
- `D09-006` 利益吐き出し率 — 最大含み益から決済までの減少
- `D09-007` 初期ストップ逸脱 — 事前設定した損切り幅への違反
- `D09-008` 早すぎる利確仮説 — 決済後の有利な値動きが継続するか
- `D09-009` 決済後の逆行・反転 — 決済以後の価格経路
- `D09-010` 建値撤退の効果 — 建値ストップの費用込みでの損益
- `D09-011` 固定利確の効果 — 一定目標値での決済シミュレーション
- `D09-012` トレーリングストップ効果 — 追随型ストップの損益とリスク
- `D09-013` 分割利確効果 — 一括決済との比較
- `D09-014` 手動介入の寄与 — 当初注文と変更後結果の差
- `D09-015` 損失限定と利益伸長の両立 — 利確・損切りの非対称性

### D10 / 保有時間・時間効率 / type=observed / sources=H,P / academic=生存時間解析・First-passage理論
- `D10-001` 平均・中央値保有時間 — 取引の典型的な継続時間
- `D10-002` 勝ち取引保有時間 — 勝つ取引の時間分布
- `D10-003` 負け取引保有時間 — 負ける取引の時間分布
- `D10-004` 保有時間別勝率 — 時間帯別ではなく長さ別の勝率
- `D10-005` 保有時間別期待値 — 長時間保有の損益効率
- `D10-006` 時間当たり利益 — 資金拘束時間当たりの成果
- `D10-007` 利益到達時間 — 目標利益到達までの時間
- `D10-008` 損切り到達時間 — 設定ストップ到達までの時間
- `D10-009` 利益経路のハザード — 利益到達・決済が発生する時間依存
- `D10-010` タイムストップ仮説 — 時間制限決済の効果
- `D10-011` 保有時間二極化 — 短期決済と長期塩漬けの混在
- `D10-012` 未決済の検閲処理 — 保有中の建玉を無理に確定させない

### D11 / 時間帯・曜日・カレンダー / type=observed / sources=H,X / academic=季節性・市場マイクロストラクチャー
- `D11-001` 時間帯別勝率 — 時刻帯ごとの勝敗差
- `D11-002` 時間帯別期待値 — 時刻帯ごとの平均損益
- `D11-003` 曜日別勝率 — 曜日に依存する勝敗差
- `D11-004` 曜日別PF — 曜日での利益損失効率
- `D11-005` 月別・四半期別成績 — 季節性の探索
- `D11-006` 週初・週末効果 — 月曜・金曜の成績差
- `D11-007` 市場セッション別成績 — 東京・ロンドン・NY時間の比較
- `D11-008` オープン直後の成績 — 寄り付き直後のリスク
- `D11-009` クローズ直前の成績 — 引け前のリスク
- `D11-010` 指標発表前後の成績 — イベント時の成績
- `D11-011` 日内取引順序 — その日の何回目の取引か
- `D11-012` 日跨ぎ・週跨ぎ保有 — オーバーナイト・ギャップ影響
- `D11-013` DST補正の効果 — 時差変更でカテゴリがずれないか

### D12 / テクニカル・価格パターン / type=observed / sources=H,P / academic=シグナル処理・統計的パターン認識
- `D12-001` 移動平均線位置 — 価格とMAの上下関係
- `D12-002` 移動平均線傾き — トレンドの局所的傾向
- `D12-003` 移動平均クロス — クロス後の期待値
- `D12-004` RSI状態 — 買われ過ぎ・売られ過ぎ指標との関係
- `D12-005` MACD状態 — モメンタム指標との関係
- `D12-006` ATR状態 — 値幅に対するストップや目標の相対位置
- `D12-007` ボリンジャーバンド位置 — 相対的価格水準との関係
- `D12-008` VWAP乖離 — 出来高加重平均価格との距離
- `D12-009` ローソク足形状 — 実体・ヒゲなどの形状分類
- `D12-010` サポート・レジスタンス — 節目への距離
- `D12-011` 一目均衡表との関係 — 雲・基準線等との位置
- `D12-012` 価格収縮からの拡大 — レンジ突破の環境
- `D12-013` 直近高安への距離 — 突破や反転の可能性

### D13 / 相場レジーム・環境 / type=observed / sources=H,P,X / academic=非定常時系列・レジームスイッチング
- `D13-001` トレンド相場での成績 — 方向性のある局面での優位性
- `D13-002` レンジ相場での成績 — 方向性が乏しい局面での優位性
- `D13-003` 高変動相場での成績 — 高ATR・高実現分散での損益
- `D13-004` 低変動相場での成績 — 低ボラ時の損益
- `D13-005` 転換点付近の成績 — 相場構造変化直後の取引
- `D13-006` トレンド強度別成績 — ADXなどによる強度分類
- `D13-007` 急騰急落時の成績 — ジャンプ事象前後の成績
- `D13-008` ボラティリティ急拡大 — 局所的変動率ショック
- `D13-009` 価格ギャップの影響 — 連続価格経路を仮定できない損失
- `D13-010` 流動性低下時の成績 — スプレッド・板厚の変化
- `D13-011` レジーム遷移の影響 — 市場状態間移行での戦略脆弱性
- `D13-012` NO_TRADE条件 — どの環境なら売買を見送るべきか

### D14 / 約定品質・コスト / type=observed / sources=H,O,P / academic=市場マイクロストラクチャー・最適執行
- `D14-001` スプレッド負担 — 買値と売値の差による損益劣化
- `D14-002` 取引手数料率 — 取引規模に対する明示費用
- `D14-003` スリッページ — 発注基準値と約定値の差
- `D14-004` 発注から約定までの遅延 — 執行待ちによる価格変化
- `D14-005` 成行・指値・逆指値別効果 — 注文方法ごとの費用と約定差
- `D14-006` 約定率 — 注文が約定に至る割合
- `D14-007` 部分約定率 — 注文の一部のみ約定する割合
- `D14-008` 注文取消・変更頻度 — 発注後に方針を変える頻度
- `D14-009` Implementation Shortfall — 判断基準価格と執行価格・未約定の差
- `D14-010` 約定後の逆行（Adverse Selection） — 執行直後の不利な価格変動
- `D14-011` Market Impact — 注文規模が市場価格に与えた影響
- `D14-012` 資金調達費・金利調整 — 保有に伴う費用
- `D14-013` 費用控除前後の期待値 — コストで優位性が消えるか

### D15 / 複数ポジション・資産配分 / type=observed / sources=H,P,A / academic=ポートフォリオ理論・相関・テール依存
- `D15-001` 同時保有ポジション数 — 複数の建玉を抱える頻度
- `D15-002` 総エクスポージャー — 絶対ポジション量の合計
- `D15-003` ネットエクスポージャー — 方向相殺後のリスク
- `D15-004` 銘柄間相関 — 資産同士の同時値動き
- `D15-005` 相関ポジション重複 — 見かけの分散と実質集中
- `D15-006` 限界リスク寄与 — 新しい建玉が追加するリスク
- `D15-007` ヘッジ効果 — 逆方向ポジションの損失緩和
- `D15-008` 共通ファクター露出 — 金利・株価・為替等への依存
- `D15-009` 同時大損失頻度 — テールイベントでの共同損失
- `D15-010` ポートフォリオPF・DD — 総合成績と単体成績の違い
- `D15-011` 資産配分の偏り — 特定市場にリスクが集中するか

### D16 / 連勝・連敗・売買連鎖 / type=observed / sources=H / academic=マルコフモデル・点過程
- `D16-001` 最大連勝・連敗 — 続いた勝敗系列の極値
- `D16-002` 平均連勝・連敗長 — 勝敗がまとまる程度
- `D16-003` 勝利後の次回勝率 — 勝利条件付きの次の勝敗
- `D16-004` 敗北後の次回勝率 — 損失条件付きの次の勝敗
- `D16-005` 勝敗の自己相関 — 独立性に対する系列依存
- `D16-006` 連敗後ロット変化 — 損失系列とリスク選択の連動
- `D16-007` 連勝後ロット変化 — 成功系列とリスク選択の連動
- `D16-008` 損失後の再エントリー時間 — 負けから次の発注までの間隔
- `D16-009` 取引間隔別期待値 — 短い間隔での成績悪化の有無
- `D16-010` 休止ルールの効果 — 連敗後の停止を仮想的に導入
- `D16-011` 売買頻度の自己励起 — 売買後ほど次の売買が増えるか
- `D16-012` 取引密度の急増 — 短時間の取引集中エピソード

### D17 / 認知バイアスの行動指標 / type=hypothesis / sources=H,P,O,J / academic=行動経済学・認知心理学
- `D17-001` 損失回避仮説 — 等価な利益・損失に対し反応が非対称か
- `D17-002` ディスポジション効果 — 含み益を確定し含み損を抱えやすいか
- `D17-003` アンカリング仮説 — 建値・高安など基準値への固着
- `D17-004` サンクコスト仮説 — 既投入資金が継続判断に影響するか
- `D17-005` 確証バイアス仮説 — 予想に反する情報を無視していないか
- `D17-006` 過信仮説 — 成功後に適切な根拠なくリスクを拡大するか
- `D17-007` リベンジトレード仮説 — 損失回復目的で短時間に追加売買
- `D17-008` FOMO仮説 — 急変動後の追随が計画外に増えるか
- `D17-009` ギャンブラーの誤謬仮説 — 連敗で次は勝つと判断するか
- `D17-010` ホットハンド信念仮説 — 連勝で主観的成功確率を上げるか
- `D17-011` 直近性バイアス仮説 — 直近の損益を過大視するか
- `D17-012` メンタルアカウンティング — 利益の出所でリスク選択を変えるか
- `D17-013` ブレークイーブン効果 — 損失を回復するまでリスク選択が変わるか
- `D17-014` 認知疲労仮説 — 判断の累積でルール逸脱が増えるか
- `D17-015` 計画逸脱 — 当初ルールと異なる行為の頻度
- `D17-016` 後知恵バイアス — 事後説明と事前予測に齟齬があるか
- `D17-017` 過剰取引仮説 — 頻度増加が純期待値を下げるか

### D18 / 外部ニュース・マクロ要因 / type=observed / sources=H,P,X / academic=マクロ計量経済・イベントスタディ
- `D18-001` 主要経済指標前後の取引 — 発表時刻と取引の距離
- `D18-002` 金融政策イベントでの成績 — 会合・会見等の影響
- `D18-003` 指標サプライズとの関係 — 事前予想と実績の差の影響
- `D18-004` 突発ニュース後の取引 — 速報への反応と取引結果
- `D18-005` 市場センチメント別成績 — リスク選好局面での損益
- `D18-006` 金利・為替連動 — 他市場の変化による結果
- `D18-007` 国際市場の連動 — 東京・ロンドン・NYの順行/逆行
- `D18-008` 先物・現物価格差 — 市場間情報伝播
- `D18-009` 休日・非取引時間 — ギャップの影響

### D19 / 手法変更・学習効果 / type=hypothesis / sources=H,P,J / academic=因果推論・構造変化
- `D19-001` 手法変更前後の勝率差 — 勝率のレベル変化
- `D19-002` 手法変更前後の期待値差 — 費用込み平均損益の変化
- `D19-003` 手法変更前後のPF差 — 損益効率の変化
- `D19-004` 損失尾部の変化 — 大損失率が変化したか
- `D19-005` 保有時間の変化 — 売買スタイルが変わったか
- `D19-006` 時間帯・銘柄構成の変化 — 構成変化で見かけの改善が起きていないか
- `D19-007` 取引量変化 — ロット違いを標準化した成績
- `D19-008` 学習曲線 — 経験とともに改善したか
- `D19-009` 構造変化点の検出 — 変化した時点がいつか
- `D19-010` ローリング期待値 — 成績の安定性
- `D19-011` 非定常性 — 過去の優位性が持続するか
- `D19-012` 変更の純効果 — 交絡調整後にも成績改善が残るか

### D20 / 反実仮想・決済シミュレーション / type=counterfactual / sources=H,P,O / academic=因果推論・動的計画
- `D20-001` 参入5分遅延 — 参入を待った場合の費用込み損益
- `D20-002` 参入5分前倒し — 早期参入した場合の損益
- `D20-003` 決済5分前倒し — 早期撤退した場合の損益
- `D20-004` 決済15分延長 — 保持を続けた場合の損益
- `D20-005` 固定利確導入 — 事前目標で機械決済した場合
- `D20-006` 固定損切り導入 — 事前ストップで損失限定した場合
- `D20-007` ATRストップ導入 — ボラティリティ適応型ストップ
- `D20-008` トレーリング導入 — 利益を追跡するストップ
- `D20-009` 時間決済導入 — 所定時間で退出した場合
- `D20-010` 連敗後休止 — 連敗状態で見送った場合
- `D20-011` 特定時間帯の除外 — 苦手時間を省いた場合
- `D20-012` 特定銘柄の除外 — 苦手商品を省いた場合
- `D20-013` 勝ち建玉の延長 — 利益拡大候補のみ継続
- `D20-014` ナンピン禁止 — 追加建てを禁止した場合
- `D20-015` ロット固定化 — 方向判断とサイズ判断を分離
- `D20-016` 非取引選択 — NO_TRADEを選んだ場合の代替成果

### D21 / 統計的信頼性・再現性 / type=inference / sources=H,P,A / academic=推測統計・機械学習
- `D21-001` 勝率の信頼区間 — 標本誤差の幅
- `D21-002` 期待値の信頼区間 — 平均損益の推定不確実性
- `D21-003` 期待値ゼロ仮説検定 — 観測利得が偶然の範囲か
- `D21-004` ブートストラップ — 再標本化による頑健性
- `D21-005` ブロックブートストラップ — 系列依存を考慮した再標本化
- `D21-006` ベイズ事後分布 — 成功確率などの不確実性
- `D21-007` 実効サンプルサイズ — 重複・依存を考慮した検出力
- `D21-008` 多重比較補正 — 多数の条件探索による偽発見抑制
- `D21-009` 交互作用効果 — 銘柄×時間帯などの組み合わせ
- `D21-010` 交絡因子調整 — 見かけの関連を分離
- `D21-011` ロジスティック回帰 — 勝敗確率の条件付き関連
- `D21-012` 分位点回帰 — 典型値ではなく尾部の説明
- `D21-013` クラスタリング — 類似した取引タイプの識別
- `D21-014` 特徴量重要度 — 予測で寄与する特徴の探索
- `D21-015` 期間外検証 — ルール選択に使わない未来期間で評価
- `D21-016` Walk-forward — 時間順の繰り返し評価
- `D21-017` リーケージ監査 — 判断時に利用不能な情報の排除
- `D21-018` Deflated Sharpe Ratio — 多重試行・非正規性による評価の調整
- `D21-019` パラメータ感度 — 閾値変更に対する脆弱性
- `D21-020` モンテカルロ — 仮定した損益過程の結果分布

### D22 / 規律・業務上のリスク / type=observed / sources=H,O,A,J / academic=ヒューマンファクター・リスク統制
- `D22-001` ルール遵守率 — 事前手法に沿う売買の割合
- `D22-002` ストップ変更率 — 損切り指値を不利な方向へずらす頻度
- `D22-003` サイズ制限違反 — 許容ロットを超える頻度
- `D22-004` 証拠金余力違反 — 余力フロアの逸脱
- `D22-005` 強制決済発生率 — 余力不足などの強制ロスカット
- `D22-006` 誤発注率 — 方向・数量・価格の入力ミス
- `D22-007` システム障害損失 — 通信・約定障害に関連する損失
- `D22-008` 計画外売買の成績 — 想定外の判断の期待値
- `D22-009` 停止ルール遵守 — 日次・連敗停止の実効性
- `D22-010` 予防可能損失 — 決定済みルール遵守なら回避した損失

### P01 / パーソナリティ関連仮説 / type=hypothesis / sources=H,P,J / academic=特性心理学・行動経済学
- `P01-001` 状況限定のリスク選好 — 市場内で大きなリスクを選びやすいか
- `P01-002` 慎重さ — 参入前の確認条件を厳格にするか
- `P01-003` 衝動性 — 計画外の即時参入が多いか
- `P01-004` 自己規律 — 繰り返しルールを守るか
- `P01-005` 忍耐的な保有 — 戦略条件を満たすまで保有できるか
- `P01-006` 判断の一貫性 — 同じ状況で同じ行動か
- `P01-007` 柔軟性 — 市場環境の変化に適応するか
- `P01-008` 完璧主義傾向 — 過度な確認が結果を損なうか
- `P01-009` 達成志向 — 目標設定と行動の一貫性
- `P01-010` 刺激追求仮説 — 高変動局面を嗜好するか
- `P01-011` 曖昧さ耐性 — 不明瞭な相場で判断がどう変化するか
- `P01-012` 自己効力感 — 成功後の見積もり精度の変化
- `P01-013` 過信傾向 — 主観的確率と実際の的中の不一致
- `P01-014` 感情的反応性 — 大損益後の行動変化
- `P01-015` Big Five誠実性 — 取引規律との関連仮説※尺度が必要
- `P01-016` Big Five開放性 — 新戦略探索との関連仮説※尺度が必要
- `P01-017` Big Five外向性・協調性 — 取引単独では測定根拠に乏しい

### P02 / 思考・認知スタイル / type=hypothesis / sources=H,P,O,J / academic=認知科学・意思決定心理学
- `P02-001` 直感型・熟慮型 — 即応と分析プロセスをどう使い分けるか
- `P02-002` トップダウン型 — 上位市場状況を先に確認するか
- `P02-003` ボトムアップ型 — 直近価格の変化から判断するか
- `P02-004` パターン認識型 — 類似価格形状に反応するか
- `P02-005` 確率思考型 — 期待値と損失分布を意思決定に使うか
- `P02-006` 二分法的判断 — 方向判断が過度に固定化するか
- `P02-007` 仮説検証型 — 小規模に試し統計的評価を行うか
- `P02-008` 探索型 — 商品や時間帯の実験が多いか
- `P02-009` 最適化志向 — 失敗後にルールを系統的に改めるか
- `P02-010` 反応型 — ニュースや値動きへの即応が多いか
- `P02-011` 予測先行型 — 値動き確認前にポジションを持つか
- `P02-012` 確認重視型 — 複数指標の成立まで待つか
- `P02-013` 損失最小化志向 — リターンより損失制御を優先するか
- `P02-014` 機会最大化志向 — シグナル機会の最大化を優先するか
- `P02-015` 状況適応型 — 相場に応じて手法を変更するか
- `P02-016` 固定ルール型 — 再現可能なトリガーを重視するか

### P03 / 習慣・反復行動 / type=observed / sources=H,O,J / academic=習慣形成・行動学習
- `P03-001` 定時売買習慣 — 同じ時刻に取引するか
- `P03-002` 反射的な参入 — 急変動直後の短時間反応
- `P03-003` 決済直後再参入 — 決済と次の注文の時間差
- `P03-004` ナンピン習慣 — 逆行中に追加建てする反復
- `P03-005` ロット増額習慣 — 勝敗系列でサイズが変化
- `P03-006` 早期利確習慣 — 小さな含み益を確定する反復
- `P03-007` 損切り延期習慣 — ストップを繰り返し変更
- `P03-008` 見送り困難仮説 — 条件不足での取引頻度
- `P03-009` 確認の反復 — 発注後の変更・取消頻度
- `P03-010` 同方向の惰性 — 同じ方向の連続売買
- `P03-011` 判断の一貫性 — 類似条件での反応パターン
- `P03-012` 改善後の維持率 — 修正行動が継続するか
- `P03-013` 利益目標後の継続 — 日次目標達成後に取引するか
- `P03-014` 計画外行動率 — 事前ルールからの逸脱

### P04 / 情動・ストレス反応の仮説 / type=hypothesis / sources=H,O,J / academic=感情調整・ストレス心理学
- `P04-001` 損失後の反応変化 — 損失後のサイズ・頻度変化
- `P04-002` 利益後の反応変化 — 大勝ち後のリスク選択
- `P04-003` 大損益局面のルール遵守 — 圧力下で行動が変わるか
- `P04-004` 不確実性への反応 — レンジ・乱高下で行動が変化
- `P04-005` 小さな逆行への反応 — 微損での撤退頻度
- `P04-006` 利益期待による延長 — 利確条件に達しても保有するか
- `P04-007` 取引行動の回復時間 — 大きな損失後に通常の行動に戻る時間
- `P04-008` 判断の硬直 — 市場が反転しても方針を変更できないか
- `P04-009` 安全確保行動 — 過度な建値撤退や即時利確
- `P04-010` 連続判断後の品質変化 — 長時間取引後に逸脱が増えるか

### P05 / 得意分野・技能の仮説 / type=hypothesis / sources=H,P,O,J / academic=熟達研究・学習科学
- `P05-001` トレンド認識の技能 — トレンド開始・継続時の方向精度
- `P05-002` 反転認識の技能 — 転換点付近の方向判断
- `P05-003` 参入タイミング技能 — 参入後の逆行と順行
- `P05-004` リスク管理技能 — 初期損失限定・余力維持
- `P05-005` 利益伸長技能 — 高MFE捕捉率を維持するか
- `P05-006` 損失限定技能 — 大損失の尾部を制御するか
- `P05-007` 相場適応技能 — 市場状態変化への対応
- `P05-008` 統計的思考技能 — 期待値と検証記録の利用
- `P05-009` パターン学習技能 — 類似の失敗が減るか
- `P05-010` ミス修正技能 — 違反行動の反復が減るか
- `P05-011` 選択的注意技能 — 重要シグナルの取り逃し
- `P05-012` 反応速度 — 条件成立から発注までの所要時間
- `P05-013` 戦略遂行技能 — 意図したルールの実装精度
- `P05-014` 非対称損益の活用 — 小損大利を実現するか
- `P05-015` 自己改善技能 — 検証・修正後の改善維持
- `P05-016` 複合情報統合 — 複数条件を一貫して判断するか

### P06 / 神経科学的研究との接点 / type=not_identifiable / sources=H,O,J / academic=神経経済学・計算論的神経科学
- `P06-001` 報酬処理 — 利益後の行動と報酬学習モデルの対応
- `P06-002` 損失・脅威処理 — 損失後行動と情動モデルの対応
- `P06-003` 抑制制御 — シグナル不足での見送り行動
- `P06-004` 認知的柔軟性 — 方針転換の行動上の速度
- `P06-005` ワーキングメモリ — 複数条件の同時保持※直接推定不可
- `P06-006` 注意制御 — 重要情報への選択的反応※直接推定不可
- `P06-007` 予測誤差学習 — 予想外の結果で次の判断が変わるか
- `P06-008` 不確実性処理 — 曖昧な状況での選択変化
- `P06-009` 時間割引 — 将来大益と現在小益の選好※選択課題が必要
- `P06-010` 習慣的・目標志向的制御 — 反復反応と柔軟反応の比較
- `P06-011` 疲労と情報処理 — 連続売買時の行動変化
- `P06-012` 神経発達特性 — 診断や属性の推定は禁止
- `P06-013` 神経伝達物質 — ドーパミン等の状態推定は禁止
- `P06-014` 脳領域の活性・構造 — 扁桃体・前頭前野等の状態推定は禁止

### P07 / 生育環境・形成要因の研究 / type=not_identifiable / sources=J / academic=発達心理・社会化・ライフコース研究
- `P07-001` 幼少期の経済的安定性 — 現在のリスク選択との関連※別途本人情報
- `P07-002` 経済的困窮経験 — 金銭的損失への反応との関連※別途本人情報
- `P07-003` 家庭環境の予測可能性 — 不確実性への態度との関連※別途本人情報
- `P07-004` 家庭の金銭教育 — 資金管理習慣との関連※別途本人情報
- `P07-005` 保護者のリスク選好 — 社会的学習との関連※別途本人情報
- `P07-006` 失敗への教育経験 — 損失後の学習方法との関連※別途本人情報
- `P07-007` 成功経験の蓄積 — 自己効力感・過信との関連※別途本人情報
- `P07-008` 過去の重大な経済損失 — 現在の安全志向との関連※別途本人情報
- `P07-009` 競争経験 — 目標志向の形成との関連※別途本人情報
- `P07-010` 環境変化への適応経験 — 変動相場への適応との関連※別途本人情報
- `P07-011` 教育・専門分野 — 分析手法選択との関連※別途本人情報
- `P07-012` 職務経験・専門訓練 — ルール化・リスク管理技能との関連
- `P07-013` 過去の投資成功・失敗 — 現在の判断ルールの学習史

## 10. Source references (verified publication metadata)

- `R01` Kahneman, D., & Tversky, A. (1979). Prospect Theory: An Analysis of Decision under Risk. Econometrica, 47(2), 263–292. https://www.jstor.org/stable/1914185
- `R02` Shefrin, H., & Statman, M. (1985). The Disposition to Sell Winners Too Early and Ride Losers Too Long: Theory and Evidence. The Journal of Finance, 40(3), 777–790. https://doi.org/10.1111/j.1540-6261.1985.tb05002.x
- `R03` Odean, T. (1998). Are Investors Reluctant to Realize Their Losses? The Journal of Finance, 53(5), 1775–1798. https://doi.org/10.1111/0022-1082.00072
- `R04` Barber, B. M., & Odean, T. (2000). Trading Is Hazardous to Your Wealth: The Common Stock Investment Performance of Individual Investors. The Journal of Finance, 55(2), 773–806. https://doi.org/10.1111/0022-1082.00226
- `R05` Grinblatt, M., & Keloharju, M. (2009). Sensation Seeking, Overconfidence, and Trading Activity. The Journal of Finance, 64(2), 549–578. https://doi.org/10.1111/j.1540-6261.2009.01443.x
- `R06` Mischel, W., & Shoda, Y. (1995). A Cognitive-Affective System Theory of Personality: Reconceptualizing Situations, Dispositions, Dynamics, and Invariance in Personality Structure. Psychological Review, 102(2), 246–268. https://doi.org/10.1037/0033-295X.102.2.246
- `R07` Poldrack, R. A. (2006). Can Cognitive Processes Be Inferred from Neuroimaging Data? Trends in Cognitive Sciences, 10(2), 59–63. https://doi.org/10.1016/j.tics.2005.12.004
- `R08` Daw, N. D., Niv, Y., & Dayan, P. (2005). Uncertainty-Based Competition between Prefrontal and Dorsolateral Striatal Systems for Behavioral Control. Nature Neuroscience, 8, 1704–1711. https://doi.org/10.1038/nn1560
- `R09` Lo, A. W. (2004). The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective. The Journal of Portfolio Management, 30(5), 15–29. https://doi.org/10.3905/jpm.2004.442611
- `R10` White, H. (2000). A Reality Check for Data Snooping. Econometrica, 68(5), 1097–1126. https://doi.org/10.1111/1468-0262.00152
- `R11` Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality. The Journal of Portfolio Management, 40(5), 94–107. https://doi.org/10.3905/jpm.2014.40.5.094
- `R12` Benjamini, Y., & Hochberg, Y. (1995). Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing. Journal of the Royal Statistical Society, Series B, 57(1), 289–300. https://doi.org/10.1111/j.2517-6161.1995.tb02031.x
- `R13` Markowitz, H. (1952). Portfolio Selection. The Journal of Finance, 7(1), 77–91. https://doi.org/10.1111/j.1540-6261.1952.tb01525.x
- `R14` Rockafellar, R. T., & Uryasev, S. (2000). Optimization of Conditional Value-at-Risk. The Journal of Risk, 2(3), 21–41. https://doi.org/10.21314/JOR.2000.038
- `R15` Hinds, J., & Joinson, A. N. (2024). Digital Data and Personality: A Systematic Review and Meta-Analysis of Human Perception and Computer Prediction. Psychological Bulletin, 150(6), 727–766. https://doi.org/10.1037/bul0000430
- `R16` Almlund, M., Duckworth, A. L., Heckman, J. J., & Kautz, T. (2011). Personality Psychology and Economics. NBER Working Paper 16822. https://doi.org/10.3386/w16822

## 11. Final quality gates

- `[ ]` Trade reconstruction reproducible; contract/currency/timezone correct.
- `[ ]` Market data timestamp not after decision as-of.
- `[ ]` No unobserved MFE/MAE/psychological state invented.
- `[ ]` Costs and slippage reflected; worst-case path ambiguity tested.
- `[ ]` PnL and risk expressed in appropriate money and capital units.
- `[ ]` Uncertainty intervals and effective n reported; not only point estimates.
- `[ ]` Multiple testing and repeated rule search tracked.
- `[ ]` OOS/WF and sensitivity tests; no same-sample validation.
- `[ ]` Psychological claims have alternative explanations and consented instruments, otherwise labeled hypothesis or cannot infer.
- `[ ]` Clinical, neurological, developmental background and childhood attributes NEVER inferred from trades.
- `[ ]` Live trading NOT initiated; immutable risk protections remain external to AI.

**END: This file is research reference material, not trading instructions or individual diagnosis.**
