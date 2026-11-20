# 売買履歴比較評価テンプレート｜AI入出力プロトコル v1.0

## 範囲
- 元指標辞書: `registry/metrics_full_379.json`（379指標、29カテゴリ）。**元ID・項目・カテゴリは改変しない**。
- 全量: `templates/evaluation_full_379.xlsx`。Lite: `templates/evaluation_lite_76.xlsx`（76/379=20.1%、29/29カテゴリ）。
- 順序と抽出根拠: `registry/priority_lite_selection.json`。
- 入力交換: `templates/evaluation_full_379x4.csv` または `templates/evaluation_lite_76x4.csv`。`dataset_id`×`metric_id` を一意キーとする。

## 研究目的
1. 適切な建玉復元・損益整合性を前提に、事実として計測できる取引指標を比較する。
2. 保有時間・利確・損切り・ロット・連敗後の行動・心理仮説を、同一データ定義で比較する。
3. 相場環境・通貨・契約倍率・売買費用・時点情報の違いを統制して、比較可能性を評価する。
4. 交易成績や行動パターンを人間の性格・神経・生育要因の診断へと不当に飛躍させない。

## 処理順（厳守）
- P0: インポート。CSVまたは約定履歴を受領し、タイムゾーン、建玉再構成、契約倍率、コスト、データ欠損を監査。
- P1: データセット情報(A/B/C/D)の期間・戦略バージョン・銘柄・通貨・市場を定義。
- P2: FULLは379指標、Liteは76指標を**全件**返す。測定不能も行を削除しない。
- P3: 各指標に value/unit/status/qualitative_finding/effective_n/evidence_level/source_reference/data_asof_utc/alternative_explanations/uncertainty/next_validation を記す。
- P4: 観測`observed`、推論`inference`、心理仮説`hypothesis`、反実仮想`counterfactual`、非識別`not_identifiable`を区別。
- P5: 比較前に同一指標定義・単位・通貨・契約倍率・費用・観測期間・N/交絡・レジームの違いを点検。比較条件が成立しないときは差の意味を定量的に断定しない。
- P6: 試行の数・事前登録の有無・時点リーケージ・期間外検証・不確実性を監査し、推奨は`RESEARCH_ONLY`等で留保する。

## CSV出力上の拘束
- `dataset_id`: A, B, C, D（必要なら同形式の行を追加して数は無制限）。
- `metric_id`: 元辞書に存在する不変ID。重複または欠損はエラー。
- `numeric_value`: 実測できない場合は空欄。0と欠測は区別する。
- `unit`: ％は数値52.3と単位%（前後差はポイント）、通貨/ポイント/分などは明示。
- `score_1_5`: 操作的なルーブリックが明記される場合のみ付ける。非識別項目に付けない。
- `assessment_status`: 評価済/仮説段階/要追加データ/識別不可/対象外/レビュー待ち。
- `evidence_level`: L0/L1/L2/L3/L4/NI。
- `source_reference`: ファイル名、明細ID、URL、シート、計算手順などをできるだけ具体化。
- `data_asof_utc`: 情報が当時観測可能になった時点。未来情報を使わない。
- `alternative_explanations`: 交絡・逆因果・選択バイアス・他の説明を列挙。
- 未解析の時点で値や確証を創作して埋めない。`null`／空欄を適切に使用。

## 脳・心理・生育環境の推論上の禁止事項
- 売買履歴から性格診断、精神疾患・神経発達診断、脳領域の活性、ドーパミン等の状態を断定しない。
- 売買履歴から生育環境、幼少期の経済事情、保護者の性格、トラウマ等を推定しない。
- 「負け直後の再参入 = リベンジ」と断定せず、戦略・相場・時間帯の対立仮説と比較する。
- `P06`と`P07`は、本人の任意提供情報がない限り`識別不可`を原則とする。
- 取引数が少ない条件を掘り続けて偶然の優位性を確定しない。

## 最小出力契約
`task_type, as_of, datasets, data_quality, metric_results, observed_patterns, candidate_hypotheses, alternative_explanations, evidence_levels, comparison_gates, uncertainty, validation_plan, remaining_limitations, decision`

## ワークフロー提案
1. Lite76（29カテゴリすべて）→ 2. 問題あり/要検証のカテゴリのみFull379で精査 → 3. タイムスタンプ付き価格データの追加 → 4. 事前確定した対策のWalk-Forward・OOS検証。

研究状態: `RESEARCH_ONLY`。売買注文を実行しない。未検証の収益改善を保証しない。
