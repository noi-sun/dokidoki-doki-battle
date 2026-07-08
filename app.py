import streamlit as st
from PIL import Image
import hashlib
import time
import random
import numpy as np
import cv2
import io
import json
import os
import html

# --- データ定義: 属性ごとの技リストとアイコン ---
ELEMENTS = {
    "火": {"icon": "🔥", "color": "#FF4B4B", "text_color": "#FFC1C1"},
    "水": {"icon": "💧", "color": "#007BFF", "text_color": "#C1E0FF"},
    "草": {"icon": "🌿", "color": "#28A745", "text_color": "#C1FFC1"},
    "無": {"icon": "🌟", "color": "#A0A0A0", "text_color": "#E5E5E5"}
}

SKILLS = {
    "火": [
        {"name": "プロミネンスバースト", "mult": 1.5, "msg": "猛烈な火炎が土器の窯のように相手を包み込む！"},
        {"name": "フレアストライク", "mult": 1.2, "msg": "赤々とした劫火が吹き荒れる！"}
    ],
    "水": [
        {"name": "ハイドロボルテックス", "mult": 1.5, "msg": "渦巻く激流が相手を押し流す！"},
        {"name": "アクアブラスト", "mult": 1.2, "msg": "清らかなる激流が弾け飛ぶ！"}
    ],
    "草": [
        {"name": "ギガドレインソーン", "mult": 1.4, "msg": "蔓草が絡みつき、相手のエネルギーを吸収する！"},
        {"name": "ソーラーバースト", "mult": 1.7, "msg": "凝縮された大自然 of 陽光を一気に放つ！"}
    ],
    "無": [
        {"name": "コズミックノヴァ", "mult": 1.4, "msg": "属性を超越した無属性の超エネルギー波！"},
        {"name": "クラッシュインパクト", "mult": 1.2, "msg": "土器の質量を活かした強力な体当たり！"}
    ]
}

# CPU用エネミー土器のプリセット
CPU_PRESETS = [
    {
        "name": "伝説の火焔型土器",
        "element": "火",
        "similarity": 95,
        "hp": 390,
        "max_hp": 390,
        "atk": 65,
        "def": 35,
        "desc": "燃え盛る炎のような突起を持つ、縄文時代中期の傑作土器。"
    },
    {
        "name": "水煙柄深鉢土器",
        "element": "水",
        "similarity": 88,
        "hp": 376,
        "max_hp": 376,
        "atk": 52,
        "def": 48,
        "desc": "湧き上がる水や煙を模したとされる美しい隆起線を持つ土器。"
    },
    {
        "name": "遮光器土偶",
        "element": "無",
        "similarity": 92,
        "hp": 384,
        "max_hp": 384,
        "atk": 45,
        "def": 60,
        "desc": "不思議なゴーグル型をした巨大な目を持ち、防御力の極めて高い土偶。"
    },
    {
        "name": "弥生式土器（壺型）",
        "element": "草",
        "similarity": 82,
        "hp": 364,
        "max_hp": 364,
        "atk": 55,
        "def": 40,
        "desc": "シンプルながら洗練されたフォルムを持つ、実用性に優れた農耕社会の土器。"
    }
]

# --- ランキング管理 (JSON永続化) ---
RANKINGS_FILE = "clay_pot_rankings.json"

def load_rankings():
    if not os.path.exists(RANKINGS_FILE):
        return []
    try:
        with open(RANKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_rankings(rankings):
    try:
        with open(RANKINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(rankings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def register_to_ranking(name, element, similarity):
    # 初期名以外かつ意味のある名前のみ登録
    if not name:
        return
    rankings = load_rankings()
    exists = False
    for item in rankings:
        if item["name"] == name:
            # 良い類似度なら上書き
            if similarity > item["similarity"]:
                item["similarity"] = similarity
                item["element"] = element
            exists = True
            break
    if not exists:
        rankings.append({
            "name": name,
            "element": element,
            "similarity": similarity,
            "wins": 0,
            "date": time.strftime("%Y-%m-%d %H:%M")
        })
    save_rankings(rankings)

def increment_win_count(name):
    rankings = load_rankings()
    for item in rankings:
        if item["name"] == name:
            item["wins"] = item.get("wins", 0) + 1
            break
    save_rankings(rankings)

# --- 相性チェック関数 ---
def get_compatibility(atk_elem, def_elem):
    chart = {
        ("火", "草"): 1.5, ("火", "水"): 0.7,
        ("草", "水"): 1.5, ("草", "火"): 0.7,
        ("水", "火"): 1.5, ("水", "草"): 0.7
    }
    return chart.get((atk_elem, def_elem), 1.0)

# --- 基準土器の輪郭生成 ---
def get_base_pot_contour():
    points = []
    # 左側の輪郭 (上から下へ)
    for y in range(0, 301, 10):
        t = y / 300.0
        if t < 0.1:
            w = 80 - t * 200        # 口元の広がり (80 から 60 へ)
        elif t < 0.4:
            w = 60 - (t - 0.1) * 50  # 首元のくびれ (60 から 45 へ)
        elif t < 0.8:
            w = 45 + (t - 0.4) * 80  # 胴体の膨らみ (45 から 77 へ)
        else:
            w = 77 - (t - 0.8) * 185 # 底のすぼまり (77 から 40 へ)
        points.append([100 - int(w), y])
    
    # 右側の輪郭
    for y in range(300, -1, -10):
        t = y / 300.0
        if t < 0.1:
            w = 80 - t * 200
        elif t < 0.4:
            w = 60 - (t - 0.1) * 50
        elif t < 0.8:
            w = 45 + (t - 0.4) * 80
        else:
            w = 77 - (t - 0.8) * 185
        points.append([100 + int(w), y])
        
    return np.array(points, dtype=np.int32)

# --- 基準シルエットの画像生成 ---
def get_base_pot_image():
    img = np.zeros((330, 220, 3), dtype=np.uint8)
    img[:] = (30, 26, 24) # ダーク和風背景色 (BGR)
    
    contour = get_base_pot_contour()
    shifted_contour = contour + [10, 15]
    
    # 塗りつぶし
    cv2.drawContours(img, [shifted_contour], -1, (90, 140, 210), -1) 
    # 輪郭線
    cv2.drawContours(img, [shifted_contour], -1, (40, 60, 110), 3) 
    # 装飾的な横線
    for y in [100, 150, 180, 230]:
        t = (y - 15) / 300.0
        if t < 0.1: w = 80 - t * 200
        elif t < 0.4: w = 60 - (t - 0.1) * 50
        elif t < 0.8: w = 45 + (t - 0.4) * 80
        else: w = 77 - (t - 0.8) * 185
        
        cv2.line(img, (110 - int(w) + 10, y), (110 + int(w) - 10, y), (40, 60, 110), 2)
        
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

# --- 画像類似度の計算ロジック ---
def analyze_shape(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return 0, None
        
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    h, w = thresh.shape
    border_pixels = np.concatenate([thresh[0, :], thresh[h-1, :], thresh[:, 0], thresh[:, w-1]])
    if np.mean(border_pixels) > 127:
        thresh = cv2.bitwise_not(thresh)
        
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0, img_bgr
        
    user_contour = max(contours, key=cv2.contourArea)
    
    base_contour = get_base_pot_contour()
    # cv2.CONTOUR_MATCH_I1エラー対策で direct 数値 1 を指定
    match_val = cv2.matchShapes(base_contour, user_contour, 1, 0.0)
    
    similarity = int(np.exp(-2.5 * match_val) * 100)
    similarity = max(5, min(100, similarity))
    
    vis_img = img_bgr.copy()
    cv2.drawContours(vis_img, [user_contour], -1, (46, 204, 113), 6)
    
    vis_rgb = cv2.cvtColor(vis_img, cv2.COLOR_BGR2RGB)
    vis_pil = Image.fromarray(vis_rgb)
    
    return similarity, vis_pil

# --- 色属性抽出ロジック ---
def analyze_color(img_bytes):
    nparr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return "無", {"red": 25, "blue": 25, "green": 25, "none": 25}
        
    small_bgr = cv2.resize(img_bgr, (100, 100))
    hsv = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2HSV)
    
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    
    color_mask = (s > 45) & (v > 40)
    colored_pixels = np.sum(color_mask)
    
    red_mask = color_mask & ((h < 10) | (h > 170))
    green_mask = color_mask & ((h >= 35) & (h <= 85))
    blue_mask = color_mask & ((h >= 90) & (h <= 145))
    
    r_count = np.sum(red_mask)
    g_count = np.sum(green_mask)
    b_count = np.sum(blue_mask)
    
    if colored_pixels > 80:
        p_red = (r_count / colored_pixels) * 100
        p_green = (g_count / colored_pixels) * 100
        p_blue = (b_count / colored_pixels) * 100
    else:
        p_red = p_green = p_blue = 0.0
        
    p_none = 100.0 - (p_red + p_green + p_blue)
    
    threshold = 30.0
    ratios = [("火", p_red), ("草", p_green), ("水", p_blue)]
    valid_elements = [x for x in ratios if x[1] > threshold]
    
    if valid_elements:
        valid_elements.sort(key=lambda x: x[1], reverse=True)
        elem = valid_elements[0][0]
    else:
        elem = "無"
        
    return elem, {
        "red": p_red,
        "green": p_green,
        "blue": p_blue,
        "none": p_none
    }

# --- ステータス生成 ---
def get_status_from_image(image_file, name=None):
    img_bytes = image_file.getvalue()
    img_hash = hashlib.md5(img_bytes).hexdigest()
    
    pil_img = Image.open(image_file)
    
    similarity, contour_img = analyze_shape(img_bytes)
    if contour_img is None:
        contour_img = pil_img
        
    element, color_ratios = analyze_color(img_bytes)
    
    hp = 200 + (similarity * 2)
    
    atk_base = 35
    def_base = 25
    
    if element == "火":
        atk_base += int(color_ratios["red"] * 0.4)
    elif element == "水":
        atk_base += int(color_ratios["blue"] * 0.2)
        def_base += int(color_ratios["blue"] * 0.2)
    elif element == "草":
        hp += int(color_ratios["green"] * 1.5)
        atk_base += int(color_ratios["green"] * 0.2)
    else: # 無
        def_base += int(color_ratios["none"] * 0.4)
        
    atk = atk_base + (similarity // 4)
    dfn = def_base + (similarity // 4)
    
    if name is None or name.strip() == "":
        name = f"ドキ土器_{img_hash[:4].upper()}"
        
    meta = ELEMENTS[element]
    icon = meta["icon"]
    color = meta["color"]
    
    # 永続ランキングに自動登録
    register_to_ranking(name, element, similarity)
    
    return {
        "name": name,
        "element": element,
        "icon": icon,
        "color": color,
        "hp": hp,
        "max_hp": hp,
        "atk": atk,
        "def": dfn,
        "image": pil_img,
        "contour_image": contour_img,
        "similarity": similarity,
        "color_ratios": color_ratios,
        "custom": True
    }

# --- ページ設定とCSS注入 ---
st.set_page_config(page_title="ドキドキ粘土土器バトル", layout="wide", page_icon="🏺")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&family=Zen+Maru+Gothic:wght@500;700&display=swap');
    
    .stApp {
        background-color: #121216;
        color: #f7f7f9;
        font-family: 'Zen Maru Gothic', 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 3rem;
        background: linear-gradient(135deg, #e67e22, #f1c40f, #e74c3c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-weight: 700;
        margin-bottom: 0px;
    }
    .sub-title {
        text-align: center;
        color: #a0a0a5;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .status-card {
        background: rgba(30, 30, 38, 0.7);
        border: 2px solid #3f3f4e;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(8px);
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    .status-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(230, 126, 34, 0.2);
        border-color: #e67e22;
    }
    
    .element-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    div[data-testid="stProgress"] > div > div > div {
        background-image: linear-gradient(135deg, #e74c3c, #f1c40f);
    }
    
    table {
        background-color: rgba(30, 30, 38, 0.5);
        color: #fff;
        border-radius: 8px;
        border-collapse: collapse;
    }
    
    th {
        background-color: #2b2b36 !important;
        color: #e67e22 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<p class='main-title'>🏺 粘土土器バトル！DokiDoki CLAY ARENA</p>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>作成した粘土土器の写真をアップロードしてバトルするゲーム！基準モデルに近いほど強く、色によって属性が決まります。</p>", unsafe_allow_html=True)

# 基準モデルセクション
with st.sidebar:
    st.header("🏺 土器の基準モデル")
    st.image(get_base_pot_image(), caption="基準土器の理想的シルエット", use_container_width=True)
    st.info("このシルエットに輪郭形状が近いほど、基本ステータス（HP・攻撃力・防御力）が上昇します。")
    
    st.subheader("🎨 色と属性の法則")
    st.markdown("""
    - <span style='color:#FF4B4B;font-weight:bold;'>【火】</span> 赤ピクセルが30%以上かつ最大 → 炎属性 🔥
    - <span style='color:#007BFF;font-weight:bold;'>【水】</span> 青ピクセルが30%以上かつ最大 → 水属性 💧
    - <span style='color:#28A745;font-weight:bold;'>【草】</span> 緑ピクセルが30%以上かつ最大 → 草属性 🌿
    - <span style='color:#A0A0A0;font-weight:bold;'>【無】</span> 色がまんべんなく、もしくは地色の茶・グレー系のみ → 無属性 🌟
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    game_mode = st.radio("対戦モード選択", ["👩‍💻 CPU対戦 (1人プレイ)", "👥 プレイヤー対戦 (2人プレイ)"])

# プレイヤーデータ格納
players = [None, None]

st.header("🏺 土器の写真アップロード")

col_p1, col_p2 = st.columns(2)

# --- プレイヤー1 の画像アップロード ---
with col_p1:
    st.subheader("Player 1 (あなた)")
    uploaded_file_1 = st.file_uploader("土器の写真をアップロード (P1)", type=["png", "jpg", "jpeg"], key="p1_file")
    p1_name = st.text_input("土器のニックネーム (P1)", "オレの粘土土器", key="p1_name")
    
    if uploaded_file_1:
         with st.spinner("土器を分析中..."):
            p1_data = get_status_from_image(uploaded_file_1, p1_name)
            players[0] = p1_data
            
            st.markdown(f"""
            <div class="status-card">
                <h3>{p1_data['icon']} {html.escape(p1_data['name'])}</h3>
                <span class="element-badge" style="background-color: {p1_data['color']}; color: {ELEMENTS[p1_data['element']]['text_color']}">
                    属性: {p1_data['element']} {p1_data['icon']}
                </span>
                <p><b>📐 基準モデル類似度:</b> <span style="font-size: 1.2rem; color: #f1c40f; font-weight: bold;">{p1_data['similarity']}%</span></p>
                <p><b>❤️ HP:</b> {p1_data['hp']} | <b>⚔️ ATK:</b> {p1_data['atk']} | <b>🛡️ DEF:</b> {p1_data['def']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            t_img, t_mask = st.tabs(["元の画像", "検出された輪郭"])
            with t_img:
                st.image(p1_data["image"], caption="アップロード画像", use_container_width=True)
            with t_mask:
                st.image(p1_data["contour_image"], caption="検出された輪郭 (緑)", use_container_width=True)
                
            # 色の割合表示
            st.write("🎨 色の成分構成:")
            ratios = p1_data["color_ratios"]
            st.progress(ratios["red"] / 100.0, text=f"火（赤）: {ratios['red']:.1f}%")
            st.progress(ratios["blue"] / 100.0, text=f"水（青）: {ratios['blue']:.1f}%")
            st.progress(ratios["green"] / 100.0, text=f"草（緑）: {ratios['green']:.1f}%")
            st.progress(ratios["none"] / 100.0, text=f"無/地色（その他）: {ratios['none']:.1f}%")

# --- プレイヤー2（またはCPU）の選択・アップロード ---
with col_p2:
    if game_mode == "👩‍💻 CPU対戦 (1人プレイ)":
        st.subheader("Player 2 (エネミー CPU)")
        
        cpu_select = st.selectbox(
            "対戦する歴史的な土器を選択:",
            range(len(CPU_PRESETS)),
            format_func=lambda x: f"{ELEMENTS[CPU_PRESETS[x]['element']]['icon']} {CPU_PRESETS[x]['name']} (属性: {CPU_PRESETS[x]['element']})"
        )
        
        cpu_pattern = CPU_PRESETS[cpu_select]
        players[1] = {
            "name": cpu_pattern["name"],
            "element": cpu_pattern["element"],
            "icon": ELEMENTS[cpu_pattern["element"]]["icon"],
            "color": ELEMENTS[cpu_pattern["element"]]["color"],
            "hp": cpu_pattern["hp"],
            "max_hp": cpu_pattern["max_hp"],
            "atk": cpu_pattern["atk"],
            "def": cpu_pattern["def"],
            "similarity": cpu_pattern["similarity"],
            "custom": False,
            "desc": cpu_pattern["desc"]
        }
        
        st.markdown(f"""
        <div class="status-card" style="border-color: #3498db;">
            <h3>{players[1]['icon']} {html.escape(players[1]['name'])} (CPU)</h3>
            <span class="element-badge" style="background-color: {players[1]['color']}; color: {ELEMENTS[players[1]['element']]['text_color']}">
                属性: {players[1]['element']} {players[1]['icon']}
            </span>
            <p style="color: #bdc3c7; font-size: 0.9rem; margin-top: 5px;">{players[1]['desc']}</p>
            <p><b>📐 基準モデル類似度:</b> <span style="font-size: 1.2rem; color: #f1c40f; font-weight: bold;">{players[1]['similarity']}%</span></p>
            <p><b>❤️ HP:</b> {players[1]['hp']} | <b>⚔️ ATK:</b> {players[1]['atk']} | <b>🛡️ DEF:</b> {players[1]['def']}</p>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.subheader("Player 2 (対戦相手)")
        uploaded_file_2 = st.file_uploader("土器の写真をアップロード (P2)", type=["png", "jpg", "jpeg"], key="p2_file")
        p2_name = st.text_input("土器のニックネーム (P2)", "対戦相手の粘土土器", key="p2_name")
        
        if uploaded_file_2:
            with st.spinner("土器を分析中..."):
                p2_data = get_status_from_image(uploaded_file_2, p2_name)
                players[1] = p2_data
                
                st.markdown(f"""
                <div class="status-card">
                    <h3>{p2_data['icon']} {html.escape(p2_data['name'])}</h3>
                    <span class="element-badge" style="background-color: {p2_data['color']}; color: {ELEMENTS[p2_data['element']]['text_color']}">
                        属性: {p2_data['element']} {p2_data['icon']}
                    </span>
                    <p><b>📐 基準モデル類似度:</b> <span style="font-size: 1.2rem; color: #f1c40f; font-weight: bold;">{p2_data['similarity']}%</span></p>
                    <p><b>❤️ HP:</b> {p2_data['hp']} | <b>⚔️ ATK:</b> {p2_data['atk']} | <b>🛡️ DEF:</b> {p2_data['def']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                t_img_2, t_mask_2 = st.tabs(["元の画像 (P2)", "検出された輪郭 (P2)"])
                with t_img_2:
                    st.image(p2_data["image"], caption="アップロード画像", use_container_width=True)
                with t_mask_2:
                    st.image(p2_data["contour_image"], caption="検出された輪郭 (緑)", use_container_width=True)
                
                st.write("🎨 色の成分構成:")
                ratios_2 = p2_data["color_ratios"]
                st.progress(ratios_2["red"] / 100.0, text=f"火（赤）: {ratios_2['red']:.1f}%")
                st.progress(ratios_2["blue"] / 100.0, text=f"水（青）: {ratios_2['blue']:.1f}%")
                st.progress(ratios_2["green"] / 100.0, text=f"草（緑）: {ratios_2['green']:.1f}%")
                st.progress(ratios_2["none"] / 100.0, text=f"無/地色（その他）: {ratios_2['none']:.1f}%")


# --- バトルステージ ---
if players[0] is not None and players[1] is not None:
    st.divider()
    st.markdown("<h2 style='text-align: center;'>⚔️ バトルフィールド ⚔️</h2>", unsafe_allow_html=True)
    
    p1, p2 = players[0].copy(), players[1].copy()
    
    if st.button("🔥 この土器でバトルを開始する！ 🔥", use_container_width=True, type="primary"):
        st.divider()
        
        battle_title = st.empty()
        action_empty = st.empty()
        
        col_hp1, col_vs, col_hp2 = st.columns([4, 1, 4])
        with col_hp1:
            p1_name_empty = st.empty()
            p1_bar = st.progress(1.0)
            p1_hp_text = st.empty()
        with col_vs:
            st.markdown("<h1 style='text-align:center; color:#e74c3c;'>VS</h1>", unsafe_allow_html=True)
        with col_hp2:
            p2_name_empty = st.empty()
            p2_bar = st.progress(1.0)
            p2_hp_text = st.empty()
            
        p1_name_empty.markdown(f"👥 **{html.escape(p1['name'])}** ({p1['icon']}{p1['element']})")
        p2_name_empty.markdown(f"🤖 **{html.escape(p2['name'])}** ({p2['icon']}{p2['element']})")
        
        battle_ended = False
        winner = None
        
        for turn in range(1, 13):
            battle_title.markdown(f"<h3 style='text-align: center; color: #f1c40f;'>ターン {turn} / 12</h3>", unsafe_allow_html=True)
            
            initiative_1 = p1["def"] * 0.5 + random.randint(1, 20)
            initiative_2 = p2["def"] * 0.5 + random.randint(1, 20)
            
            if initiative_1 >= initiative_2:
                turn_order = [(p1, p2, p2_bar, p2_hp_text, "Player 1"), (p2, p1, p1_bar, p1_hp_text, "Player 2")]
            else:
                turn_order = [(p2, p1, p1_bar, p1_hp_text, "Player 2"), (p1, p2, p2_bar, p2_hp_text, "Player 1")]
                
            for attacker, defender, bar, hp_text, label in turn_order:
                if attacker["hp"] <= 0 or defender["hp"] <= 0:
                    break
                    
                comp_mult = get_compatibility(attacker['element'], defender['element'])
                skill = random.choice(SKILLS[attacker['element']])
                
                comp_comment = " (効果はバツグン！)" if comp_mult > 1.0 else " (効果はいまひとつ...)" if comp_mult < 1.0 else ""
                
                action_empty.markdown(
                    f"<div style='text-align: center; background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; margin-bottom: 20px;'>"
                    f"⚔️ <b style='color:{attacker['color']};'>{html.escape(attacker['name'])}</b> の攻撃！<br>"
                    f"<span style='font-size: 1.15rem; font-weight: bold;'>「{skill['name']}」</span>{comp_comment}<br>"
                    f"<span style='font-size: 0.9rem; color: #bdc3c7;'>{skill['msg']}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                
                time.sleep(1.0)
                
                damage_factor = (attacker['atk'] * skill['mult'] * comp_mult)
                defense_factor = (defender['def'] * 0.6)
                raw_dmg = damage_factor - defense_factor
                dmg = max(random.randint(15, 25), int(raw_dmg + random.randint(-5, 5)))
                
                defender["hp"] -= dmg
                defender["hp"] = max(0, defender["hp"])
                
                bar.progress(defender['hp'] / defender['max_hp'])
                hp_text.markdown(f"**HP: {defender['hp']} / {defender['max_hp']}**")
                
                if defender["hp"] <= 0:
                    winner = attacker
                    battle_ended = True
                    break
                    
            if battle_ended:
                break
                
        # --- 結果発表 ---
        time.sleep(1.0)
        action_empty.empty()
        if winner:
            st.balloons()
            st.success(f"🏆 バトル決着！ 勝者：【{winner['name']}】")
            st.markdown(f"""
            <div style="background: rgba(46, 204, 113, 0.2); border: 2px solid #2ecc71; border-radius: 12px; padding: 20px; text-align: center; margin-top:20px;">
                <h2>🎉 VICTORY 🎉</h2>
                <h3 style="color:#2ecc71;">勝者: {winner['icon']} {html.escape(winner['name'])}</h3>
                <p>優れた土器の魂が、このバトルを制した！</p>
            </div>
            """, unsafe_allow_html=True)
            
            # カスタム(プレイヤー)土器が勝った場合、勝利数をインクリメント
            if winner.get("custom", False):
                increment_win_count(winner["name"])
        else:
            st.warning("⚔️ 12ターンが経過しました！ 引き分けです。")
            st.markdown("""
            <div style="background: rgba(241, 196, 15, 0.2); border: 2px solid #f1c40f; border-radius: 12px; padding: 20px; text-align: center; margin-top:20px;">
                <h2>🤝 DRAW 🤝</h2>
                <p>両者譲らぬ名勝負！ 土器の強さは互角だった！</p>
            </div>
            """, unsafe_allow_html=True)

else:
    st.info("💡 土器の写真をアップロードしてください。対戦相手をセットするとバトルが開始できます。")


# --- ランキング表示セクション ---
st.divider()
st.markdown("<h2 style='text-align: center; color: #f39c12;'>🏆 土器殿堂（ランキング）</h2>", unsafe_allow_html=True)

rankings = load_rankings()

col_rank1, col_rank2 = st.columns(2)

with col_rank1:
    st.markdown("<h3 style='text-align : center; color: #f1c40f;'>📐 匠の造形部門 (類似度順)</h3>", unsafe_allow_html=True)
    if rankings:
        # 類似度順にソート (最高順位Top 10)
        sim_sorted = sorted(rankings, key=lambda x: x["similarity"], reverse=True)[:10]
        sim_data = []
        for i, item in enumerate(sim_sorted):
            elem_meta = ELEMENTS.get(item["element"], ELEMENTS["無"])
            sim_data.append({
                "順位": f"🥇 {i+1}位" if i == 0 else f"🥈 {i+1}位" if i == 1 else f"🥉 {i+1}位" if i == 2 else f"{i+1}位",
                "名前": f"{elem_meta['icon']} {html.escape(item['name'])}",
                "属性": item["element"],
                "類似度": f"{item['similarity']}%",
                "勝利数": f"{item.get('wins', 0)}勝",
                "登録日付": item.get("date", "-")
            })
        st.table(sim_data)
    else:
        st.info("まだ登録されている土器がありません。写真をアップロードして最初の土器を登録しましょう！")

with col_rank2:
    st.markdown("<h3 style='text-align : center; color: #3498db;'>⚔️ 歴戦の覇者部門 (勝利数順)</h3>", unsafe_allow_html=True)
    if rankings:
        # 勝利数でフィルタしソート (勝利数が1以上のもの、Top 10)
        win_candidates = [x for x in rankings if x.get("wins", 0) > 0]
        win_sorted = sorted(win_candidates, key=lambda x: x["wins"], reverse=True)[:10]
        
        if win_sorted:
            win_data = []
            for i, item in enumerate(win_sorted):
                elem_meta = ELEMENTS.get(item["element"], ELEMENTS["無"])
                win_data.append({
                    "順位": f"🥇 {i+1}位" if i == 0 else f"🥈 {i+1}位" if i == 1 else f"🥉 {i+1}位" if i == 2 else f"{i+1}位",
                    "名前": f"{elem_meta['icon']} {html.escape(item['name'])}",
                    "属性": item["element"],
                    "類似度": f"{item['similarity']}%",
                    "勝利数": f"{item.get('wins', 0)}勝"
                })
            st.table(win_data)
        else:
            st.info("まだ勝利数を挙げた土器がいません。バトルを開始して初勝利を目指しましょう！")
    else:
        st.info("まだ登録されている土器がありません。")
