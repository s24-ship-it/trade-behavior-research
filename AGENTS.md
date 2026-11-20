# AI Agent Instructions | CFD・FX行動研究

このファイルは、このリポジトリと利用者の売買履歴を共有されたAIが遵守すべき分析契約です。

## ミッション

CFD/FXの売買履歴から、検証可能な実績・行動傾向を計算し、`registry/metrics_full_379.json` と `registry/priority_lite_selection.json` のIDを保った評価を出力する。`benchmark/quant-omega/ideal_model_full_379.json` と照合してギャップを特定し、原因仮説・競合仮説・改善候補・期間外検証計画を作る。**無敗・全環境利益の保証や実在する完璧な投資家は想定しない**。

## 読み込み順

1. `README.md`: 使い方・入力スキーマ・秘密情報の取り扱い。
2. `registry/metrics_full_379.json`: 唯一の指標定義（379件、29カテゴリ）。
3. `registry/priority_lite_selection.json`: LITE 76件、29カテゴリ。指標IDは不変。
4. `benchmark/quant-omega/ideal_model_full_379.json`: 架空の品質目標。スコア5は実測値ではない。
5. `research/evaluation_protocol.md` と `research/methodology_for_ai.md`: 根拠・反証・必要データ。
6. 必要なら `research/paper.md` の出典・研究の限界。

## 処理仕様

1. 公開されないセッション／ローカルで利用者の取引履歴を読み、CSV/XLSXの列名と費用算定を確定する。
2. 1件の建玉と約定の対応を監査し、建玉IDがない分割約定を根拠なく1取引とみなさない。約定明細しかない場合は原始データの解釈を求める。
3. 損益通貨、契約倍率、通貨換算、手数料、スプレッド、スワップ、入出金、含み損益の扱いを明記する。異通貨の損益を無換算で合算しない。
4. `python tools/evaluate_trades.py --input <private-file> --mode lite --out outputs/<case>` の一次評価を起点に、追加データがあれば再計測する。
5. LITEは**全76行・全29カテゴリ**、FULLは**全379行・全29カテゴリ**を出力し、省略しない。未測定なら `NEEDS_DATA` 等で明示し、決して補完・捏造しない。
6. 1指標につき、`metric_id,category,raw_data,data_asof,measurement_definition,value,unit,effective_n,uncertainty,evidence,alternatives,ideal_reference,gap,action,falsification` を再現可能な形で保持する。
7. 観測事実(L0)、決定的計算(L1)、統計的関連(L2)、心理仮説(L3)、検証された限定的結論(L4)を区別。説明と因果を混同しない。
8. ギャップは、**数値指標を規範的な5点から減算しない**。プロセススコアが、事前定義されたルーブリックと出典付き証拠で採点された場合のみ `5 - score`。評価できない場合は情報不足のギャップとして表示する。
9. 性格、衝動性、感情、バイアス、スキルは個人内の**行動指標・仮説**としてのみ扱う。取引履歴から生育歴、脳の状態、神経伝達物質、神経発達特性を同定・診断しない。
10. 損失を減らす改善提案は「仮説」「見込まれる機序」「別の説明」「必要データ」「固定された検証計画」「コスト/NO_TRADE条件」のセットで提出する。
11. 指標を探索して良かった条件だけ報告しない。多数の試行・サンプル数・時系列依存・情報利用可能時点・費用・レジーム変化を扱う。
12. 最終判断は `RESEARCH_ONLY`, `NEEDS_DATA`, `SUPPORTED_WITH_LIMITATIONS`, `REJECTED` などを使用。実際の取引を発注しない。

## 最終納品（必須）

- `evaluation_lite.csv` または `evaluation_full.csv`（欠落IDゼロ）および編集可能な同等Excel。
- `gap_analysis_*.csv`（ユーザー値と理想の行動品質基準を並置。比較不可能性も明記）。
- `analysis_report.md`（成績・時間/曜日/銘柄/方向/保有時間・大損失要因を、得られたデータの範囲で）。
- `behavior_analysis.md`（行動の観測と心理仮説・代替説明を分離）。
- `candidate_actions.csv`（優先度・対策案・反証・OOS検証・リスク停止条件）。
- `provenance.json`（使用したファイル・時点・欠損・変更履歴）。

## 秘密保持と公開への禁止事項

利用者の売買履歴・口座情報・個人日誌・入力ファイル・分析結果を**公開リポジトリにcommitしない**。`.gitignore` だけを機密保持機能とみなさず、公開前のステージング差分と履歴を検査する。`examples/` はすべて架空データのみを扱う。
