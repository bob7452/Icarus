import base64
import csv
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from update_news import chat

# --- 1. 路徑初始化 (Pathlib) ---
BASE_DIR = Path(__file__).resolve().parent
CRED_DIR = BASE_DIR / "credit"
DB_DIR = BASE_DIR / "database"
CREDENTIALS_FILE = CRED_DIR / "credentials.json"
TOKEN_FILE = CRED_DIR / "token.json"
DATABASE_FILE = DB_DIR / "trading_journal.db"
PROCESSED_LOG = DB_DIR / "processed_emails.log"

# 自動建立資料夾
DB_DIR.mkdir(parents=True, exist_ok=True)
CRED_DIR.mkdir(parents=True, exist_ok=True)

# --- 2. Gmail 服務初始化 ---
def get_gmail_service():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(f"找不到憑證檔案：{CREDENTIALS_FILE}，請確認檔案位置。")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        
    return build('gmail', 'v1', credentials=creds)

# --- 3. 強化版附件下載 (防重複 + 最鄰近搜尋) ---
def fetch_latest_ib_attachment(service):
    # 搜尋最近 7 天內的信件，避免漏掉週末或假日的報表
    #subject:活動報表
    search_query = "from:interactivebrokers.com has:attachment newer_than:7d"
    
    print(f"🔍 正在搜尋 Gmail 報表...")
    results = service.users().messages().list(userId='me', q=search_query).execute()
    messages = results.get('messages', [])

    if not messages:
        print("❌ 沒找到符合條件的報表郵件。")
        return None

    # 取得詳細資料並按時間排序 (從新到舊)
    full_messages = []
    for m in messages:
        detail = service.users().messages().get(userId='me', id=m['id'], format='minimal').execute()
        full_messages.append(detail)
    
    full_messages.sort(key=lambda x: int(x['internalDate']), reverse=True)
    
    # 挑選最新的一封
    target_msg = full_messages[0]
    msg_id = target_msg['id']

    # 重複下載判別
    already_processed = []
    if PROCESSED_LOG.exists():
        already_processed = PROCESSED_LOG.read_text().splitlines()

    if msg_id in already_processed:
        print(f"⏭️  郵件 (ID: {msg_id}) 已經解析過，跳過下載。")
        return None

    # 下載附件
    full_msg = service.users().messages().get(userId='me', id=msg_id).execute()
    for part in full_msg['payload'].get('parts', []):
        if part['filename'] and part['filename'].endswith('.csv'):
            print(f"📥 發現新報表：{part['filename']} (ID: {msg_id})")
            att_id = part['body'].get('attachmentId')
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=msg_id, id=att_id).execute()
            
            data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))
            csv_path = BASE_DIR / part['filename']
            csv_path.write_bytes(data)
            
            # 紀錄已處理
            with PROCESSED_LOG.open("a") as f:
                f.write(msg_id + "\n")
            
            return csv_path
    return None

# --- 4. 數據解析、入庫與視覺化 ---
def run_analysis_system(csv_path: Path):
    trades_rows = []
    headers = None
    cash_value = 0
    positions = []

    print(f"🚀 開始解析報表數據...")

    with csv_path.open('r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            # 交易紀錄
            if row[0] == '交易' and row[1] == 'Header':
                headers = row[:14]
            elif row[0] == '交易' and row[1] == 'Data' and row[2] == 'Order':
                trades_rows.append(row[:14])
            # 現金快照
            if row[0] == '淨資産值' and row[1] == 'Data' and row[2] == '現金':
                try: cash_value = float(row[6].replace(',', ''))
                except: pass
            # 持倉快照
            if row[0] == '未平倉持倉' and row[1] == 'Data' and row[2] == 'Summary':
                try: positions.append({'Sym': row[5], 'Val': float(row[11].replace(',', ''))})
                except: pass

    # A. 處理交易數據
    if trades_rows and headers:
        df = pd.DataFrame(trades_rows, columns=headers)
        mapping = {
            '代碼': 'symbol', '貨幣': 'currency', '日期/時間': 'timestamp',
            '數量': 'quantity', '交易價格': 'price', '收益': 'proceeds',
            '傭金/稅': 'commission', '已實現的損益': 'realized_pnl'
        }
        df = df[mapping.keys()].rename(columns=mapping)

        # 數值轉換
        for col in ['quantity', 'price', 'proceeds', 'commission', 'realized_pnl']:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
        # 時間轉換 (美東轉台北)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d, %H:%M:%S')
        tw_tz = pytz.timezone('Asia/Taipei')
        us_tz = pytz.timezone('US/Eastern')
        df['timestamp_tw'] = df['timestamp'].apply(lambda x: us_tz.localize(x).astimezone(tw_tz))
        
        # 生成雜湊值防 Row 重複
        df['raw_hash'] = df.apply(lambda r: hashlib.md5(f"{r['timestamp']}_{r['symbol']}_{r['quantity']}_{r['price']}".encode()).hexdigest(), axis=1)
        
        # 寫入 SQLite
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    raw_hash TEXT PRIMARY KEY, symbol TEXT, currency TEXT, 
                    timestamp_tw TEXT, quantity REAL, price REAL, 
                    proceeds REAL, commission REAL, net_proceeds REAL, 
                    realized_pnl REAL, timestamp_utc TEXT
                )
            ''')
            
            df_final = df.assign(net_proceeds = df['proceeds'] + df['commission'])[[
                'raw_hash', 'symbol', 'currency', 'timestamp_tw', 'quantity', 
                'price', 'proceeds', 'commission', 'net_proceeds', 'realized_pnl', 'timestamp'
            ]]
            
            data_tuples = [tuple(str(item) if hasattr(item, 'isoformat') else item for item in row) for row in df_final.values.tolist()]
            cursor.executemany('INSERT OR IGNORE INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?)', data_tuples)
            print(f"✅ 資料庫同步完成，新增 {cursor.rowcount} 筆紀錄。")
    else:
        print("⚠️  本次報表中無新成交紀錄。")


    # --- 視覺化升級：專業環形圖 ---
    if cash_value > 0 or positions:
        labels = ['Cash'] + [p['Sym'] for p in positions]
        values = [cash_value] + [p['Val'] for p in positions]
        total_nav = sum(values)

        # 1. 強制設定深色背景
        plt.style.use('dark_background') # 使用 matplotlib 內建深色模板
        fig, ax = plt.subplots(figsize=(10, 10), facecolor='#121212', dpi=100) # 設定畫布為極深灰
        ax.set_facecolor('#121212')

        # 2. 精選配色：深海科技漸層
        # 使用 mako 或 viridis 配色會很有專業感
        colors = sns.color_palette("mako", len(labels))

        # 3. 繪製環形圖
        # explode 讓第一個元素稍稍突出
        explode = [0.08] + [0.02] * (len(labels) - 1)
        
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%', 
            startangle=150,
            pctdistance=0.82, 
            explode=explode,
            colors=colors,
            wedgeprops={'width': 0.35, 'edgecolor': '#121212', 'linewidth': 3}, # 較細的環，深色間隔
            textprops={'color': 'w', 'fontsize': 12}
        )

        # 4. 優化自動百分比標籤
        plt.setp(autotexts, size=10, weight="bold", family='sans-serif')

        # # 5. 中心文字：總資產 NAV (改用亮綠色，像螢幕顯示器)
        # ax.text(0, 0, f'NAV\n${total_nav:,.0f}', 
        #         ha='center', va='center', 
        #         fontsize=24, fontweight='bold', 
        #         color='#00ffcc', # 霓虹綠
        #         family='monospace') # 等寬字體更有代碼感

        # 6. 標題與標註
        plt.title(f'TradeMirror | Portfolio Intelligence', 
                fontsize=18, pad=30, color='#ffffff', fontweight='bold', loc='left')
        
        # --- 靈魂標語：換成低調淺灰 ---
        plt.figtext(0.9, 0.07, f'Plan your trading and Trade your plan', 
                    horizontalalignment='right', 
                    color='#D3D3D3',  # 這裡改為 Light Gray
                    fontsize=12, 
                    fontstyle='italic', 
                    family='serif',
                    alpha=0.8) # 增加一點點透明度，讓它更不突兀

        # 7. 保存圖檔
        report_img = BASE_DIR / 'portfolio_pro_report.png'
        plt.savefig(report_img, 
                    bbox_inches='tight', 
                    facecolor=fig.get_facecolor(), # 確保邊框也是深色的
                    edgecolor='none',
                    dpi=300)
        
        print(f"🖼️  終端機質感報表已生成：{report_img}")
        
# --- 5. 執行進入點 ---
if __name__ == "__main__":
    try:
        service = get_gmail_service()
        csv_file = fetch_latest_ib_attachment(service)
        
        if csv_file:
            run_analysis_system(csv_file)
            print("\n✨ [TradeMirror] 任務執行成功。")
            chat(contents=["!TodayPosition"],chanel_list=["1495289248063033516"])
        else:
            print("\n👋 沒有需要處理的新數據。")
            
    except Exception as e:
        print(f"💥 系統錯誤: {e}")
    finally:
        if csv_file and csv_file.exists():
            csv_file.unlink()
            print(f"🗑️  暫存檔已清理: {csv_file.name}")
