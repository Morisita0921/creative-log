"""
MoriEdit CreativeLog — 支援記録アシスタント
メタゲーム明石向け：日次支援記録の文章生成ツール
"""

import os
import sys
import json
import random
import urllib.request
import urllib.error
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# EXE化した場合のパス解決
if getattr(sys, 'frozen', False):
    _BASE = Path(sys._MEIPASS)
    _EXE_DIR = Path(sys.executable).parent
else:
    _BASE = Path(__file__).parent
    _EXE_DIR = _BASE

app = Flask(__name__, template_folder=str(_BASE / "templates"))

# --- データの永続化（EXEの場合はEXEと同じフォルダに保存） ---
DATA_DIR = _EXE_DIR / "data"
MEMBERS_FILE = DATA_DIR / "members.json"
OPTIONS_FILE = DATA_DIR / "options.json"

# デフォルトの選択肢（初回起動時に options.json へ書き出す）
DEFAULT_OPTIONS = {
    "activities": [
        "動画編集",
        "サムネイル制作",
        "イラスト制作",
        "3Dモデリング",
        "Webデザイン",
        "アニメーション制作",
        "名札制作",
        "CANVA作業",
        "デザイン制作",
        "eスポーツ実習",
        "ゲームプレイ",
        "チーム練習",
        "動画リサーチ",
        "ソフトの操作練習",
        "チュートリアル学習",
        "講義・インプットタイム",
        "PC入力作業",
        "動画配信",
        "ミーティング",
    ],
    "behaviors": [
        "集中して取り組んでいた",
        "質問しながら丁寧に進めていた",
        "試行錯誤しながら進めていた",
        "落ち着いた様子で取り組んでいた",
        "リサーチしながらイメージを膨らませていた",
        "操作に少し苦戦していた",
        "スムーズに進めることができていた",
        "楽しそうに取り組んでいた",
        "1人で集中してプレイしていた",
        "他の利用者と協力していた",
    ],
    "impressions": [
        "落ち着いた様子だった",
        "緊張している様子だった",
        "表情が硬い印象だった",
        "積極的にコミュニケーションをとっていた",
        "他の利用者に声をかけるなど思いやりが見られた",
        "自分のペースで無理なく取り組めていた",
        "体調が良さそうだった",
        "少し疲れている様子だった",
        "意欲的に新しいことに挑戦していた",
        "前回より成長が見られた",
    ],
}


def _load_json(filepath, default):
    if filepath.exists():
        return json.loads(filepath.read_text(encoding="utf-8"))
    return default


def _save_json(filepath, data):
    DATA_DIR.mkdir(exist_ok=True)
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_members():
    return _load_json(MEMBERS_FILE, [])


def save_members(members):
    _save_json(MEMBERS_FILE, members)


def load_options():
    return _load_json(OPTIONS_FILE, DEFAULT_OPTIONS)


def save_options(options):
    _save_json(OPTIONS_FILE, options)


# --- AI機能（Groq API：無料で利用可能） ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
USE_AI = bool(GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _call_ai(system_prompt, user_message):
    """Groq APIを呼び出して応答テキストを返す（無料）"""
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise Exception(f"AI API エラー ({e.code}): {error_body}")


# --- テンプレート生成エンジン ---

ACTIVITY_OPENERS_AM = [
    "午前中は{activity}を行った。",
    "午前中は{activity}に取り組んだ。",
    "午前は{activity}を実施。",
    "午前中は{activity}に取り組まれていた。",
]

ACTIVITY_OPENERS_PM = [
    "午後からは{activity}を行った。",
    "午後は{activity}に取り組んだ。",
    "午後からは{activity}を実施。",
    "午後からは{activity}に取り組まれていた。",
]

# 選択肢テキストをそのまま記録文に変換する汎用テンプレート
GENERIC_CONNECTORS = [
    "{text}。",
    "{text}様子が見られた。",
    "{text}場面が見られた。",
]


def generate_template(data):
    """テンプレートの組み合わせで記録文を生成する"""
    parts = []
    member_name = data.get("member_name", "").strip()

    am_activities = data.get("am_activities", [])
    am_behaviors = data.get("am_behaviors", [])
    am_memo = data.get("am_memo", "")
    pm_activities = data.get("pm_activities", [])
    pm_behaviors = data.get("pm_behaviors", [])
    pm_memo = data.get("pm_memo", "")
    impressions_list = data.get("impressions", [])
    general_memo = data.get("general_memo", "")

    # 利用者名ヘッダー
    if member_name:
        parts.append(f"利用者対応　{member_name}\n")

    # 午前
    if am_activities:
        activity_text = "・".join(am_activities)
        opener = random.choice(ACTIVITY_OPENERS_AM).format(activity=activity_text)
        parts.append(opener)

        for behavior in am_behaviors:
            connector = random.choice(GENERIC_CONNECTORS).format(text=behavior)
            parts.append(connector)

        if am_memo:
            parts.append(am_memo.rstrip("。") + "。")

    # 午後
    if pm_activities:
        activity_text = "・".join(pm_activities)
        opener = random.choice(ACTIVITY_OPENERS_PM).format(activity=activity_text)
        parts.append(opener)

        for behavior in pm_behaviors:
            connector = random.choice(GENERIC_CONNECTORS).format(text=behavior)
            parts.append(connector)

        if pm_memo:
            parts.append(pm_memo.rstrip("。") + "。")

    # 全体の印象
    for impression in impressions_list:
        parts.append(impression.rstrip("。") + "。")

    if general_memo:
        parts.append(general_memo.rstrip("。") + "。")

    result = "".join(parts)
    result = result.replace("。。", "。")
    return result


# --- AI生成エンジン ---

SYSTEM_PROMPT = """あなたはB型就労支援施設「メタゲーム明石」の支援記録を作成するアシスタントです。
スタッフが入力した構造化データから、自然で温かみのある支援記録文を生成してください。

## ルール
- 最初の行に「利用者対応　○○様」のヘッダーを必ず入れる（利用者名が提供された場合）
- 文体は「です・ます調」ではなく、記録体（「〜された」「〜していた」「〜の様子」）で書く
- 午前・午後の活動をそれぞれ段落で分けて書く
- 観察した様子や行動を具体的に記述する
- ポジティブな面を見つけて記録する（福祉的視点）
- 1記録あたり100〜200文字程度にまとめる（ヘッダー除く）
- 補足メモがある場合は、その内容を自然に文章に組み込む
- 毎回少しずつ表現を変えて、コピペ感が出ないようにする

## 記録例
利用者対応　I・M様
午前中はCANVAにて名札の制作を実施。基本的な操作方法の理解に少し時間がかかったが、その後はデザインを考えながらスムーズに進めることができていた。午後からはeスポーツを実施。1人で集中してプレイされていた。まだ緊張している様子で、表情が硬い印象を受けた。

利用者対応　T・M様
午前中は動画編集。落ち着いた様子で動画をリサーチしながら、イメージを膨らませつつ試行錯誤されている様子。午後からはゲームをいつも通り集中して楽しまれていた。新しい利用者さんが困っているときに話しかけて教えてあげるなど、思いやりのある行動が見かけられコミュニケーションをしっかり図ろうとされているところが伺えます。
"""


def generate_ai(data):
    """Gemini APIで自然な記録文を生成する"""
    member_name = data.get("member_name", "").strip()
    am_activities = data.get("am_activities", [])
    am_behaviors = data.get("am_behaviors", [])
    am_memo = data.get("am_memo", "")
    pm_activities = data.get("pm_activities", [])
    pm_behaviors = data.get("pm_behaviors", [])
    pm_memo = data.get("pm_memo", "")
    impressions_list = data.get("impressions", [])
    general_memo = data.get("general_memo", "")

    user_message = f"""以下の情報から支援記録文を1つ生成してください。

■ 利用者名: {member_name if member_name else '未入力'}
■ 午前の活動: {', '.join(am_activities) if am_activities else '特になし'}
■ 午前の様子: {', '.join(am_behaviors) if am_behaviors else '特になし'}
■ 午前の補足メモ: {am_memo if am_memo else 'なし'}
■ 午後の活動: {', '.join(pm_activities) if pm_activities else '特になし'}
■ 午後の様子: {', '.join(pm_behaviors) if pm_behaviors else '特になし'}
■ 午後の補足メモ: {pm_memo if pm_memo else 'なし'}
■ 全体の印象: {', '.join(impressions_list) if impressions_list else '特になし'}
■ その他メモ: {general_memo if general_memo else 'なし'}

記録文のみを出力してください。前置きや説明は不要です。"""

    return _call_ai(SYSTEM_PROMPT, user_message)


# =====================
# ルーティング
# =====================

@app.route("/")
def index():
    options = load_options()
    return render_template(
        "index.html",
        activities=options["activities"],
        behaviors=options["behaviors"],
        impressions=options["impressions"],
        members=load_members(),
        use_ai=USE_AI,
    )


@app.route("/admin")
def admin():
    options = load_options()
    return render_template(
        "admin.html",
        options=options,
        members=load_members(),
    )


# --- 利用者 API ---

@app.route("/members", methods=["GET"])
def get_members():
    return jsonify(load_members())


@app.route("/members", methods=["POST"])
def add_member():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "名前を入力してください"}), 400
    members = load_members()
    if name in members:
        return jsonify({"success": False, "error": "既に登録されています"}), 400
    members.append(name)
    members.sort()
    save_members(members)
    return jsonify({"success": True, "members": members})


@app.route("/members", methods=["DELETE"])
def delete_member():
    data = request.json
    name = data.get("name", "").strip()
    members = load_members()
    if name in members:
        members.remove(name)
        save_members(members)
    return jsonify({"success": True, "members": members})


# --- 選択肢 API ---

@app.route("/options", methods=["GET"])
def get_options():
    return jsonify(load_options())


@app.route("/options/<category>/add", methods=["POST"])
def add_option(category):
    """選択肢を追加する (category: activities / behaviors / impressions)"""
    options = load_options()
    if category not in options:
        return jsonify({"success": False, "error": "無効なカテゴリ"}), 400
    data = request.json
    value = data.get("value", "").strip()
    if not value:
        return jsonify({"success": False, "error": "内容を入力してください"}), 400
    if value in options[category]:
        return jsonify({"success": False, "error": "既に登録されています"}), 400
    options[category].append(value)
    save_options(options)
    return jsonify({"success": True, "options": options[category]})


@app.route("/options/<category>/delete", methods=["POST"])
def delete_option(category):
    """選択肢を削除する"""
    options = load_options()
    if category not in options:
        return jsonify({"success": False, "error": "無効なカテゴリ"}), 400
    data = request.json
    value = data.get("value", "").strip()
    if value in options[category]:
        options[category].remove(value)
        save_options(options)
    return jsonify({"success": True, "options": options[category]})


@app.route("/options/<category>/edit", methods=["POST"])
def edit_option(category):
    """選択肢を変更する"""
    options = load_options()
    if category not in options:
        return jsonify({"success": False, "error": "無効なカテゴリ"}), 400
    data = request.json
    old_value = data.get("old_value", "").strip()
    new_value = data.get("new_value", "").strip()
    if not new_value:
        return jsonify({"success": False, "error": "内容を入力してください"}), 400
    if old_value in options[category]:
        idx = options[category].index(old_value)
        options[category][idx] = new_value
        save_options(options)
    return jsonify({"success": True, "options": options[category]})


# --- 生成 API ---

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    try:
        text = generate_template(data)
        return jsonify({"success": True, "text": text})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- AIチェック API（クラウド版のみ） ---

CHECK_SYSTEM_PROMPT = """あなたはB型就労支援施設「メタゲーム明石」の支援記録を校正するアシスタントです。
入力された支援記録文を確認し、より自然で適切な文章に校正してください。

## 校正ルール
- 文法的な不自然さを修正する
- 「。。」のような重複表現を除去する
- 記録体（「〜された」「〜していた」「〜の様子」）で統一する
- 主語と述語の対応を確認する
- 同じ表現の繰り返しを避ける（言い換える）
- 文章の流れが自然になるようにする
- 意味を変えないこと（情報の追加・削除はしない）
- 「利用者対応　○○様」のヘッダー行はそのまま残す

## 出力形式
校正後の文章のみを出力してください。前置きや説明は不要です。
修正がない場合はそのまま返してください。"""


@app.route("/check", methods=["POST"])
def check_text():
    """生成された記録文をAIで校正する（APIキーがある場合のみ）"""
    if not USE_AI:
        return jsonify({"success": False, "error": "AI機能は利用できません"}), 400

    data = request.json
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "校正するテキストがありません"}), 400

    try:
        checked_text = _call_ai(
            CHECK_SYSTEM_PROMPT,
            f"以下の支援記録文を校正してください。\n\n{text}",
        )
        return jsonify({"success": True, "text": checked_text})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    # 初回起動時にデフォルト選択肢を保存
    if not OPTIONS_FILE.exists():
        save_options(DEFAULT_OPTIONS)

    print("=" * 50)
    print("  CreativeLog - 支援記録アシスタント")
    print("  メタゲーム明石")
    print("=" * 50)
    if USE_AI:
        print("  モード: AI生成（Gemini API・無料）")
    else:
        print("  モード: テンプレート生成（APIキー不要）")
        print("  ※ GEMINI_API_KEY を設定するとAI生成に切り替わります")
    print()
    print("  記録入力: http://localhost:5000")
    print("  管理画面: http://localhost:5000/admin")
    print("  終了するには Ctrl+C を押してください")
    print("=" * 50)
    app.run(debug=True, port=5000)
