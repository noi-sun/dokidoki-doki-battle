import streamlit as st
import base64
from PIL import Image, ImageFilter, ImageStat
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
    
    # 1. 輪郭（形）の解析
    edge_img = img.convert("L").filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edge_img)
    complexity = stat.mean[0] 
    
    # 2. 複雑さによるボーナス
    shape_bonus = int(complexity * 2) 
    special_comment = ""
    if complexity > 20:
        special_comment = "【SR】"
    elif complexity < 5:
        special_comment = "【N】"

    # 3. 色の解析
    avg_color = img.resize((1, 1)).getpixel((0, 0))
    r, g, b = avg_color
    
    # 属性判定 (最大値と最小値の差で無属性を判定)
    diff = max(r, g, b) - min(r, g, b)
    if diff < 30:
        elem, shadow = "🏺", "rgba(150, 150, 150, 0.9)"
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
        "atk": 50 + (max(r,g,b) // 5) + shape_bonus,
        "name": f"{special_comment}{name_prefix}-{img_hash[:4].upper()}"
    }

def get_compatibility_multiplier(attacker_elem, defender_elem):
    chart = {
        ("🔥", "🍃"): 1.5, ("🔥", "💧"): 0.7,
        ("🍃", "💧"): 1.5, ("🍃", "🔥"): 0.7,
        ("💧", "🔥"): 1.5, ("💧", "🍃"): 0.7,
        ("🏺", "🔥"): 1.1, ("🏺", "🍃"): 1.1, ("🏺", "💧"): 1.1, 
    }
    return chart.get((attacker_elem, defender_elem), 1.0)

# --- UI & CSS ---
st.set_page_config(layout="wide", page_title="どきどき土器バトル")
st.title("🤖 どきどき土器バトル：ランキング版")

st.markdown("""
<style>
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
@keyframes attack-p1 { 0% { transform: translateX(0); } 50% { transform: translateX(100px) scale(1.1); } 100% { transform: translateX(0); } }
@keyframes attack-p2 { 0% { transform: translateX(0); } 50% { transform: translateX(-100px) scale(1.1); } 100% { transform: translateX(0); } }
@keyframes shake { 0% { transform: translate(5px, 5px); } 20% { transform: translate(-5px, -5px); } 100% { transform: translate(0, 0); } }

.monster { width: 250px; border-radius: 25px; animation: float 3s ease-in-out infinite; }
.p1-atk { animation: attack-p1 0.4s ease-in-out; }
.p2-atk { animation: attack-p2 0.4s ease-in-out; }
.hit { animation: shake 0.4s ease-in-out; filter: brightness(2) contrast(2) !important; }
</style>
""", unsafe_allow_html=True)

# セッション状態の初期化
if "battle_active" not in st.session_state:
    st.session_state.update({
        "battle_active": False, "p1_hp": -1, "p2_hp": -1,
        "log": "土器を召喚してください", "p1_ani": "", "p2_ani": "",
        "turn": 1, "winner": None, "rankings": {}
    })

# --- サイドバー表示 ---
st.sidebar.header("🏆 土器勝利数ランキング")
if st.session_state.rankings:
    # 勝利数順にソート
    sorted_rank = sorted(st.session_state.rankings.items(), key=lambda x: x[1], reverse=True)
    for name, wins in sorted_rank:
        st.sidebar.write(f"**{wins}勝** : {name}")
else:
    st.sidebar.write("まだ戦績がありません")

# メインUI
c1, c2 = st.columns(2)
f1 = c1.file_uploader("どきモンスターＰ１ 召喚", type=["png", "jpg"])
f2 = c2.file_uploader("どきモンスターＰ２ 召喚", type=["png", "jpg"])
# --- 🌟 ここに追加：名前入力フォーム ---
name1 = c1.text_input("P1のニックネーム", placeholder="例：最強の土器")
name2 = c2.text_input("P2のニックネーム", placeholder="例：伝説のツボ")
# 画像が入れ替わった際のリセット処理
if f1 and f2:
    current_files = f"{f1.name}-{f2.name}"
    if "last_files" not in st.session_state or st.session_state.last_files != current_files:
        st.session_state.update({
            "p1_hp": -1, "p2_hp": -1, "battle_active": False,
            "winner": None, "log": "新しい土器が届きました！", "last_files": current_files
        })

    # 解析実行
    p1 = analyze_monster(f1, name1 if name1 else "P1")
    p2 = analyze_monster(f2, name2 if name2 else "P2")
    
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

    # バトル開始
    if not st.session_state.battle_active and not st.session_state.winner:
        if st.button("🚀 オートバトル開始！！", use_container_width=True):
            st.session_state.battle_active = True
            st.rerun()

    # 自動バトルループ
    if st.session_state.battle_active and not st.session_state.winner:
        time.sleep(1.2)
        if st.session_state.turn == 1:
            st.session_state.p1_ani, st.session_state.p2_ani = "p1-atk", "hit"
            mul = get_compatibility_multiplier(p1["elem"], p2["elem"])
            dmg = int(p1["atk"] * mul)
            st.session_state.p2_hp -= dmg
            msg = "効果は抜群だ！" if mul > 1 else "いまひとつのようだ..." if mul < 1 else ""
            st.session_state.log = f"⚡ {p1['name']} の攻撃！ {dmg} ダメージ！ {msg}"
            st.session_state.turn = 2
        else:
            st.session_state.p1_ani, st.session_state.p2_ani = "hit", "p2-atk"
            mul = get_compatibility_multiplier(p2["elem"], p1["elem"])
            dmg = int(p2["atk"] * mul)
            st.session_state.p1_hp -= dmg
            msg = "効果は抜群だ！" if mul > 1 else "いまひとつのようだ..." if mul < 1 else ""
            st.session_state.log = f"🔥 {p2['name']} の反撃！ {dmg} ダメージ！ {msg}"
            st.session_state.turn = 1

        # 決着判定
        if st.session_state.p1_hp <= 0 or st.session_state.p2_hp <= 0:
            st.session_state.battle_active = False
            winner_data = p1 if st.session_state.p1_hp > 0 else p2
            st.session_state.winner = winner_data['name']
            # ランキング加算
            if st.session_state.winner not in st.session_state.rankings:
                st.session_state.rankings[st.session_state.winner] = 0
            st.session_state.rankings[st.session_state.winner] += 1
        st.rerun()

    # 決着表示
    if st.session_state.winner:
        st.balloons()
        st.success(f"🏆 決着！勝者: {st.session_state.winner}")
        if st.button("再戦する", use_container_width=True):
            st.session_state.update({
                "p1_hp": -1, "p2_hp": -1, "winner": None,
                "battle_active": False, "log": "再戦準備完了", "turn": 1
            })
            st.rerun()

st.info(st.session_state.log)