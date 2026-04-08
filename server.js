const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.static('public'));
app.use(express.json());

// 读取数据
function readData(file) {
  try {
    return JSON.parse(fs.readFileSync(path.join(__dirname, 'data', file), 'utf8'));
  } catch (e) {
    return [];
  }
}

// 写入数据
function writeData(file, data) {
  fs.writeFileSync(path.join(__dirname, 'data', file), JSON.stringify(data, null, 2));
}

// 获取设置
app.get('/api/settings', (req, res) => {
  const settings = readData('settings.json');
  res.json(settings);
});

// 更新设置
app.post('/api/settings', (req, res) => {
  writeData('settings.json', req.body);
  res.json({ success: true });
});

// 获取成员
app.get('/api/members', (req, res) => {
  const members = readData('members.json');
  res.json(members);
});

// 添加成员
app.post('/api/members', (req, res) => {
  const members = readData('members.json');
  members.push(req.body);
  writeData('members.json', members);
  res.json({ success: true });
});

// 签到
app.post('/api/checkin', (req, res) => {
  const { name, team, lat, lng } = req.body;
  const settings = readData('settings.json');
  if (settings.length === 0) {
    return res.json({ success: false, message: '位置未设置' });
  }
  const center = settings[0];
  const distance = getDistance(lat, lng, center.lat, center.lng);
  if (distance > center.radius) {
    return res.json({ success: false, message: '不在指定范围内' });
  }
  const checkins = readData('checkins.json');
  checkins.push({ name, team, lat, lng, time: new Date().toISOString() });
  writeData('checkins.json', checkins);
  res.json({ success: true });
});

// 获取签到
app.get('/api/checkins', (req, res) => {
  const checkins = readData('checkins.json');
  res.json(checkins);
});

// 距离计算
function getDistance(lat1, lng1, lat2, lng2) {
  const R = 6371000; // 地球半径米
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng/2) * Math.sin(dLng/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

app.listen(3000, () => console.log('Server running on port 3000'));