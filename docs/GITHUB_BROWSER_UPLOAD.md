# ブラウザだけでGitHubの完全版を反映する（v1.1.0）

## ファイル

- `GITHUB_PASTE_check.yml`：GitHubの `.github/workflows/check.yml` 画面に全文を貼り付けるためのソース。配布ZIPの外側に付属。
- `release_bundle.zip`：ZIP展開不要、そのままGitHubにアップロード。

## 現在の公開リポジトリを更新する推奨手順

1. https://github.com/s24-ship-it/trade-behavior-research を開く。
2. `Code` → `Add file` → `Create new file` を選ぶ。
3. Filename欄に `.github/workflows/check.yml` と入力する。
4. 提供した `GITHUB_PASTE_check.yml` の全文を貼り付ける。
5. `Commit changes...` → `Commit directly to the main branch` → `Commit changes`。
6. `Code` に戻り、`Add file` → `Upload files`。
7. **ZIPを展開せず** `release_bundle.zip` だけアップロード。
8. `Commit changes...` から `main` にコミット。
9. `Actions` → `Import release and verify` → ZIPアップロードによる直近の実行を開き、**緑のチェック**を確認。
10. `Code` 画面で `.gitignore`、`.github/workflows/check.yml`、`MANIFEST.sha256`、`templates/`、`benchmark/`が存在し、`release_bundle.zip`が消えていることを確認する。
11. 実際のユーザーデータはアップロードしない。使用は README・AGENTS・promptsの指定に従う。

自動取込処理は `.github/workflows/check.yml` の内容を変更しません。Actions標準トークンはワークフローの変更権限を持たないため、ワークフローだけはブラウザから登録します。

## トラブル時

- Actionsがない：ワークフローの場所が正確に `.github/workflows/check.yml` か、`main` ブランチにコミット済みか確認。
- `Run workflow`が見えない：`Actions` の該当ワークフロー画面へ移動する。通常は ZIPアップロードで自動実行される。
- `Permission denied`：`Settings`→`Actions`→`General`のWorkflow permissionsを確認。ワークフロー側で`contents: write`を指定しています。
- `sha256 mismatch`：ZIPを再度アップロードする前に同名ファイルの内容を変更していないか確認。
- CIが失敗：`Actions` の該当実行の `import-and-verify`を展開し、赤字のエラー箇所を確認。失敗した状態で更新はコミットされません。ただしアップロードしたZIPがmain上に残るため、修復後に再実行する必要があります。
- 新しいリポジトリを使いたい場合：同名で新規公開リポジトリを作成（README初期化）して同手順。ワークフローの`main`名は揃える。

## 安全上の注意

公開リポジトリでは、ファイルを削除してもGitの過去コミットに残ることがあります。機密データを誤アップロードした場合は速やかに資格情報の無効化と履歴削除対応を行ってください。`.gitignore`は既にコミットしたファイルを秘密に戻す機能ではありません。
