from flask import Flask, render_template, redirect, url_for, request, send_file, session
from datetime import datetime
import sqlite3
import pandas as pd
import io
import threading
import webbrowser
import os
import License_checker

app = Flask(__name__)
app.secret_key = 'secret!'

DB_PATH = None

def get_db_path():
    global DB_PATH
    project = session.get('project')
    chamber = session.get('chamber')

    if project and chamber:
        DB_PATH = f'X:/06 SAR/03. Personal/25. Taehun Kim/Debugging_DB/{project}/SAR{chamber}/database.db'
        init_db()

def init_db():
    print("DB_PATH:", DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS time_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              start_time TEXT,
              stop_time TEXT,
              debugging_time TEXT,
              reason TEXT,
              person TEXT,
              tech TEXT,
              remark TEXT)''')
    conn.commit()
    conn.close()

@app.route('/start', methods=['POST'])
def start():
    tech = request.form.get('tech', '')
    person = request.form.get('person', '')
    reason = request.form.get('reason', '')
    remark = request.form.get('remark', '')
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO time_log (start_time, reason, person, tech, remark) VALUES (?, ?, ?, ?, ?)", (now, reason, person, tech, remark))
    conn.commit()
    conn.close()
    return redirect(url_for('main'))

@app.route('/stop')
def stop():
   now = datetime.now().strftime("%Y-%m-%d %H:%M")
   conn = sqlite3.connect(DB_PATH)
   c = conn.cursor()
   # stop_time이 없는 가장 최근 row 조회
   c.execute('SELECT id, start_time FROM time_log WHERE stop_time IS NULL ORDER BY id DESC LIMIT 1')
   row = c.fetchone()
   if row:
       time_log_id = row[0]
       start_time_str = row[1]
       start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
       stop_time = datetime.strptime(now, "%Y-%m-%d %H:%M")
       duration = stop_time - start_time
       total_seconds = int(duration.total_seconds())
       hours = total_seconds // 3600
       minutes = (total_seconds % 3600) // 60

       duration_str = f"{hours}시간:{minutes}분" if hours > 0 else f"{minutes}분"
       c.execute('''
           UPDATE time_log
           SET stop_time = ?, debugging_time = ?
           WHERE id = ?
       ''', (now, duration_str, time_log_id))
       conn.commit()
   conn.close()
   return redirect(url_for('main'))

@app.route('/export')
def export_excel():
   conn = sqlite3.connect(DB_PATH)
   df = pd.read_sql_query("SELECT tech, person, reason, remark, debugging_time FROM time_log WHERE debugging_time IS NOT NULL", conn)
   conn.close()
   # 엑셀 파일로 변환
   output = io.BytesIO()
   with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
       df.to_excel(writer, index=False, sheet_name='기록')
   output.seek(0)
   return send_file(output,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name='Debugging 내역.xlsx')

@app.route('/', methods=['GET', 'POST'])
def setup():
    if request.method == 'POST':
        session['project'] = request.form['project']
        session['chamber'] = request.form['chamber']
        return redirect(url_for('main'))
    return render_template('setup.html')

@app.route('/main')
def main():
    get_db_path()
    if DB_PATH == None:
        return redirect(url_for('setup'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM time_log ORDER BY id DESC')
    logs = c.fetchall()
    conn.close()
    return render_template('index.html', logs=logs)

@app.route('/reset')
def reset():
   session.clear()
   return redirect(url_for('setup'))

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    # 웹 브라우저에서 열기
    license_manager = License_checker.OnlineLicenseManager()
    
    if not license_manager.validate_license():
        print("라이센스가 유효하지 않습니다.")

    else:
        threading.Timer(1.0, open_browser).start()
        app.run()