# Trade Behavioral Research | CFD・FX取引履歴の学際的評価

**研究用・公開可能なテンプレート集 + 検証可能な分析フロー**  
**全379指標・29カテゴリ（FULL）／76指標・29カテゴリ（LITE）**

CFD・FXの売買履歴を、金融工学・統計学・行動ファイナンス・認知科学の観点から解析し、仮想的な理想運用モデル **QUANT-OMEGA** と比較するためのリポジトリです。指標IDはFULLとLITEで共通です。

> **最重要**：QUANT-OMEGAは「損失なしで全相場から必ず利益を得る実在投資家」ではありません。**観測実績のない規範的な運用品質モデル**です。5点は運用プロセスの目標であり、勝率・収益率・取引能力の実測値ではありません。本リポジトリは研究用であり、利益を保証せず、個人への金融助言や取引の自動発注を目的としません。

## GitHubブラウザのみで更新する（v1.1.0）

OSの隠しファイル選択は不要です。`docs/GITHUB_BROWSER_UPLOAD.md` の手順に従い、GitHub上で `.github/workflows/check.yml` を1ファイルだけ作成（コードを貼り付け）し、配布の `release_bundle.zip` を1ファイルアップロードします。CIがZIPを展開し、`.gitignore` と最新の研究・テンプレートを反映します。ワークフローはブラウザから作成するため、Actionsトークンにワークフロー編集権限を与える必要はありません。

- ZIPを展開してFinderから大量選択する必要はありません。
- 最初に `.github/workflows/check.yml` をWebの編集画面で追加します。
- `release_bundle.zip` をアップロードするとActionsが展開・検証し、元ZIPを削除してコミットします。
- `Actions` の最新 `Import release and verify` が成功、Codeに `.gitignore` が存在することを確認します。
- 公開リポジトリに実際の顧客・投資家の取引CSVをアップロードしないでください。

## v1.1.0 修正内容

- Excelの評価ステータスを日本語の制御値へ変換。機械の元状態は所見欄とCSVに保存します。
- 複数データセットの場合は `comparison_lite.xlsx` / `comparison_full.xlsx` を生成。比較可能性は人間の確認まで未確認のままにします。
- 研究文書中のファイル参照を正式なGitHubディレクトリへ統一。
- 必須ファイルとマニフェスト内容を照合する検証器に変更。
- ワースト5件の集中警告を取引数・損失件数が少ないときに保留。
- 取引評価CSVへ `data_asof_utc` と `source_sha256` を追加（ソースファイル単位）。
- 未実装：生約定明細の建玉復元、MFE/MAEの市場価格経路計測、脳・人格・生育歴の推定。

## クイックスタート

### 1. GitHubをAIと共有して使う（推奨）

1. このリポジトリのURL、または展開したフォルダをAIに渡してください。
2. **取引履歴は公開GitHubにpushせず**、AIとの非公開セッションまたはローカル環境で渡してください。
3. `AGENTS.md` と [`prompts/analyze_with_ai.md`](prompts/analyze_with_ai.md) を読み込むように指定してください。
4. まずLITE 76項目、必要に応じてFULL 379項目について「実測 / 不足データ / 仮説 / 識別不能」を厳格に区別し、QUANT-OMEGAとの差分、行動傾向、改善仮説、検証計画を出力させます。

**そのまま使える依頼文**

> このGitHubリポジトリの `AGENTS.md` と `prompts/analyze_with_ai.md` に従って、添付したCFD/FX売買履歴を評価してください。最初はLITE 76指標、必要ならFULL 379指標も実施。評価不能なものは埋めず、QUANT-OMEGAの規範的な品質目標とギャップ分析を行い、観測事実・行動仮説・競合説明・改善策・期間外検証計画を分けて報告してください。個人の脳・性格・生育歴を断定しないでください。

### 2. ローカルでデータを解析する（再現可能な一次評価）

Python 3.11+ を推奨します。

```bash
python -m pip install -r requirements.txt
python tools/evaluate_trades.py \
  --input examples/synthetic_round_trips.csv \
  --mode lite \
  --out outputs/demo
```

出力は `outputs/demo/A/` に保存されます。既に `examples/demo-output/A/` に**合成データのみ**を用いた出力例も収録しています。`outputs/` は `.gitignore` により公開対象外です。

実データに差し替える場合（完成した1建玉・1決済の往復取引ごとに1行）：

```bash
python tools/evaluate_trades.py \
  --input private/my_trades.csv \
  --mode full \
  --out outputs/my_study
```

取引日時がタイムゾーンなしで記録されている場合は `--timezone Asia/Tokyo`（既定値）を検証してください。損益通貨列がなければ、`--currency JPY` のように**明示的に**指定します。異なるブローカーの列名には `--columns config/columns.example.json` を元に作ったローカルJSONを使用できます。

### 3. 取引履歴 A〜D の比較

```bash
python tools/evaluate_trades.py \
  --dataset A:private/before.csv \
  --dataset B:private/after.csv \
  --mode lite \
  --out outputs/before_after
```

`cross_dataset_lite.csv` は**指標IDで突合するための縦持ち資料**です。前後差や銘柄差を因果的な改善とみなす前に、通貨・契約倍率・手数料・取引頻度・相場状態・取引期間を揃えてください。自動的に「改善」とは判定しません。

### 4. 専門家による根拠付きプロセス評価（任意）

定量パフォーマンスとプロセス品質を混同しないため、1〜5点の評価スコアは**自動生成しません**。実証根拠とともに評価したい場合は、`examples/synthetic_ratings_example.csv` を参照してください。

```bash
python tools/evaluate_trades.py \
  --input examples/synthetic_round_trips.csv \
  --ratings examples/synthetic_ratings_example.csv \
  --mode lite \
  --out outputs/demo_with_review
```

規範的プロセス品質の対象指標かつ根拠IDと証拠水準がある場合に限り、`process_gap_points = 5 - score_1_5` を表示します。**得点差は利益率の差ではありません。** 他の指標については「条件依存」「仮説」「識別不能」として扱います。

## リポジトリ構造

```text
.
├── README.md / AGENTS.md / LICENSE / .gitignore
├── research/
│   ├── paper.md / paper.pdf / paper.docx           # 人間向け論文（同一内容の3形式）
│   ├── methodology_for_ai.md                       # AI向け研究方法論
│   ├── evaluation_protocol.md                      # 比較評価手順
│   └── quant_omega_protocol.md                     # 仮想理想トレーダーの前提
├── registry/
│   ├── metrics_full_379.json                       # 29カテゴリ・379指標の唯一の元定義
│   ├── priority_lite_selection.json                # 76指標の選定・優先順
│   └── original_template_manifest.json            # 元成果物の整合記録
├── templates/
│   ├── evaluation_full_379.xlsx / evaluation_full_379x4.csv
│   └── evaluation_lite_76.xlsx / evaluation_lite_76x4.csv
├── benchmark/quant-omega/
│   └── ideal_model_full_379.json                   # 理想プロセスの機械可読モデル
├── examples/
│   ├── ideal-trader/                              # 理想評価の見本（FULL/LITE、CSV/XLSX）
│   ├── synthetic_round_trips.csv                  # 架空データのみ
│   ├── synthetic_ratings_example.csv              # 架空の監査者採点例
│   ├── demo-output/                               # 架空データを使った出力例
│   └── previews/                                  # UIプレビュー
├── config/columns.example.json                   # ブローカー列名の対応例
├── prompts/analyze_with_ai.md                    # コピペ用AIタスク仕様
├── tools/evaluate_trades.py                      # 一次解析・結果作成CLI
├── tools/package_release.py                       # ZIP再生成と整合確認
├── tools/validate_release.py                     # ID・整合性・公開安全検査
├── tools/make_synthetic_example.py               # 架空データ再生成
└── tests/                                        # ユニットテスト
```

旧世代のZIPをZIPの中に入れることはせず、**原典となるユニークな成果物のみ**整理しました。論文のPDF・Word・Markdown、AI用資料、元の比較テンプレート、理想モデルのFULL/LITE出力例は維持しています。

## 取り込み可能な売買データ

一次解析のスクリプトは**約定ごとの生レコードではなく、完結したポジション単位（round-trip）**を受け取ります。約定が分割されている場合、FIFO/平均法/建玉IDなどブローカーが定義した方法で先に対応付ける必要があります。**勝手なペアリングは禁止**です。

| 項目 | 必須 | 説明 |
|---|---|---|
| `trade_id` | 推奨 | 一意の完結取引ID。省略時は行番号から仮IDを付与（分割約定の復元には使えない） |
| `instrument` | 必須 | 銘柄・取引対象（契約条件は別途確認） |
| `side` | 必須 | LONG / SHORT （buy / sell、買 / 売にも対応） |
| `entry_time`, `exit_time` | 必須 | ISO 8601日時。UTCまたはタイムゾーンを明記することを強く推奨 |
| `quantity` | 必須 | 正の数量。銘柄横断の数量加算は不可 |
| `net_pnl` | 原則必須 | **費用控除後**・統一通貨建ての確定損益。基準を確認すること |
| `gross_pnl`, `fees` | 代替可 | `net_pnl` がない場合は両方必須。`net_pnl` がある場合は検算に使用 |
| `currency` | 必須 | JPY等。ない場合は `--currency` で明示 |
| `entry_price`, `exit_price` | 推奨 | 価格経路の代わりにはならないため、MFE/MAEは算定しない |

CSVとXLSXの先頭シートに対応します。追加の価格履歴(P)、注文・取消履歴(O)、残高・含み損益(A)、判断日誌(J)、経済イベント(X)はAIと共有すれば分析対象を拡張できますが、**CLIの一次評価だけで全379項目を実測できるわけではありません**。

## 出力物とギャップ分析の解釈

1. `evaluation_lite.csv` / `evaluation_full.csv`: **全行を必ず保持**。各項目について実測値・情報不足・仮説・識別不能を表示します。
2. `gap_analysis_*.csv`: 左にユーザー観測値と状態、右に理想行動・検証条件・品質スコア差（根拠付きの場合のみ）。
3. `evaluation_*.xlsx`: 既存のA評価欄に観測可能な値を記入し、B〜Dは今後の比較用に空欄のまま残します。
4. `analysis_report.md` / `behavior_analysis.md`: 行動傾向を記述し、心理仮説には競合する説明を併記します。
5. `candidate_actions.csv`: 観測データから導いた改善仮説と、その反証・期間外検証の案です。
6. `provenance.json`: データの期間・通貨・解析スコープ・未確認事項の記録です。

**理想モデルは一律の正解値ではありません。** 時間帯、保有時間、銘柄、テクニカル指標などの指標には固定の最適値が存在せず、レジームや戦略依存です。脳機能・発達特性・生育環境は取引履歴から判定できません。

## 公開GitHubに載せる際の注意

- 実際の売買履歴、取引口座番号、氏名、住所、メール、注文ID、APIキー、トークン、心理日誌などは公開しないでください。
- `.gitignore` は `private/`、`data/`、`outputs/`、`.env`、秘密鍵などを除外します。ただし**既にGit管理へ追加済みの機密ファイルは `.gitignore` では保護できません**。push前に必ず `git status` と差分を確認してください。
- 公開前に `python tools/validate_release.py` と `python -m unittest discover -s tests -v` を実行してください。
- 全サンプルは合成・仮想です。実取引の勝率やバックテスト成績と解釈しないでください。
- 改善候補は研究仮説であり、未来の利益を保証しません。実行を伴う判断には別のリスク管理・承認が必要です。

## 出典・ライセンス

研究に関する学術文献への参照先は `research/paper.md` と `registry/metrics_full_379.json` に記載しています。引用元の論文本文や商用の市場データは同梱していません。このリポジトリ自身のオリジナルなコード・文章・テンプレートのライセンスは [MIT](LICENSE) とします。第三者素材に対する権利を付与するものではありません。
