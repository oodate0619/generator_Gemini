"""
ブログ記事ジェネレーター - Streamlit + Gemini API 版
社内・学習用サンプル
"""
import streamlit as st
from google import genai
from google.genai import types
import json
import re
from datetime import datetime

# ================================================================
# ページ設定
# ================================================================
st.set_page_config(
    page_title="ブログ記事ジェネレーター",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ================================================================
# カラー定数
# ================================================================
C = {
    "bg": "#f5f0e6",
    "panel": "#fbf8f1",
    "ink": "#1a1f2c",
    "ink_soft": "#4a5060",
    "rule": "#d9d0bd",
    "accent": "#a8492c",
    "accent_soft": "#e5d8c7",
    "ok": "#3a6d4f",
}

# 使用モデル：無料枠で動く Gemini 2.5 Flash
MODEL_NAME = "gemini-2.5-flash"

# ================================================================
# カスタムCSS
# ================================================================
st.markdown(f"""
<style>
.stApp {{ background-color: {C["bg"]}; }}
.main .block-container {{
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 820px;
}}
h1, h2, h3, h4 {{
    font-family: "Hiragino Mincho ProN", "Yu Mincho", "YuMincho", serif !important;
    color: {C["ink"]} !important;
    letter-spacing: -0.01em;
}}
body, .stMarkdown, .stTextInput, .stTextArea, .stSelectbox {{
    font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif;
    color: {C["ink"]};
}}
.stButton > button {{
    border-radius: 0 !important;
    background-color: {C["ink"]} !important;
    color: {C["panel"]} !important;
    border: none !important;
    padding: 0.7rem 1.5rem !important;
    font-weight: 500 !important;
    width: 100%;
    transition: all 0.2s;
}}
.stButton > button:hover {{
    background-color: {C["accent"]} !important;
    color: {C["panel"]} !important;
}}
.stButton > button:disabled {{
    background-color: {C["rule"]} !important;
    color: {C["ink_soft"]} !important;
}}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {{
    border-radius: 0 !important;
    border: 1px solid {C["rule"]} !important;
    background-color: {C["panel"]} !important;
}}
hr {{ border-color: {C["rule"]}; margin: 2rem 0; }}
.article-body {{
    background-color: {C["panel"]};
    border: 1px solid {C["rule"]};
    padding: 2.5rem;
    line-height: 1.85;
}}
.article-body h2 {{
    border-left: 4px solid {C["accent"]};
    padding-left: 0.8rem;
    font-size: 1.5rem !important;
    margin-top: 2rem !important;
    margin-bottom: 1rem !important;
}}
.article-body h3 {{
    font-size: 1.15rem !important;
    margin-top: 1.5rem !important;
}}
.article-body p {{ margin-bottom: 1.1rem; }}
.article-body strong {{
    background: linear-gradient(transparent 60%, {C["accent_soft"]} 60%);
    padding: 0 2px;
    font-weight: 700;
}}
.article-body em {{ color: {C["accent"]}; font-style: italic; }}
.article-body ul, .article-body ol {{ margin: 1rem 0 1.4rem 1.5rem; }}
.title-card {{
    background-color: {C["panel"]};
    border: 1px solid {C["rule"]};
    padding: 1.5rem;
    margin-bottom: 0.8rem;
}}
.title-card-num {{
    color: {C["accent"]};
    font-family: "Hiragino Mincho ProN", serif;
    font-size: 1.5rem;
    font-weight: 700;
}}
.title-card-title {{
    font-family: "Hiragino Mincho ProN", serif;
    font-size: 1.15rem;
    font-weight: 600;
    margin-top: 0.3rem;
}}
.title-card-angle {{
    font-family: monospace;
    font-size: 0.75rem;
    color: {C["ink_soft"]};
    margin-top: 0.4rem;
}}
.meta-bar {{
    background-color: {C["panel"]};
    border: 1px solid {C["rule"]};
    padding: 0.8rem 1.2rem;
    font-family: monospace;
    font-size: 0.7rem;
    color: {C["ink_soft"]};
    letter-spacing: 1px;
}}
.section-head {{
    font-family: monospace;
    font-size: 0.7rem;
    letter-spacing: 2px;
    color: {C["accent"]};
    font-weight: 600;
    text-transform: uppercase;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid {C["rule"]};
}}
.demo-badge {{
    display: inline-block;
    background-color: {C["accent_soft"]};
    color: {C["accent"]};
    font-family: monospace;
    font-size: 0.65rem;
    padding: 0.1rem 0.5rem;
    margin-left: 0.5rem;
    letter-spacing: 1px;
}}
.footer {{
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid {C["rule"]};
    font-family: monospace;
    font-size: 0.7rem;
    color: {C["ink_soft"]};
    letter-spacing: 1px;
}}
</style>
""", unsafe_allow_html=True)


# ================================================================
# Gemini クライアント取得
# ================================================================
@st.cache_resource
def get_client():
    api_key = None
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        pass
    if not api_key:
        st.error(
            "**Gemini API キーが設定されていません。**\n\n"
            "1. [aistudio.google.com](https://aistudio.google.com/app/apikey) で API キー発行（無料、クレカ不要）\n"
            "2. Streamlit Cloud の場合：App → Settings → Secrets で\n"
            "   `GEMINI_API_KEY = \"AI...\"` を追加\n"
            "3. ローカル実行の場合：`.streamlit/secrets.toml` に同じ内容を書く"
        )
        st.stop()
    return genai.Client(api_key=api_key)


# ================================================================
# セッション状態初期化
# ================================================================
def init_state():
    defaults = {
        "step": 1,
        "titles": [],
        "selected_title": None,
        "article_html": "",
        "cover_svg": "",
        "image_prompt": "",
        "has_generated_image": False,
        "mock_sent": False,
        "form": {
            "keyword": "",
            "persona": "",
            "char_count": 4000,
            "style": "です・ます",
            "faq": False,
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset():
    for k in [
        "step", "titles", "selected_title", "article_html",
        "cover_svg", "image_prompt", "has_generated_image", "mock_sent"
    ]:
        if k in st.session_state:
            del st.session_state[k]
    init_state()


init_state()


# ================================================================
# プレースホルダー SVG カバー生成
# ================================================================
def build_placeholder_svg(title: str, keyword: str) -> str:
    safe_title = (title or "").replace("&", "&amp;").replace("<", "&lt;")
    safe_kw = (keyword or "").replace("&", "&amp;").replace("<", "&lt;")
    lines = []
    cur = ""
    for ch in safe_title:
        cur += ch
        if len(cur) >= 18:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    lines = lines[:2]
    line_els = "".join(
        f'<text x="60" y="{180 + i*56}" font-family="serif" '
        f'font-size="40" font-weight="700" fill="#fbf8f1">{l}</text>'
        for i, l in enumerate(lines)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="100%" height="auto">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1a1f2c"/>
      <stop offset="1" stop-color="#a8492c"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#g)"/>
  <rect x="40" y="40" width="1120" height="550" fill="none" stroke="#fbf8f1" stroke-width="1" opacity="0.4"/>
  <text x="60" y="100" font-family="monospace" font-size="14" letter-spacing="2" fill="#fbf8f1" opacity="0.7">KEYWORD / {safe_kw.upper()}</text>
  {line_els}
  <text x="60" y="560" font-family="monospace" font-size="12" letter-spacing="1" fill="#fbf8f1" opacity="0.5">PLACEHOLDER · 本番では画像生成APIに差し替え</text>
</svg>"""


# ================================================================
# Gemini API 呼び出し
# ================================================================
def call_gemini(prompt: str, max_tokens: int = 4000) -> str:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
        ),
    )
    return response.text or ""


def generate_titles(form: dict) -> list:
    prompt = f"""あなたはプロのSEOブログ編集者です。以下の条件で、日本語ブログ記事のタイトル案を5つ生成してください。

【キーワード】{form["keyword"]}
【書き手について】{form["persona"] or "指定なし"}
【文体】{form["style"]}
【目標文字数】{form["char_count"]}文字
【FAQセクション】{"あり" if form["faq"] else "なし"}

要件：
- 各タイトルは28〜42文字程度
- クリックされやすく、検索意図に応える
- 過度な煽り・誇張は避ける
- 5案それぞれ異なる切り口（How-to系、比較系、体験談系、リスト系、Q&A系など）

出力は以下のJSON形式のみ。コードブロック記号や説明文は一切不要：
{{"titles":[{{"title":"...","angle":"..."}},{{"title":"...","angle":"..."}},{{"title":"...","angle":"..."}},{{"title":"...","angle":"..."}},{{"title":"...","angle":"..."}}]}}"""

    raw = call_gemini(prompt, max_tokens=2000)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    parsed = json.loads(cleaned)
    return parsed["titles"]


def generate_article(form: dict, title: dict) -> str:
    prompt = f"""あなたはプロの日本語ライターです。以下の条件でブログ記事を執筆してください。

【タイトル】{title["title"]}
【切り口】{title["angle"]}
【キーワード】{form["keyword"]}
【書き手の背景】{form["persona"] or "指定なし"}
【文体】{form["style"]}
【目標文字数】{form["char_count"]}文字（指示の1.5〜2倍程度を目安に長めに書いてOK）
【FAQ】{"末尾に「よくある質問」セクションをh2で追加し、Q&Aを3〜4つ" if form["faq"] else "FAQは不要"}

要件：
- WordPressブロックエディタで使えるHTMLで出力
- 使えるタグ：<h2>, <h3>, <p>, <strong>, <em>, <ul>, <li>
- 見出し（h2）は3〜5個、必要に応じてh3を含める
- 構成：導入文(p) → 本文（複数h2セクション）→ まとめ(h2)
- 経験を装った虚構やハルシネーションを避け、事実ベースで書く
- 「いかがでしたか」など定型的なAI臭い結びを避ける

出力はHTMLのみ。コードブロック記号、<html>/<body>タグ、説明文は不要。<h2>から始めてください。"""

    raw = call_gemini(prompt, max_tokens=8000)
    cleaned = re.sub(r"^```(?:html)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    return cleaned


def generate_image_svg(form: dict, title: dict, image_prompt: str) -> str:
    prompt = f"""あなたはブログ記事用のSVG図解を作るデザイナーです。以下の指示で、記事のヘッダーに使える図解SVGを作成してください。

【記事タイトル】{title["title"]}
【キーワード】{form["keyword"]}
【作りたい図解の内容】{image_prompt}

デザイン要件：
- viewBox="0 0 1200 630" のSVG
- 背景：#f5f0e6
- メインインク：#1a1f2c、アクセント：#a8492c、セカンダリ：#3a6d4f（必要時）
- フォント指定：font-family="serif"
- 日本語テキスト含む
- 図解として情報を伝える：ボックス、矢印、アイコン的な幾何形、シンプルな線画
- 写実的なイラストではなく「インフォグラフィック」風
- 2〜5要素程度のシンプル構成
- 全体に余白を取り、洗練された印象に

出力は <svg> から </svg> までのSVGコードのみ。コードブロック記号・説明文は不要。"""

    raw = call_gemini(prompt, max_tokens=4000)
    m = re.search(r"<svg[\s\S]*?</svg>", raw, re.IGNORECASE)
    if not m:
        raise ValueError("SVGの抽出に失敗しました")
    return m.group(0)


# ================================================================
# レンダリング: ヘッダー
# ================================================================
st.markdown(
    f'<div style="font-family: monospace; font-size: 11px; '
    f'letter-spacing: 2px; color: {C["accent"]};">'
    f'INTERNAL SAMPLE · v0.2 · STREAMLIT × GEMINI</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<h1 style="margin-top: 0.5rem; font-size: 2.5rem;">'
    f'ブログ記事ジェネレーター<span style="color: {C["accent"]};">.</span></h1>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<p style="color: {C["ink_soft"]}; font-size: 0.9rem; max-width: 540px;">'
    f'キーワード → タイトル候補 → 記事 → 図解 → WordPress用エクスポートまでの社内用サンプル。'
    f'Gemini API（無料枠）で動作。</p>',
    unsafe_allow_html=True,
)

# ================================================================
# ステップインジケーター
# ================================================================
step_labels = ["入力", "選定", "生成", "出力"]
cols = st.columns(4)
for i, (col, label) in enumerate(zip(cols, step_labels), start=1):
    is_active = st.session_state.step == i
    is_done = st.session_state.step > i
    color = C["ok"] if is_done else (C["ink"] if is_active else C["ink_soft"])
    weight = 700 if is_active else 400
    mark = "✓" if is_done else str(i)
    col.markdown(
        f'<div style="text-align: left; padding: 1rem 0;">'
        f'<div style="display:inline-block; width:28px; height:28px; '
        f'border:1px solid {color}; background-color:{color if (is_done or is_active) else "transparent"}; '
        f'color:{C["panel"] if (is_done or is_active) else color}; '
        f'text-align:center; line-height:28px; font-family:monospace; '
        f'font-size:0.75rem; margin-right:0.6rem;">{mark}</div>'
        f'<span style="font-family:monospace; font-size:0.7rem; '
        f'letter-spacing:1px; color:{color};">STEP {i}</span><br>'
        f'<span style="font-size:0.9rem; color:{color}; font-weight:{weight}; '
        f'margin-left:2.4rem;">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")


# ================================================================
# STEP 1: 入力フォーム
# ================================================================
if st.session_state.step == 1:
    f = st.session_state.form

    st.markdown('<div class="section-head">01 / キーワード *</div>', unsafe_allow_html=True)
    f["keyword"] = st.text_input(
        "キーワード",
        value=f["keyword"],
        placeholder="例：在宅ワーク 効率化 30代主婦",
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-head">02 / あなたについて（任意）</div>', unsafe_allow_html=True)
    f["persona"] = st.text_area(
        "ペルソナ",
        value=f["persona"],
        placeholder="例：愛猫に邪魔されながら働く30代フリーランス。10年のWeb制作経験あり。",
        height=100,
        label_visibility="collapsed",
    )
    st.caption("書き手の背景・経験を入れると記事に深みが出ます。固有文体（関西弁等）の指定もここに。")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="section-head">03 / 文字数 *</div>', unsafe_allow_html=True)
        f["char_count"] = st.selectbox(
            "目標文字数",
            options=[2000, 3000, 4000, 6000, 8000],
            index=[2000, 3000, 4000, 6000, 8000].index(f["char_count"]),
            format_func=lambda x: f"{x}文字",
            label_visibility="collapsed",
        )
        st.caption("AIは指示文字数より少なめに。希望の1.5〜2倍指定が安全。")

    with col2:
        st.markdown('<div class="section-head">04 / 文体</div>', unsafe_allow_html=True)
        f["style"] = st.radio(
            "文体",
            options=["だ・である", "です・ます", "カジュアル", "指定なし"],
            index=["だ・である", "です・ます", "カジュアル", "指定なし"].index(f["style"]),
            label_visibility="collapsed",
        )

    with col3:
        st.markdown('<div class="section-head">05 / 追加オプション</div>', unsafe_allow_html=True)
        f["faq"] = st.toggle("FAQ（よくある質問）", value=f["faq"])
        st.caption("「〜の方法」系で◎、How-to系で○。")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("✨ タイトル案を生成する", disabled=not f["keyword"].strip(), type="primary"):
        with st.spinner("タイトルを考えています..."):
            try:
                titles = generate_titles(f)
                st.session_state.titles = titles
                st.session_state.step = 2
                st.rerun()
            except Exception as e:
                st.error(f"タイトル生成に失敗しました：{e}")


# ================================================================
# STEP 2: タイトル選定
# ================================================================
elif st.session_state.step == 2:
    col_a, col_b = st.columns([4, 1])
    with col_a:
        st.markdown(
            f'<p style="color:{C["ink_soft"]}; font-size:0.9rem;">'
            f'5つのタイトル案ができました。記事にしたい1つを選んでください。</p>',
            unsafe_allow_html=True,
        )
    with col_b:
        if st.button("← 入力に戻る", key="back_to_1"):
            st.session_state.step = 1
            st.rerun()

    for i, t in enumerate(st.session_state.titles, start=1):
        with st.container():
            st.markdown(
                f'<div class="title-card">'
                f'<span class="title-card-num">{i:02d}</span>'
                f'<div class="title-card-title">{t["title"]}</div>'
                f'<div class="title-card-angle">切り口 · {t["angle"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"これで記事を書く →", key=f"select_{i}"):
                st.session_state.selected_title = t
                st.session_state.cover_svg = build_placeholder_svg(
                    t["title"], st.session_state.form["keyword"]
                )
                st.session_state.step = 3
                with st.spinner("記事を執筆中... (20〜60秒)"):
                    try:
                        html = generate_article(st.session_state.form, t)
                        st.session_state.article_html = html
                        st.session_state.step = 4
                        st.rerun()
                    except Exception as e:
                        st.error(f"記事生成に失敗しました：{e}")
                        st.session_state.step = 2


# ================================================================
# STEP 3: 記事生成中
# ================================================================
elif st.session_state.step == 3:
    st.info("記事を執筆中...")


# ================================================================
# STEP 4: 記事プレビュー + 画像生成 + WordPress仮ボタン
# ================================================================
elif st.session_state.step == 4:
    f = st.session_state.form
    title = st.session_state.selected_title

    st.markdown(
        f'<div class="meta-bar">'
        f'STATUS · COMPLETED &nbsp;·&nbsp; '
        f'STYLE · {f["style"]} &nbsp;·&nbsp; '
        f'TARGET · {f["char_count"]}字 &nbsp;·&nbsp; '
        f'FAQ · {"ON" if f["faq"] else "OFF"}'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_x, col_y = st.columns([1, 1])
    with col_x:
        if st.button("🔄 記事を再生成", key="regen"):
            with st.spinner("再生成中..."):
                try:
                    html = generate_article(f, title)
                    st.session_state.article_html = html
                    st.rerun()
                except Exception as e:
                    st.error(f"再生成失敗：{e}")
    with col_y:
        if st.button("最初からやり直す", key="reset"):
            reset()
            st.rerun()

    st.markdown('<div class="section-head">COVER IMAGE / 図解</div>', unsafe_allow_html=True)
    st.markdown(st.session_state.cover_svg, unsafe_allow_html=True)

    with st.container():
        st.markdown(
            f'<div style="background-color:{C["panel"]}; border:1px solid {C["rule"]}; '
            f'padding:1.2rem; margin-top:1rem;">'
            f'<div style="font-weight:600; font-size:0.95rem; margin-bottom:0.3rem;">🎨 図解を生成する</div>'
            f'<div style="font-size:0.8rem; color:{C["ink_soft"]}; line-height:1.6;">'
            f'どんな図解を作るか具体的に書いてください。例：「3ステップの流れ図」「メリット3点をアイコンで」など。<br>'
            f'<span style="font-family:monospace; font-size:0.7rem;">'
            f'※ サンプルでは Gemini が SVG 図解を生成。本番で写真風が必要なら Imagen API へ差し替え可能。</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    st.session_state.image_prompt = st.text_area(
        "画像の指示",
        value=st.session_state.image_prompt,
        placeholder="例：在宅ワーク効率化の3ステップを矢印でつないだフロー図。各ステップにアイコン的な図形を添えて。",
        height=80,
        label_visibility="collapsed",
    )

    if st.button(
        "✨ 画像を生成する" if not st.session_state.has_generated_image else "🔄 画像を再生成する",
        disabled=not st.session_state.image_prompt.strip(),
        key="gen_image",
    ):
        with st.spinner("図解を作成中..."):
            try:
                svg = generate_image_svg(f, title, st.session_state.image_prompt)
                st.session_state.cover_svg = svg
                st.session_state.has_generated_image = True
                st.rerun()
            except Exception as e:
                st.error(f"画像生成に失敗しました：{e}")

    st.markdown('<div class="section-head">ARTICLE PREVIEW</div>', unsafe_allow_html=True)

    st.markdown(
        f'<div class="article-body">'
        f'<h1 style="font-size:2rem; border-bottom:2px solid {C["ink"]}; '
        f'padding-bottom:1rem; margin-bottom:1.5rem;">{title["title"]}</h1>'
        f'{st.session_state.article_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col_p, col_w = st.columns(2)
    with col_p:
        with st.expander("📄 記事のプレビューを見る（読者視点）"):
            st.markdown(st.session_state.cover_svg, unsafe_allow_html=True)
            st.markdown(
                f'<div class="article-body" style="margin-top:1rem;">'
                f'<h1 style="font-size:1.8rem;">{title["title"]}</h1>'
                f'<div style="font-family:monospace; font-size:0.7rem; color:{C["ink_soft"]}; '
                f'border-bottom:1px solid {C["rule"]}; padding-bottom:0.5rem; margin-bottom:1rem;">'
                f'{datetime.now().strftime("%Y年%m月%d日")} · {f["keyword"]}</div>'
                f'{st.session_state.article_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col_w:
        if st.button(
            "📤 WordPressに下書き保存（仮）" if not st.session_state.mock_sent
            else "✓ 下書き保存しました（仮）",
            key="wp_save",
        ):
            st.session_state.mock_sent = True
            st.rerun()

    if st.session_state.mock_sent:
        with st.expander("📋 本番ではこの内容が送信されます", expanded=True):
            st.code(
                f'''POST /wp-json/wp/v2/posts
Authorization: Bearer <APP_PASSWORD>
Content-Type: application/json

{{
  "title": "{title["title"]}",
  "status": "draft",
  "content": "<HTML本文 {len(st.session_state.article_html)}文字>",
  "featured_media": <画像アップロード後のID>
}}''',
                language="http",
            )

    st.markdown('<div class="section-head">EXPORT</div>', unsafe_allow_html=True)

    col_h, col_t = st.columns(2)
    with col_h:
        wp_html = f'<!-- title: {title["title"]} -->\n\n{st.session_state.article_html}'
        st.download_button(
            "📥 WordPress用HTMLをダウンロード",
            data=wp_html,
            file_name="article.html",
            mime="text/html",
        )
    with col_t:
        plain = re.sub(r"<[^>]+>", "\n", st.session_state.article_html)
        plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
        st.download_button(
            "📥 プレーンテキストをダウンロード",
            data=plain,
            file_name="article.txt",
            mime="text/plain",
        )

    with st.expander("クリップボードコピー用（手動コピー）"):
        st.text_area(
            "WordPress用HTML",
            value=wp_html,
            height=200,
        )


# ================================================================
# フッター
# ================================================================
img_status = "gemini svg generated" if st.session_state.get("has_generated_image") else "placeholder svg"
st.markdown(
    f'<div class="footer">'
    f'MODEL · {MODEL_NAME} &nbsp;&nbsp; '
    f'STORAGE · session only &nbsp;&nbsp; '
    f'IMAGES · {img_status} &nbsp;&nbsp; '
    f'WP · mock'
    f'</div>',
    unsafe_allow_html=True,
)
