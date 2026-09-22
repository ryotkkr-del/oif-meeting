# OIF Meeting

OIF向けのローカル会議レコーダーです。

## v0.1
- ブラウザで対面 / Discord録音
- 録音終了後に WhisperX large-v3 で日本語文字起こし
- pyannote による話者分離
- 技術用語 hotwords 設定
- speaker付き transcript.txt 生成
- 設定したGmailへ自動送信
- 送信先Gmailはブラウザの設定画面から変更可能
- 秘密情報はOSの資格情報ストアに保存

## Windowsセットアップ
1. Python 3.10+ を用意
2. FFmpeg: `winget install Gyan.FFmpeg`
3. `python -m venv .venv`
4. `.\.venv\Scripts\activate`
5. `pip install -r requirements.txt`
6. `pip install whisperx`
7. Hugging Faceで `pyannote/speaker-diarization-community-1` の利用条件に同意しRead tokenを作成
8. Gmailで2段階認証を有効にし、アプリパスワードを作成
9. `start.bat`

起動後、右上の「設定」でGmail・Hugging Face token・話者数・専門用語を設定します。

> 録音・文字起こしを行う場合は、参加者へ事前に知らせ、必要な同意を取ってください。
