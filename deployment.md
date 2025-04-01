# AI Paper Summarizerデプロイ手順書

このドキュメントでは、AI Paper SummarizerをAWS Lambdaにデプロイする手順を詳しく説明します。初回デプロイから継続的デプロイまでの一連の流れを解説しています。

## 目次

- [前提条件](#前提条件)
- [初回デプロイ準備](#初回デプロイ準備)
  - [AWS環境の準備](#aws環境の準備)
  - [リポジトリの準備](#リポジトリの準備)
  - [GitHub Secretsの設定](#github-secretsの設定)
    - [Slack Webhook URLの取得方法](#slack-webhook-urlの取得方法)
- [AWS Lambda関数の設定](#aws-lambda関数の設定)
  - [Lambda関数の作成](#lambda関数の作成)
  - [環境変数の設定](#環境変数の設定)
  - [タイムアウトとメモリの設定](#タイムアウトとメモリの設定)
- [継続的デプロイ設定](#継続的デプロイ設定)
  - [IAMロールの設定](#iamロールの設定)
  - [AWSアカウントIDの確認方法](#awsアカウントidの確認方法)
  - [GitHub OIDCプロバイダーの設定](#github-oidcプロバイダーの設定)
- [Slack Bot設定とAPI取得方法](#slack-bot設定とapi取得方法)
  - [Slack Appの作成](#slack-appの作成)
  - [Bot機能と権限の設定](#bot機能と権限の設定)
  - [Appのインストールとトークン取得](#appのインストールとトークン取得)
  - [イベント購読の設定](#イベント購読の設定)
- [デプロイフロー](#デプロイフロー)
  - [開発からデプロイまでの流れ](#開発からデプロイまでの流れ)
  - [デプロイのモニタリング](#デプロイのモニタリング)
- [トラブルシューティング](#トラブルシューティング)

## 前提条件

- AWSアカウント
- GitHubアカウント
- AWS CLIがインストールされたローカル環境
- 以下のサービスのアカウントとAPI
  - Slack
  - OpenAI
  - Notion

## 初回デプロイ準備

### AWS環境の準備

1. AWSアカウントにログインします。
2. AWS CLIを設定します（まだ設定していない場合）。

```bash
$ aws configure
AWS Access Key ID [None]: あなたのアクセスキー
AWS Secret Access Key [None]: あなたのシークレットキー
Default region name [None]: ap-northeast-1 # 使用するリージョン
Default output format [None]: json
```

### リポジトリの準備

1. リポジトリをクローンします。

```bash
$ git clone git@github.com:hanoi0126/AI-paper-summarizer.git
$ cd AI-paper-summarizer
```

2. 依存関係をインストールします。

```bash
$ poetry install
```

3. `.env.example`を参考に`.env`ファイルを作成し、必要な環境変数を設定します。

```
# slack -----------------
SLACK_TOKEN=xoxb-xxxxxx # SlackのボットユーザートークンI

# openai -----------------
OPENAI_API_KEY=sk-xxxxxx # OpenAIのAPIキー

# notion -----------------
NOTION_DATABASE_ID=xxxxxx # NotionデータベースID
NOTION_KEY=secret_xxxxxx # NotionのAPIキー
```

### GitHub Secretsの設定

GitHub Actionsが AWS にアクセスするための認証情報を GitHub Secrets に設定します。

1. GitHubのリポジトリページで「Settings」タブをクリックします。
2. サイドバーの「Secrets and variables」の下にある「Actions」をクリックします。
3. 「New repository secret」ボタンをクリックし、以下のシークレットを追加します：
   - `AWS_REGION`: 使用するAWSリージョン（例: `ap-northeast-1`）
   - `AWS_ROLE_ARN`: 後で作成するIAMロールのARN
   - `SLACK_WEBHOOK_URL`: デプロイ通知用のSlack Webhook URL
   - `MY_GITHUB_TOKEN`: リリースPR作成用のGitHub Personal Access Token

#### Slack Webhook URLの取得方法

デプロイ通知に使用するSlack Incoming Webhook URLは以下の手順で取得できます：

1. [Slack API](https://api.slack.com/apps)にアクセスし、Slackアカウントでログインします。
2. 「Create New App」ボタンをクリックします。
3. 「From scratch」を選択します。
4. アプリ名（例: `Deployment Notifier`）を入力し、インストール先のワークスペースを選択します。
5. 「Create App」ボタンをクリックします。
6. 左側のメニューから「Incoming Webhooks」を選択します。
7. 「Activate Incoming Webhooks」を「On」に切り替えます。
8. ページ下部の「Add New Webhook to Workspace」ボタンをクリックします。
9. 通知を送信するチャンネルを選択し、「許可する」をクリックします。
10. 「Webhook URLs for Your Workspace」セクションに生成されたWebhook URLが表示されます。
11. URLは以下のような形式になります：
    ```
    https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
    ```
12. このURLをコピーし、GitHubのシークレット `SLACK_WEBHOOK_URL` に設定します。

**重要**: Webhook URLは秘密情報です。公開リポジトリやバージョン管理システムに保存しないでください。Slackはインターネット上に公開された秘密情報を積極的に探し、露出したトークンを無効化します。

## AWS Lambda関数の設定

### Lambda関数の作成

1. AWSコンソールにログインし、Lambda サービスに移動します。
2. 「関数の作成」ボタンをクリックします。
3. 「一から作成」を選択し、以下の項目を入力します：
   - 関数名: `ai-paper-summarizer`
   - ランタイム: `Python 3.10`
   - アーキテクチャ: `x86_64`
   - 実行ロール: 「新しいロールを作成」を選択し、基本的なLambda権限を持つロールを作成
4. 「関数の作成」ボタンをクリックして、Lambda関数を作成します。

**注意**: 実際の本番環境では、Lambda実行ロールには最小権限の原則に従って必要最低限の権限だけを付与することをお勧めします。必要に応じて、Amazon CloudWatch Logsへの書き込み権限、Amazon S3からの読み取り権限などの特定の権限を持つカスタムロールを作成してください。

### 環境変数の設定

1. 作成したLambda関数の詳細ページで「設定」タブをクリックします。
2. 「環境変数」セクションで「編集」ボタンをクリックします。
3. 以下の環境変数を追加します：
   - `SLACK_TOKEN`: Slackアプリのボットトークン
   - `OPENAI_API_KEY`: OpenAIのAPIキー
   - `NOTION_DATABASE_ID`: NotionデータベースのID
   - `NOTION_KEY`: NotionのAPIキー
4. 「保存」ボタンをクリックして環境変数を保存します。

### タイムアウトとメモリの設定

1. 「設定」タブの「一般設定」セクションで「編集」ボタンをクリックします。
2. 以下の設定を変更します：
   - タイムアウト: `60秒`（論文処理には長めのタイムアウトが必要）
   - メモリ: `512 MB`（OpenAI APIの呼び出しなどに十分なメモリが必要）
3. 「保存」ボタンをクリックして設定を保存します。

## 継続的デプロイ設定

### IAMロールの設定

GitHub Actions から AWS リソースにアクセスするための IAM ロールを作成します。

1. AWS マネジメントコンソールで IAM サービスに移動します。
2. サイドバーの「ロール」をクリックし、「ロールを作成」ボタンをクリックします。
3. 「カスタム信頼ポリシー」を選択し、以下のJSONを貼り付けます：

### AWSアカウントIDの確認方法

AWSアカウントIDは、信頼ポリシーの設定などで必要になります。以下の方法で確認できます。

1. **AWS マネジメントコンソールで確認する方法**:
   - AWS マネジメントコンソールにログインします。
   - 画面右上のアカウント名またはアカウント番号をクリックし、「セキュリティ認証情報」を選択します。
   - 「アカウントの詳細」セクションに「AWS アカウントID」として12桁の数字が表示されます。

2. **AWS CLI を使用して確認する方法**:
   - 以下のコマンドを実行します：
   ```bash
   aws sts get-caller-identity --query Account --output text
   ```
   - 12桁のアカウントIDが表示されます。

3. **IAMユーザーでログインしている場合**:
   - 画面右上のユーザー名をクリックし、「セキュリティ認証情報」を選択します。
   - ページ上部の「アカウントの詳細」セクションに「AWS アカウントID」が表示されます。

取得したアカウントIDを以下の信頼ポリシーの `<AWSアカウントID>` の部分に入力してください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<AWSアカウントID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:hanoi0126/AI-paper-summarizer:ref:refs/heads/prd"
        }
      }
    }
  ]
}
```

4. 「次へ」をクリックします。
5. 「権限を追加」で、`AWSLambdaFullAccess` ポリシーを検索して選択します。
   - 本番環境では、最小権限原則に従って、必要な権限のみを持つカスタムポリシーを作成することをお勧めします。
6. 「次へ」をクリックします。
7. ロール名（例: `GitHubActionsLambdaDeployRole`）を入力し、「ロールを作成」をクリックします。
8. 作成したロールの ARN をメモして、GitHub Secrets の `AWS_ROLE_ARN` に設定します。

### GitHub OIDCプロバイダーの設定

AWS と GitHub Actions の間で OIDC 認証を設定します。

1. IAM コンソールで、サイドバーから「IDプロバイダー」を選択します。
2. 「プロバイダーを追加」ボタンをクリックします。
3. 以下の情報を入力します：
   - プロバイダータイプ: `OpenID Connect`
   - プロバイダーURL: `https://token.actions.githubusercontent.com`
   - 対象者: `sts.amazonaws.com`
4. 「プロバイダーを追加」ボタンをクリックします。

## Slack Bot設定とAPI取得方法

**注意**: Slackは2025年3月31日に従来のカスタムボット（レガシーボット）のサポートを終了する予定です。以下の手順では、最新のSlack App APIを使用するように設定します。

### Slack Appの作成

1. [Slack API](https://api.slack.com/apps)にアクセスし、Slackアカウントでログインします。
2. 「Create New App」ボタンをクリックします。
3. 「From scratch」を選択します。
4. アプリ名（例: `AI Paper Summarizer`）を入力し、インストール先のワークスペースを選択します。
5. 「Create App」ボタンをクリックします。

### Bot機能と権限の設定

1. 左側のメニューから「OAuth & Permissions」を選択します。
2. 「Scopes」セクションまでスクロールし、「Bot Token Scopes」で「Add an OAuth Scope」をクリックします。
3. 以下の権限（スコープ）を追加します：
   - `chat:write` - メッセージを送信する
   - `conversations:history` - スレッド内の会話履歴を読み取る

4. 左側のメニューから「App Home」を選択します。
5. 「Show Tabs」セクションで「Messages Tab」を有効にします。
6. 「Allow users to send Slash commands and messages from the messages tab」にチェックを入れます。

### Appのインストールとトークン取得

1. 左側のメニューから「Install App」を選択します。
2. 「Install to Workspace」ボタンをクリックし、権限を確認してアプリをインストールします。
3. インストールが完了すると、「OAuth & Permissions」ページに「Bot User OAuth Token」が表示されます。
4. このトークン（`xoxb-`で始まる）をコピーし、`.env`ファイルの`SLACK_TOKEN`に設定します。
   ```
   SLACK_TOKEN=xoxb-xxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
   ```

### イベント購読の設定

1. 左側のメニューから「Event Subscriptions」を選択します。
2. スイッチをオンにして機能を有効化します。
3. Request URLにLambda関数のURLまたはAPI GatewayのエンドポイントURLを入力します。
   - ローカル開発の場合は、ngrokなどのツールでローカルサーバーを公開し、そのURLを設定します。
4. 「Subscribe to bot events」セクションで「Add Bot User Event」をクリックし、以下のイベントを追加します：
   - `message.channels` - パブリックチャンネルでのメッセージ
   - `reaction_added` - リアクションが追加されたとき
   - `file_shared` - ファイルが共有されたとき
5. 「Save Changes」ボタンをクリックして設定を保存します。
6. Appの変更を適用するには、再度「Install App」からワークスペースにインストールする必要があります。

## デプロイフロー

### 開発からデプロイまでの流れ

AI Paper Summarizerのデプロイフローは以下のとおりです：

1. **開発**:
   - 開発者はローカルで機能開発やバグ修正を行います。
   - 変更を `main` ブランチにプッシュします。

2. **リリースPR作成**:
   - `main` ブランチへのプッシュがトリガーとなり、GitHub Actionsが自動的にリリースPRを作成します。
   - このPRは `main` ブランチから `prd` ブランチへのマージを提案します。

3. **コードレビュー**:
   - チームメンバーがリリースPRをレビューします。
   - 問題がなければPRを承認し、マージします。

4. **自動デプロイ**:
   - `prd` ブランチへのマージがトリガーとなり、GitHub Actionsが自動的にデプロイを開始します。
   - デプロイプロセスは以下の手順で行われます：
     1. 依存関係をLambda Layerとしてパッケージ化
     2. Lambda Layerをデプロイ
     3. アプリケーションコードをパッケージ化
     4. Lambda関数を更新
     5. Lambda関数にLayerをアタッチ

5. **デプロイ通知**:
   - デプロイの成功/失敗はSlackに通知されます。

### デプロイのモニタリング

デプロイの進行状況や結果は以下の方法でモニタリングできます：

1. **GitHub Actions**:
   - GitHubリポジトリの「Actions」タブで、ワークフローの実行状況を確認できます。
   - 各ステップの詳細なログを見ることができます。

2. **Slack通知**:
   - デプロイの結果はSlackに自動的に通知されます。

3. **AWS Lambda コンソール**:
   - AWS Lambdaコンソールで、関数の更新状況やバージョンを確認できます。

## トラブルシューティング

### デプロイが失敗する場合

1. **GitHub Actionsのログを確認**:
   - エラーメッセージを確認して、問題を特定します。

2. **IAM権限の問題**:
   - IAMロールに必要な権限が付与されているか確認します。
   - OIDCプロバイダーとIAMロールの信頼ポリシーが正しく設定されているか確認します。

3. **AWS Lambda設定の問題**:
   - Lambda関数名が正しいか確認します。
   - 環境変数が正しく設定されているか確認します。

4. **依存関係の問題**:
   - `requirements.txt` に必要なパッケージがすべて含まれているか確認します。

### Lambda関数が正しく動作しない場合

1. **CloudWatchログの確認**:
   - AWS CloudWatchログで、Lambda関数のログを確認します。
   - エラーメッセージやスタックトレースを確認して、問題を特定します。

2. **環境変数の確認**:
   - 必要な環境変数がすべて正しく設定されているか確認します。

3. **手動テスト**:
   - AWSコンソールでLambda関数の「テスト」機能を使用して、関数を手動でテストします。
   - テストイベントを適切に設定し、関数の動作を確認します。 