from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from openai import OpenAI
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# -------------------------
# パスの設定
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
HTML_FILE = BASE_DIR / "templates" / "index.html"

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)
# -------------------------
# FastAPI / OpenAI の準備
# -------------------------
app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

load_dotenv()

client = OpenAI()

# -------------------------
# トップページ
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return HTML_FILE.read_text(encoding="utf-8")

# -------------------------
# 音声アップロード
# -------------------------
@app.post("/upload")
async def upload_audio(
    request: Request,
    audio_file: UploadFile = File(...)
):

    # -------------------------
    # ファイル形式チェック
    # -------------------------
    allowed_types = [
        "audio/mpeg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/m4a"
    ]

    if audio_file.content_type not in allowed_types:
        return HTMLResponse(
            content="対応していないファイル形式です。",
            status_code=400
        )
    
    # -------------------------
    # アップロードされた音声をメモリ上で読み込む
    # -------------------------
    audio_bytes = await audio_file.read()

    # -------------------------
    # ファイルサイズチェック
    # -------------------------
    MAX_FILE_SIZE_MB = 25
    MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


    if len(audio_bytes) > MAX_FILE_SIZE:
        return HTMLResponse(
            content=f"ファイルサイズが大きすぎます。{MAX_FILE_SIZE_MB}MB以下の音声ファイルを選択してください。",
            status_code=400
        )

    # -------------------------
    # OpenAI API処理
    # -------------------------
    try: 
        # 音声 → 文字起こし
        transcription = client.audio.transcriptions.create(
            model="gpt-transcribe",
            file=(audio_file.filename, audio_bytes)
        )
    
        # 文字起こし → 議事録
        minutes = client.responses.create(
            model="gpt-5.4-mini",
            input=f"""
以下の会議の文字起こしから、日本語で議事録を作成してください。

【重要】
・文字起こしに存在しない情報を推測して追加しないでください。
・担当者、日時、決定事項などが不明な場合は「記載なし」としてください。
・必ず自然な日本語のみを使用してください。
・各項目の間には必ず改行を入れてください。
・各項目の内容も改行して記載してください。

【文字起こし】
{transcription.text}

【議事録の形式】

■ 会議概要
内容

■ 主な議題
・内容
・内容

■ 決定事項
・内容

■ 担当者とタスク
・内容

■ 次回会議
・内容
"""
        )

    except Exception as e:
        print("OpenAI APIエラー:", e)

        return HTMLResponse(
            content="議事録の作成中にエラーが発生しました。",
            status_code=500
        )

    # -------------------------
    # 結果をブラウザへ返す
    # -------------------------
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "filename": audio_file.filename,
            "transcription": transcription.text,
            "minutes": minutes.output_text
        }
    )