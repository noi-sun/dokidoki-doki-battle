import streamlit as st
import base64
from PIL import Image
import hashlib
import io
import time

# --- 便利関数: 画像をBase64に ---
def get_img_64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# --- 画像解析 ---
def analyze_monster(image_file, name_prefix):
    img_bytes = image_file.getvalue()
    img_hash = hashlib.md5(img_bytes).hexdigest()
    img = Image.open(image_file).convert('RGB')
    avg_color = img.resize((1, 1)).getpixel((0, 0))
    r, g, b = avg_color
    
    # --- 無属性判定の追加 ---
    # 最大値と最小値の差（鮮やかさ）を計算
    diff = max(r, g, b) - min(r, g, b)
    
    # 差が 30 未満なら「無属性（土器）」とする（数値はお好みで調整してください）
    if diff < 30:
        elem, shadow = "🏺", "rgba(150, 150, 150, 0.9)"
    # --- ここから元の判定 ---
    elif r >= g and r >= b:
        elem, shadow = "🔥", "rgba(255, 50, 50, 0.9)"
    elif g >= r and g >= b:
        elem, shadow = "🍃", "rgba(50, 255, 50, 0.9)"
    else:
        elem, shadow = "💧", "rgba(50, 50, 255, 0.9)"
    
    return {
        "img_64": get_img_64(img),
        "elem": elem,
        "shadow": shadow,
        "hp": int(img_hash[:2], 16) + 300,
        "atk": 50 + (max(r,g,b) // 5),
        "name": f"{name_prefix}-{img_hash[:4].upper()}"
    }

def get_compatibility_multiplier(attacker_elem, defender_elem):
    chart = {
        ("🔥", "🍃"): 1.5, ("🔥", "💧"): 0.7,
        ("🍃", "💧"): 1.5, ("🍃", "🔥"): 0.7,
        ("💧", "🔥"): 1.5, ("💧", "🍃"): 0.7,
        # 例：無属性（🏺）は全属性に少し強い、などの設定
        ("🏺", "🔥"): 1.1, ("🏺", "🍃"): 1.1, ("🏺", "💧"): 1.1, 
    }
    return chart.get((attacker_elem, defender_elem), 1.0)

# --- UI & CSS ---
st.set_page_config(layout="wide")
st.title("どきどき土器バトル")

st.markdown("""
<style>
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
@keyframes attack-p1 { 0% { transform: translateX(0); } 50% { transform: translateX(100px) scale(1.1); } 100% { transform: translateX(0); } }
@keyframes attack-p2 { 0% { transform: translateX(0); } 50% { transform: translateX(-100px) scale(1.1); } 100% { transform: translateX(0); } }
@keyframes shake { 0% { transform: translate(5px, 5px); } 20% { transform: translate(-5px, -5px); } 100% { transform: translate(0, 0); } }

.monster { width: 250px; border-radius: 25px; animation: float 3s ease-in-out infinite; }
.p1-atk { animation: attack-p1 0.4s ease-in-out; }
.p2-atk { animation: attack-p2 0.4s ease-in-out; }
.hit { animation: shake 0.4s ease-in-out; filter: brightness(2) red !important; }
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if "battle_active" not in st.session_state:
    st.session_state.update({
        "battle_active": False, "p1_hp": -1, "p2_hp": -1, # 初期値を-1に
        "log": "モンスターを召喚してください", "p1_ani": "", "p2_ani": "",
        "turn": 1, "winner": None
    })

c1, c2 = st.columns(2)
f1 = c1.file_uploader("どきモンスターＰ１ 召喚", type=["png", "jpg"])
f2 = c2.file_uploader("どきモンスターＰ２ 召喚", type=["png", "jpg"])
# --- ここから「確実なリセット」処理 ---
# 現在アップロードされているファイル名を合体させて「今の状態」を記録
current_files = f"{f1.name if f1 else ''}-{f2.name if f2 else ''}"

# もし前回記録したファイル名と違うなら、中身を全部リセットする
if "last_files" not in st.session_state or st.session_state.last_files != current_files:
    st.session_state.p1_hp = -1
    st.session_state.p2_hp = -1
    st.session_state.battle_active = False
    st.session_state.winner = None
    st.session_state.log = "新しい土器が届きました！"
    st.session_state.last_files = current_files # 今のファイル名を保存
# --- ここまで ---
if f1 and f2:
    p1 = analyze_monster(f1, "P1")
    p2 = analyze_monster(f2, "P2")
    
    # HPの初期化（一度だけ実行）
    if st.session_state.p1_hp == -1:
        st.session_state.p1_hp = p1["hp"]
        st.session_state.p2_hp = p2["hp"]

    # モンスター表示
    disp1, disp2 = st.columns(2)
    with disp1:
        st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{p1["img_64"]}" class="monster {st.session_state.p1_ani}" style="filter: drop-shadow(0 0 25px {p1["shadow"]});"><br><b>{p1["name"]} {p1["elem"]}</b></div>', unsafe_allow_html=True)
        st.progress(max(0, st.session_state.p1_hp / p1["hp"]), text=f"HP: {st.session_state.p1_hp}")
    with disp2:
        st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{p2["img_64"]}" class="monster {st.session_state.p2_ani}" style="filter: drop-shadow(0 0 25px {p2["shadow"]});"><br><b>{p2["name"]} {p2["elem"]}</b></div>', unsafe_allow_html=True)
        st.progress(max(0, st.session_state.p2_hp / p2["hp"]), text=f"HP: {st.session_state.p2_hp}")

    if not st.session_state.battle_active and not st.session_state.winner:
        if st.button("🚀 オートバトル開始！！", use_container_width=True):
            st.session_state.battle_active = True
            st.rerun()

    # --- 自動バトルループ ---
    if st.session_state.battle_active and not st.session_state.winner:
        time.sleep(1.2) # アニメーションを見せるための待機
        
        if st.session_state.turn == 1:
            # P1の攻撃
            st.session_state.p1_ani, st.session_state.p2_ani = "p1-atk", "hit"
            mul = get_compatibility_multiplier(p1["elem"], p2["elem"]) # <--- 相性計算を追加
            dmg = int(p1["atk"] * mul)
            st.session_state.p2_hp -= dmg
            msg = "効果は抜群だ！" if mul > 1 else "いまひとつのようだ..." if mul < 1 else ""
            st.session_state.log = f"⚡ {p1['name']} の攻撃！ {dmg} ダメージ！ {msg}"
            st.session_state.turn = 2
        else:
            # P2の攻撃
            st.session_state.p1_ani, st.session_state.p2_ani = "hit", "p2-atk"
            mul = get_compatibility_multiplier(p2["elem"], p1["elem"]) # <--- 相性計算を追加
            dmg = int(p2["atk"] * mul)
            st.session_state.p1_hp -= dmg
            msg = "効果は抜群だ！" if mul > 1 else "いまひとつのようだ..." if mul < 1 else ""
            st.session_state.log = f"🔥 {p2['name']} の反撃！ {dmg} ダメージ！ {msg}"
            st.session_state.turn = 1

        if st.session_state.p1_hp <= 0 or st.session_state.p2_hp <= 0:
            st.session_state.battle_active = False
            st.session_state.winner = p1['name'] if st.session_state.p1_hp > 0 else p2['name']
        
        st.rerun()

# 決着後の表示
if st.session_state.winner:
    st.balloons()
    st.success(f"🏆 決着！勝者: {st.session_state.winner}")
    
    # 決着がついた時だけ「再戦する」ボタンを出す
    if st.button("再戦する", use_container_width=True):
        st.session_state.p1_hp = -1
        st.session_state.p2_hp = -1
        st.session_state.winner = None
        st.session_state.battle_active = False
        st.session_state.log = "再戦準備完了"
        st.rerun()

st.info(st.session_state.log)