from flask import Flask, request, jsonify, send_from_directory
import csv
import io
import json
import os
from datetime import datetime
import math
import uuid
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

app = Flask(__name__, static_folder='public', static_url_path='')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

os.makedirs(DATA_DIR, exist_ok=True)

def read_data(file):
    path = os.path.join(DATA_DIR, file)
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_data(file, data):
    path = os.path.join(DATA_DIR, file)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_id():
    return uuid.uuid4().hex


def normalize_members(members):
    changed = False
    for member in members:
        if 'id' not in member:
            member['id'] = generate_id()
            changed = True
        if 'activity_id' not in member:
            member['activity_id'] = 'default'
            changed = True
    if changed:
        write_data('members.json', members)
    return members


def ensure_default_activity():
    activities = read_data('activities.json')
    if not activities:
        default = {'id': 'default', 'name': '默认活动', 'created': datetime.now().isoformat()}
        activities.append(default)
        write_data('activities.json', activities)
    return activities

ensure_default_activity()

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/checkin')
def checkin_page():
    return send_from_directory('public', 'checkin.html')

@app.route('/checkin.html')
def checkin_html():
    return send_from_directory('public', 'checkin.html')

@app.route('/admin.html')
def admin():
    return send_from_directory('public', 'admin.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(read_data('settings.json'))

@app.route('/api/settings', methods=['POST'])
def post_settings():
    data = request.json
    write_data('settings.json', data)
    return jsonify({'success': True})

@app.route('/api/activities', methods=['GET'])
def get_activities():
    activities = read_data('activities.json')
    if not activities:
        activities = ensure_default_activity()
    return jsonify(activities)

@app.route('/api/activities', methods=['POST'])
def create_activity():
    data = request.json
    activities = read_data('activities.json')
    new_id = data.get('id') or f"activity-{int(datetime.now().timestamp())}"
    activity = {'id': new_id, 'name': data.get('name', '新活动'), 'created': datetime.now().isoformat()}
    activities.append(activity)
    write_data('activities.json', activities)
    return jsonify({'success': True, 'activity': activity})

@app.route('/api/members', methods=['GET'])
def get_members():
    activity_id = request.args.get('activity_id', 'default')
    members = normalize_members(read_data('members.json'))
    return jsonify([member for member in members if member.get('activity_id', 'default') == activity_id])

@app.route('/api/members', methods=['POST'])
def post_member():
    data = request.json
    activity_id = request.args.get('activity_id', 'default')
    member = {
        'id': generate_id(),
        'name': data.get('name'),
        'team': data.get('team'),
        'contact': data.get('contact', ''),
        'activity_id': activity_id
    }
    members = normalize_members(read_data('members.json'))
    members.append(member)
    write_data('members.json', members)
    return jsonify({'success': True})

@app.route('/api/members/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    members = normalize_members(read_data('members.json'))
    for index, member in enumerate(members):
        if str(member.get('id')) == str(member_id):
            deleted = members.pop(index)
            write_data('members.json', members)
            return jsonify({'success': True, 'deleted': deleted})
    return jsonify({'success': False, 'message': '成员不存在'})

@app.route('/api/import', methods=['POST'])
def import_members():
    activity_id = request.args.get('activity_id', 'default')
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到上传文件'})
    upload = request.files['file']
    if upload.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})
    if upload.filename.lower().endswith('.csv'):
        members, invalid = parse_csv(upload)
    elif upload.filename.lower().endswith('.pdf'):
        members, invalid = parse_pdf(upload)
    else:
        return jsonify({'success': False, 'message': '仅支持 CSV 或 PDF 文件'})

    saved = normalize_members(read_data('members.json'))
    existing = {(m.get('name'), m.get('team'), m.get('activity_id', 'default')) for m in saved}
    added = 0
    ignored = 0
    errors = []
    for member in members:
        name = member.get('name')
        team = member.get('team')
        if not name or not team:
            errors.append(f"缺少姓名或团队: {name}, {team}")
            continue
        if team not in ['运营', '硬件', '软件', '设计']:
            errors.append(f"无效团队: {team} (必须是运营/硬件/软件/设计)")
            continue
        key = (name, team, activity_id)
        if key in existing:
            ignored += 1
            continue
        member['activity_id'] = activity_id
        member['id'] = generate_id()
        saved.append(member)
        existing.add(key)
        added += 1
    write_data('members.json', saved)
    return jsonify({'success': True, 'added': added, 'ignored': ignored, 'errors': errors[:10]})

@app.route('/api/checkin', methods=['POST'])
def checkin_post():
    data = request.json
    activity_id = data.get('activity_id', 'default')
    name = data['name']
    team = data['team']
    lat = data['lat']
    lng = data['lng']
    settings = read_data('settings.json')
    if not settings:
        return jsonify({'success': False, 'message': '位置未设置'})
    center = settings[0]
    distance = get_distance(lat, lng, center['lat'], center['lng'])
    if distance > center['radius']:
        return jsonify({'success': False, 'message': '不在指定范围内'})
    checkins = read_data('checkins.json')
    checkins.append({
        'activity_id': activity_id,
        'name': name,
        'team': team,
        'lat': lat,
        'lng': lng,
        'time': datetime.now().isoformat()
    })
    write_data('checkins.json', checkins)
    return jsonify({'success': True})

@app.route('/api/checkins', methods=['GET'])
def get_checkins():
    activity_id = request.args.get('activity_id', 'default')
    return jsonify([c for c in read_data('checkins.json') if c.get('activity_id', 'default') == activity_id])

def parse_csv(upload):
    content = upload.read()
    # 尝试多种编码
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin1']
    text = None
    for encoding in encodings:
        try:
            text = content.decode(encoding, errors='ignore')
            if text.strip():  # 如果解码后有内容，说明编码正确
                break
        except:
            continue
    if not text:
        text = content.decode('utf-8', errors='ignore')

    rows = []
    invalid = 0
    reader = csv.reader(io.StringIO(text))
    for parts in reader:
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) < 2:
            invalid += 1
            continue
        rows.append({
            'name': parts[0],
            'team': parts[1],
            'contact': parts[2] if len(parts) > 2 else ''
        })
    return rows, invalid


def parse_pdf(upload):
    if PdfReader is None:
        raise RuntimeError('缺少 PDF 解析依赖，请安装 PyPDF2')
    content = upload.read()
    reader = PdfReader(io.BytesIO(content))
    raw = []
    for page in reader.pages:
        text = page.extract_text() or ''
        raw.append(text)
    text = '\n'.join(raw)
    return parse_text_rows(text)


def parse_text_rows(text):
    lines = [line.replace('，', ',').strip() for line in text.splitlines() if line.strip()]
    rows = []
    invalid = 0
    for line in lines:
        parts = [p.strip() for p in line.split(',') if p.strip()]
        if len(parts) < 2:
            invalid += 1
            continue
        rows.append({
            'name': parts[0],
            'team': parts[1],
            'contact': parts[2] if len(parts) > 2 else ''
        })
    return rows, invalid


def get_distance(lat1, lng1, lat2, lng2):
    R = 6371000  # 米
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', debug=debug, port=port)