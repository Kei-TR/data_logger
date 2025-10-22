from ftplib import FTP
import time
import datetime
import os
import sys
import re
import traceback
import json
import pandas as pd
import smtplib
import email
from email.mime.text import MIMEText
import numpy as np
import matplotlib.pyplot as plt

# v1.0 2025/09/08 作成
# v1.1 2025/10/22 修正：サンプリングレートの検出方法を修正(GL800対応)

debug = False # Trueならメール送信しない

#logger_server_dic = {'GL840-02':'172.30.113.89','Local':'192.168.151.154','test':'192.168.151.111'}
#logger_server_dic = {'GL840-02':'172.30.113.89','GL840-01':'172.30.113.97'}

# データロガー名とIPアドレスの辞書
if not debug:
    logger_server_dic = {
        'GL840-01':'172.30.113.97','GL840-02':'172.30.113.89','GL840-03':'172.30.113.91',
        'GL800-01':'172.30.113.92','GL800-02':'172.30.113.93','GL800-03':'172.30.113.94',
        'GL900-01':'172.30.113.95','GL900-02':'172.30.113.96'
    }    
else: # デバッグ用
    logger_server_dic = {'GL800-02':'172.30.113.93','GL840-02':'172.30.113.89'}
    # logger_server_dic = {
    #     'GL840-01':'172.30.113.97','GL840-02':'172.30.113.89','GL840-03':'172.30.113.91',
    #     'GL800-01':'172.30.113.92','GL800-02':'172.30.113.93','GL800-03':'172.30.113.94',
    #     'GL900-01':'172.30.113.95','GL900-02':'172.30.113.96','test':'172.30.113.89' # testはGL840-02と同じ
    # }

if not debug:
    log_dir = r'\\cae-sv02\CAE部\共通\log\IoT\rasPi\common\data_logger\log' # ログファイルのディレクトリ
else:
    log_dir = r'\\cae-sv02\CAE部\共通\log\IoT\rasPi\common\data_logger\log\local_test' # ログファイルのディレクトリ(デバッグ用)

parent_dir_list = ['/SD2', '/USB1'] # GL840 or GL800
local_base_dir = '//cae-sv02/CAE部/共通/log/IoT/data_logger'  # バックアップ先のローカルディレクトリ
#FILE_PATTERN = re.compile(r'(\d{6}-\d{6}_UG_rep\d{3}|\d{6}-\d{6})\.CSV$', re.IGNORECASE) # ファイル名パターンの正規表現
FILE_PATTERN = re.compile(r'^\d{6}-\d{6}.*\.csv$', re.IGNORECASE) # ファイル名パターンの正規表現
checked_lines = {}  # グローバル辞書、logger_nameごとに最終チェック行を記録
logger_alert_flg = {} #  グローバル辞書、logger_nameごとのアラートフラグ
previous_local_path = {} #  グローバル辞書、logger_nameごとに前回ログファイルパス

##############################
# 記録中のファイルだけをコピーする場合
##############################

# 関数：親ディレクトリを取得
def get_available_parent_dir(ftp):
    for d in parent_dir_list:
        try:
            ftp.cwd(d)
            return d
        except Exception:
            continue
    return None

# 関数：フォルダ名のリストを取得(6桁の数字)
def get_date_dirs(ftp):
    dirs = ftp.nlst()
    return sorted([d for d in dirs if d.isdigit() and len(d) == 6]) # フォルダ名は6桁数字

# 関数：ファイル名のリストを取得
def get_files_in_dir(ftp):
    files = ftp.nlst()
    return [f for f in files if FILE_PATTERN.match(f)] # ファイル名は6-6桁数字(文字列が付加されている場合あり)

# 関数：FTPにあるファイルのサイズを取得
def get_ftp_file_size(ftp, filename):
    try:
        size = ftp.size(filename)
        return size if size is not None else -1
    except Exception:
        return -1

# 関数：最新のログファイルパスを取得
def get_latest_log_path(ftp):

    # 親フォルダ名を検出(/SD2 or /USB1)
    parent_dir = get_available_parent_dir(ftp)
    if not parent_dir:
        print(f"WARNING -> /SD2 or /USB1 not found in FTP server")
        return None

    # /SD2 配下のフォルダ一覧を取得
    ftp.cwd(parent_dir)
    dirs = get_date_dirs(ftp)
    if not dirs:
        return None

    # 最新のフォルダ名を取得
    latest_dir = max(dirs) 

    # 最新フォルダ配下のファイル一覧を取得
    ftp.cwd(latest_dir)
    files = get_files_in_dir(ftp)
    if not files:
        return None

    # 最新日時のファイル名を取得
    latest_file = max(files)
 
    return f'{parent_dir}/{latest_dir}/{latest_file}'

# 関数：FTP上のファイルをローカルにコピー
def backup_log(logger_name):

    print("Log backup...")

    # FTPに接続
    try:
        # ftp = FTP(logger_server_dic.get(logger_name))
        ftp = FTP()
        ftp.connect(host=logger_server_dic.get(logger_name), timeout=3) # タイムアウト3秒

        ftp.login() # ユーザー名・パスワード不要
        ftp.encoding = 'cp932' # Windowsの日本語環境の場合

    except (TimeoutError, ConnectionRefusedError):
        print(f"ERROR -> Failed to connect to FTP server: {logger_server_dic.get(logger_name)}")
        #write_error_log(f'backup_log({logger_name})', f'Failed to connect to FTP server: {logger_server_dic.get(logger_name)}')
        return False
    except Exception as e:
        print("ERROR: "+str(e))
        print("TYPE: "+str(type(e)))
        print(f'MESSAGE:\n----------\n{traceback.format_exc()}----------')
        write_error_log(f'backup_log({logger_name})', traceback.format_exc())
        return False

    # FTP側のパス・ファイル名を取得
    copying_file_path = get_latest_log_path(ftp) # FTP側のパス(最新のファイル)
    if copying_file_path is None:
        print(f"ERROR -> No log file found in FTP server: {logger_server_dic.get(logger_name)}")
        #write_error_log(f'backup_log({logger_name})', f'No log file found in FTP server: {logger_server_dic.get(logger_name)}')
        try:
            ftp.quit()
        except ConnectionResetError:
            pass
        return False
    file_name = os.path.basename(copying_file_path) # コピーするファイル名

    # ローカル側のパスを指定
    local_path = os.path.join(local_base_dir, logger_name, file_name) # ローカル側のパス
    os.makedirs(os.path.dirname(local_path), exist_ok=True) # ディレクトリがなければ作成

    # すでにサーバーにファイルがあるか確認
    if os.path.exists(local_path):

        ftp_file_size = get_ftp_file_size(ftp, file_name) # FTP側のファイルサイズ
        local_file_size = os.path.getsize(local_path) # ローカル側のファイルサイズ

        # FTP側のファイルサイズが大きければコピー
        if ftp_file_size > local_file_size:
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {file_name}', f.write) # FTP側のファイルの方が大きいので上書きコピー
            print(f'コピー成功(サイズ変化): {datetime.datetime.now().replace(microsecond=0)} {local_path}')
        
        # ファイルサイズが同じならスキップ
        else:
            print(f'スキップ(ファイルサイズ同じ): {file_name}')

    # ローカルにファイル自体なければ新規コピー
    else:
        with open(local_path, 'wb') as f:
            ftp.retrbinary(f'RETR {file_name}', f.write) # ローカルにないのでコピー
        print(f'コピー成功(新規): {datetime.datetime.now().replace(microsecond=0)} {local_path}')

    # FTP切断
    try:
        ftp.quit()
    except ConnectionResetError:
        pass

    return True

# 関数：jsonファイルをロード
def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8-sig') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"WARNING -> JSON file not found: {path}")
        return {}

# 関数：jsonファイルをセーブ
def save_json(path, data):
    with open(path, 'w', encoding='utf-8-sig') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# 関数：読み込んだjsonの中から最大の波長を見つける(前部オフセット量として使う)
def find_max_cycle_time(json_dict):

    wavelength = []
    for channel in json_dict.get("thresholds", []):
        tmp = 0
        for key, val in channel.items():
            if key == "time_high":
                tmp += val.get("max", 0)
            if key == "time_low":
                tmp += val.get("max", 0)
        wavelength.append(tmp)
    return max(wavelength) if wavelength else 0

    # 半分の波長
    # max_values = []
    # for threshold in json_dict.get("thresholds", []):
    #     for key, val in threshold.items():
    #         if key != "value_alltime":
    #             if isinstance(val, dict) and "max" in val:
    #                 max_values.append(val["max"])
    # return max(max_values) if max_values else 0

# 関数：CSVヘッダーからサンプリング間隔(秒)を取得
def get_sampling_interval_from_header(path):
    try:
        with open(path, encoding="cp932") as f:
            for i, line in enumerate(f):
                if i > 50:  # 最初の50行だけチェック
                    break
                if "測定間隔" in line:
                    # 例: "測定間隔,500ms" or "測定間隔,10s"
                    parts = line.strip().split(",")
                    if len(parts) >= 2:
                        interval_str = parts[1].strip()
                        # ms単位の場合
                        if "ms" in interval_str.lower():
                            value = float(interval_str.lower().replace("ms", "").strip())
                            return value / 1000.0  # ミリ秒→秒に変換
                        # s単位の場合
                        elif "s" in interval_str.lower():
                            value = float(interval_str.lower().replace("s", "").strip())
                            return value
        return None
    except Exception as e:
        print(f"ERROR in get_sampling_interval_from_header: {e}")
        print(f"MESSAGE:\n----------\n{traceback.format_exc()}----------")
        return None

# 関数：キーワードが入っている行の次行番号を検出し、コラム名も取得
def detect_data_line(path, keyword, offset=1):
    with open(path, encoding="cp932") as f:
        for i, line in enumerate(f):
            if keyword in line:
                start_row = i + offset  # 「測定値」行+offsetの行から読み込み
                column = next(f).strip().split(",") # 「測定値」の次の行をリスト化
                break
    return start_row, column

# 関数：ログファイルからグラフ(PNG)作成
def create_graph_from_log(logpath_x, logpath_y, output_path):
    plt.plot(logpath_x, logpath_y)
    #plt.xlabel(logpath_x.name if logpath_x.name else 'x')
    plt.xlabel("Sample Number") # 日本語表示対応してないので暫定対応
    plt.ylabel(logpath_y.name if logpath_y.name else 'y')
    #plt.title('Sample Plot')
    plt.savefig(output_path)
    plt.close()

# 関数：メール送信
def send_mail(SUBJECT='【自動送信】メール通知',
              BODY='本文を入れてください', # 改行に<br>を使うとHTML形式になる
              SENDER='自動送信システム',
              FROM='alert@info.tokai-rika.co.jp',
              RECIPIENT='RECIPIENT',
              TO=['to@info.tokai-rika.co.jp'], # メールアドレスはリスト形式で入力
              CC=[] # メールアドレスはリスト形式で入力
              ):

    # メールサーバー等の情報
    smtp_host = "192.168.14.54"
    smtp_port = 25
    admin_mail_address=["kei.sumiyoshi@exc.tokai-rika.co.jp"] # 管理者メールアドレス(メール送信時BCCで送られる)

	#メールの内容
    msg = MIMEText(BODY,"html") if ("<br>" in BODY) else MIMEText(BODY,"plain") # 送信形式をhtmlにするか判定
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((SENDER, FROM))
    msg['To'] = ",".join([email.utils.formataddr((RECIPIENT, addr)) for addr in TO])
    msg['Cc'] = ",".join(CC)

	#重要フラグ追加
    msg['X-Priority'] = '1'
    #msg['Importance'] = 'High'

    # 宛先リスト(CC,BCC含む)
    TO_list = TO + CC + admin_mail_address

	#メール送信
    server = smtplib.SMTP(smtp_host, smtp_port)
    #server.set_debuglevel(True) # サーバとの通信内容を表示する
    server.sendmail(FROM, TO_list, msg.as_string())
    server.close()

# 関数：閾値監視
def monitor_threshold(logger_name):

    print("Checking threshold...")

    # --- 状態ファイルのパス ---
    status_path = os.path.join(local_base_dir, logger_name, ".status.json")

    # --- 状態ファイルから情報を読み込み ---
    status_data = load_json(status_path)

    # ファイルがあれば既存のグローバル変数に反映
    if status_data:
        checked_lines[logger_name] = status_data.get("checked_lines", 0)
        logger_alert_flg[logger_name] = status_data.get("logger_alert_flg", False)
        previous_local_path[logger_name] = status_data.get("previous_local_path", None)

    # 特定のディレクトリにあるファイルの中から最もファイル名の数字が大きいものを選択
    folder_path = os.path.join(local_base_dir, logger_name)  # 例: 'C:/example_folder'
    try:
        file_list = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and FILE_PATTERN.match(f)]
    except Exception as e:
        print("ERROR: "+str(e))
        print("TYPE: "+str(type(e)))
        print(f'MESSAGE:\n----------\n{traceback.format_exc()}----------')
        write_error_log(f'monitor_threshold({logger_name})', traceback.format_exc())
        return
    if file_list:
        file_name = max(file_list)
    else:
        print("ERROR: No log file to check (A folder is empty)")
        #write_error_log(f'monitor_threshold({logger_name})', 'No log file to check (A folder is empty)')
        return

    # 最新のログファイルのパスを探す
    local_path = os.path.join(local_base_dir, logger_name, file_name)
    #print(local_path)

    # ログファイルを指定行から読み込み
    try:
        start_row, column = detect_data_line(local_path,"測定値",offset=3)
        df = pd.read_csv(local_path, skiprows=start_row, names=column+["NA"], encoding="cp932") # ログの最後にカンマがあるのでダミー列を追加
    except Exception as e:
        print("ERROR: "+str(e))
        print("TYPE: "+str(type(e)))
        print(f'MESSAGE:\n----------\n{traceback.format_exc()}----------')
        write_error_log(f'monitor_threshold({logger_name})', traceback.format_exc())
        return

    # 時刻をdatetime形式に変換し、もとのms列＆日付列を削除し置き換える
    date_col = None

    # 日付列の検出
    # GL840シリーズは'日付/時間'と'ms'列、GL800シリーズは'日付 時間'列のみ
    if '日付/時間' in df.columns:
        date_col = '日付/時間'
    elif '日付 時間' in df.columns:
        date_col = '日付 時間'
    else:
        print(f"ERROR -> '日付/時間' or '日付 時間' column not found in CSV file")
        print(f"Available columns: {df.columns.tolist()}")
        write_error_log(f'monitor_threshold({logger_name})', f"Date column not found. Available: {df.columns.tolist()}")
        return

    # ms列がある場合はmsを加算し、ms列＆日付列を削除し置き換える(GL840シリーズなど)
    if 'ms' in df.columns:
        df_time = pd.to_datetime(df[date_col]) + pd.to_timedelta(df['ms'], unit='ms')
        df = df.drop([date_col, 'ms'], axis=1)
    else:
        # ms列がない場合、日付列のみを削除し置き換える(GL800シリーズなど)
        df_time = pd.to_datetime(df[date_col])
        df = df.drop([date_col], axis=1)

    df.insert(0, '日時', df_time)
    #print(df)

    # サンプリングレート取得
    # 優先順位: 1.CSVヘッダーから取得 → 2.時刻差分から計算 → 3.デフォルト値
    sample_interval = get_sampling_interval_from_header(local_path)

    if sample_interval is None:
        # ヘッダーから取得できない場合は、時刻差分から計算
        if len(df) > 1:
            sample_interval = (df['日時'].iloc[1] - df['日時'].iloc[0]).total_seconds()
            if sample_interval == 0:
                # 差分が0秒の場合(同一秒に複数サンプル)は、デフォルト値を使用
                sample_interval = 1.0
                print(f"WARNING -> Sampling interval could not be determined accurately. Using default: {sample_interval}s")
        else:
            sample_interval = 1.0 # ログが空欄の場合は仮の値を入れておく(エラー対策)

    # print(f"Sampling interval: {sample_interval}s")

    # jsonファイル読み込み
    #json_path = os.path.join(local_base_dir, logger_name, f'{logger_name}.json')
    json_path = os.path.join(local_base_dir, logger_name, f'setting.json')
    if os.path.exists(json_path):
        json_dict = load_json(json_path)
    else:
        print(f"WARNING -> Skipping a threshold check (No JSON file)")
        #write_error_log(f'monitor_threshold({logger_name})', 'No JSON file')
        return

    # ログファイルが変わったらアラート＆最終チェック行数リセット
    if previous_local_path.get(logger_name,None) != local_path:
        logger_alert_flg[logger_name] = False
        checked_lines[logger_name] = 0

    # チェックするデータだけ抽出
    last_checked = checked_lines.get(logger_name, 0) # すでにチェック済みの行数を取得
    head_offset = find_max_cycle_time(json_dict) / sample_interval if len(df) != last_checked else 0 # 比較用にきりのいいところ(設定された最大周期)まで前オフセット
    first_ignore = find_max_cycle_time(json_dict) / sample_interval # ログの最初の部分は判定しない(範囲は設定された最大周期とする)
    checking_range = max(last_checked - head_offset, first_ignore) # 「新規データ-前オフセット」から最後まで抽出　監視始めなら最初の行から前オフセット
    new_data = df.iloc[int(checking_range):].copy() # 新規データ+前オフセットを抽出(元のdfを変更しないようにcopyする)
    # print(f"checking_range: {checking_range}")
    # print(f"Head Offset: {head_offset}")
    # print(new_data)

    # NG情報保存用
    alert_rows = pd.DataFrame() # NG行を保存しておく
    alert_message = [] # NGメッセージを保存しておく
    alert_type = ["測定値NG", "HIGH時間NG", "LOW時間NG", "MID時間NG", "状態変化NG"] # NGの種類

    # メールアドレスの取得
    mail = json_dict.get("email")
    #print(f'Email: {mail}')

    # jsonファイルに書かれている全ての閾値設定でチェック
    for threshold in json_dict.get("thresholds", []): 

        try:

            channel = 'CH' + threshold.get("channel") # チャンネル名

            # 監視対象のCHがログに存在するときだけ処理
            if channel in new_data.columns and not new_data[channel].empty:

                # 閾値・判別データの取得
                border = threshold.get("border") # HIGH/LOW電圧の値
                time_high = threshold.get("time_high") # 閾値：HIGH電圧の継続時間
                time_low = threshold.get("time_low") # 閾値：LOW電圧の継続時間
                time_mid = threshold.get("time_mid")  # 閾値：中間電圧の継続時間
                value_alltime = threshold.get("value_alltime") # 閾値：全体を通した値

                # 中間電圧の継続時間maxが未設定の場合はHIGHとLOWの合計を設定(1周期ぶんの長さ)
                # if time_mid.get("max") is None and time_high.get("max") is not None and time_low.get("max") is not None:
                #     time_mid["max"] = time_high.get("max") + time_low.get("max")

                # new_dataを成形
                if new_data[channel].dtype == object:
                    new_data[channel] = new_data[channel].str.replace(' ', '') # 文字列の列のみ空白削除

                new_data[channel] = pd.to_numeric(new_data[channel], errors='coerce') # 数値に変換(数値データ以外はNaNにする)
                #new_data = new_data.dropna(subset=[channel]) # NaN除外
                #print(new_data[channel])

                # 矩形波の比較用マスクを作成
                if border is not None:

                    # 状態を符号化する関数
                    def voltage_state(v): # HIGH=1, LOW=0, 中間値はnp.nanにする
                        if pd.isna(v):
                            return np.nan
                        if v >= border["HIGH"]:
                            return 1  # HIGH
                        elif v <= border["LOW"]:
                            return 0  # LOW
                        else:
                            return -1  # MID

                    # 状態比較用マスク＆状態ID
                    states = new_data[channel].apply(voltage_state) # HIGH/LOW判定用の状態列作成（HIGH=1, LOW=0, 中間値は-1）
                    state_change = states != states.shift(1) # 状態変化があったところだけTrueにする
                    segment_id = state_change.cumsum() # それぞれの連続した区間にIDを付与

                    # サイクル数ID
                    low_to_high = (states.shift(1) == 0) & (states == 1) # LOW→HIGHに変化した箇所を検出
                    cycle_id = low_to_high.cumsum() # cycle_idを初期化（最初は0）
                    cycle_id = cycle_id.reindex(new_data.index, fill_value=0) # 最初のサイクル起点前は0、それ以降は1,2,...

                    # 状態遷移の推移
                    segment_states = states.groupby(segment_id).first() # 状態遷移を順番に取得
                    state_transitions = segment_states[segment_states != -1].astype(int).values # MIDは除外してHIGH/LOWのみにする
                    #np.set_printoptions(threshold=np.inf)
                    #print(state_transitions)

                    # 同じ状態の継続時間
                    segment_lengths = states.groupby(segment_id).transform('count') # 各連続区間の長さ(サンプル数)を追加
                    segment_time = segment_lengths * sample_interval # サンプル数→秒に変換

                    # 波形をきりのいい範囲で抽出するためのマスク
                    valid_range_mask = pd.Series([False]*len(new_data), index=new_data.index) # 判定対象のマスクを作成（全てFalseで初期化）
                    state_change_idx = new_data.index[state_change] # 状態変化が起きたインデックス（行番号）を取得 ※最初の状態も含まれる
                    if len(state_change_idx) > 2 and border is not None: # 状態が3つ以上、かつ閾値が設定されている場合
                        start_idx = state_change_idx[1] # 判定範囲の開始インデックス
                        end_idx = state_change_idx[-1] # 判定範囲の終了インデックス
                        valid_range_mask = (new_data.index >= start_idx) & (new_data.index < end_idx) # 判定対象のマスクを作成（開始〜終了の範囲のみTrue）

                    # print(f"Valid Range Data:\n{new_data[valid_range_mask]}")

                # サイクル数を追加
                if border is not None:
                    new_data.insert(0, 'サイクル数', cycle_id.loc[new_data.index])
                else:
                    new_data.insert(0, 'サイクル数', 0)

                # テスト出力用
                # if border is not None:
                #     tmp = pd.concat([new_data.copy(), states, state_change, segment_id, segment_time], axis=1)
                #     tmp.to_csv(f'{local_base_dir}/{logger_name}/test.csv', encoding='utf-8-sig')

                # 1.測定値の閾値判定
                if value_alltime.get("min") is not None:
                    new_data.loc[new_data[channel] < value_alltime.get("min"), "測定値NG"] = "閾値以上"
                if value_alltime.get("max") is not None:
                    new_data.loc[new_data[channel] > value_alltime.get("max"), "測定値NG"] = "閾値以下"

                # 矩形波のみ適用
                if border is not None:

                    # 2.HIGH状態の連続時間判定
                    high_mask = (states == 1)
                    if time_high.get("min") is not None:
                        new_data.loc[high_mask & (segment_time < time_high.get("min")) & state_change & valid_range_mask, "HIGH時間NG"] = "閾値以下"
                    if time_high.get("max") is not None:
                        new_data.loc[high_mask & (segment_time > time_high.get("max")) & state_change & valid_range_mask, "HIGH時間NG"] = "閾値以上"

                    # 3.LOW状態の連続時間判定
                    low_mask = (states == 0)
                    if time_low.get("min") is not None:
                        new_data.loc[low_mask & (segment_time < time_low.get("min")) & state_change & valid_range_mask, "LOW時間NG"] = "閾値以下"
                    if time_low.get("max") is not None:
                        new_data.loc[low_mask & (segment_time > time_low.get("max")) & state_change & valid_range_mask, "LOW時間NG"] = "閾値以上"

                    # 4.中間電圧の連続時間判定
                    mid_mask = (states == -1)
                    if time_mid.get("min") is not None:
                        new_data.loc[mid_mask & (segment_time < time_mid.get("min")) & state_change, "MID時間NG"] = "閾値以下"
                    if time_mid.get("max") is not None:
                        new_data.loc[mid_mask & (segment_time > time_mid.get("max")) & state_change, "MID時間NG"] = "閾値以上"

                    # 5.状態遷移判定(HIGHとLOWが交互になっているか)
                    ng_indices = [] # NGになったsegment_idをここに格納
                    if len(state_transitions) > 1: 
                        for i in range(1, len(state_transitions)):
                            if state_transitions[i] == state_transitions[i-1]: # 連続して同じ状態が続いているとみなしNG
                                ng_indices.append(i-1) # NGになったsegment_idを保存
                    else: # 状態が1種類しかない(状態が変化していない)場合はNG
                        ng_indices.append(1) # 最初のsegment_idを保存

                    # テスト用print
                    # print(f"state_transitions: {state_transitions}")
                    # print(f"ng_indices: {ng_indices}")
                    # # print(segment_id)
                    # print("")

                    new_data.loc[(segment_id.isin(ng_indices)) & state_change, "状態変化NG"] = "状態変化NG"

                # まだ追加されていないNG種類がある場合は、空の列を追加する(エラー防止)
                for col in alert_type:
                    if col not in new_data.columns:
                        new_data[col] = np.nan

                # NG格納用の列に文字列が入っていた場合は、alert_messageにNG種類に応じたエラー文とその文字列を追加
                for col in alert_type:
                    if col in new_data.columns and new_data[col].notna().any():
                        alert_message.append(f"[{channel}] {col}")

                # NG行をalert_rowsに追加
                ng_rows = new_data[new_data[alert_type].notna().any(axis=1)].copy() # NG行
                if not ng_rows.empty:
                    #ng_rows['NGチャンネル'] = channel
                    ng_rows.insert(0, 'NGチャンネル', channel) # NGチャンネル名
                    alert_rows = pd.concat([alert_rows, ng_rows], axis='index')

                # NGの場合グラフ作成
                # if not alert_rows.empty:
                #     filename_time = f"[{name}]" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                #     png_path = os.path.join(local_base_dir, folder_path, f'NGgraph_{filename_time}.png')
                #     create_graph_from_log(new_data["番号"], new_data[channel], png_path)
                #     print(f"Graph created at: {png_path}")

            # データのクリア(次のチャンネルで使うため)
            if 'サイクル数' in new_data.columns:
                new_data = new_data.drop('サイクル数', axis=1) # サイクル数の列を削除

        # 例外処理
        except Exception as e: 
            print("ERROR: "+str(e))
            print("TYPE: "+str(type(e)))
            print(f'MESSAGE:\n----------\n{traceback.format_exc()}----------')
            write_error_log(f'monitor_threshold({logger_name})-threshold', traceback.format_exc())

    # 閾値超過した場合
    if not alert_rows.empty:
    
        # 表示用に加工
        alert_rows = alert_rows.loc[:, (alert_rows != 0).any(axis=0)] # 全部ゼロの列は削除
        alert_rows = alert_rows.loc[:, (alert_rows.notna()).any(axis=0)] # 全部NAの列は削除
        alert_rows = alert_rows.loc[:, ~alert_rows.columns.str.contains('Alarm') & (alert_rows.columns != 'NA')] # アラーム列などは削除

        # テスト用print
        print(f"alert message:\n{'\n'.join(alert_message)}\n")
        print(f"alert_rows:\n{alert_rows}\n")

        # メール通知
        if logger_alert_flg[logger_name] == False:

            print(f"[{logger_name}] <<<<< Alert! log data exceeded the threshold >>>>>>")

            # if debug == False:
            #print(f"Alert rows:\n{alert_rows}")

            if debug == False:
                send_mail(SUBJECT='【自動送信】データロガー アラート',
                            BODY=f'''データロガー{logger_name}で閾値NGになりました。
                            <br>【NG内容】
                            <br>{"<br>".join(alert_message)}
                            <br>
                            <br>【NG発生箇所】
                            <br>{alert_rows.to_html(index=False)}''',
                            SENDER='自動送信システム',
                            FROM='alert@info.tokai-rika.co.jp',
                            RECIPIENT='RECIPIENT',
                            TO=mail, # メールアドレスはリスト形式で入力
                            )
                print(f"Mail sent: {mail}")

        # 前回とログファイルが同じなら再アラートしない
        else:
            print(f"[{logger_name}] Exceeded threshold but triggered previously (no alert)")

        # アラート発動したら、以降はメール送信しない(新しくログファイルが作成されるまで)
        logger_alert_flg[logger_name] = True 

    # 閾値OKの場合はメッセージ表示
    else:
        #print(f"[{logger_name} {channel}] Threshold OK ")
        print(f"{logger_name} Threshold OK ")

    # 最終チェック行数を更新
    checked_lines[logger_name] = len(df)
    print(f"current checked line: {checked_lines[logger_name]}")

    # 今回のログファイルパスを保存(フラグ判定用)
    previous_local_path[logger_name] = local_path

    # --- 状態をファイルに保存 ---
    save_json(
        status_path,
        {
            "checked_lines": checked_lines[logger_name],
            "logger_alert_flg": logger_alert_flg[logger_name],
            "previous_local_path": previous_local_path[logger_name]
        }
    )

# 関数：エラーログを書き込む
def write_error_log(location, error_message):
    os.makedirs(log_dir, exist_ok=True)
    now = datetime.datetime.now()
    log_filename = now.strftime('%Y%m') + '.csv'
    log_path = os.path.join(log_dir, log_filename)
    log_line = f'{now.strftime("%Y-%m-%d %H:%M:%S")},{location},"{error_message.replace(chr(10), " ").replace(chr(13), " ")}"\n'
    with open(log_path, 'a', encoding='utf-8-sig') as f:
        f.write(log_line)

if __name__ == '__main__':

    while True:

        for name in logger_server_dic.keys():

            try:
                print(f"\n[{name}] " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                # 1.ログファイルのバックアップ
                backup_result = backup_log(name)

                # 2.閾値監視
                if backup_result:
                    monitor_threshold(name)
                else:
                    print(f"WARNING -> Skipping threshold check for {name} (backup failed)")

            except Exception as e: # 例外処理
                print("ERROR: "+str(e))
                print("TYPE: "+str(type(e)))
                print(f'MESSAGE:\n----------\n{traceback.format_exc()}----------')
                write_error_log(f'__main__({name})', traceback.format_exc())

        if not debug:
            print("Waiting for 60 seconds...")
            time.sleep(60) # 60秒待機
        else:
            print("Waiting for 5 seconds...(debug)")
            time.sleep(5) # 5秒待機(デバッグ)