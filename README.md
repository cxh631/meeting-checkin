# 会议签到系统

这是一个基于Flask的会议签到网页应用，支持地理位置验证和动态二维码。

## 功能

- 动态二维码生成（每分钟更新）
- 地理位置签到验证
- 团队管理（运营、硬件、软件、设计）
- 签到记录查看和筛选

## 运行

1. 安装依赖：`python3 -m pip install -r requirements.txt`
2. 本地运行：`python3 app.py`
3. 打开浏览器访问 `http://localhost:3000`

## 公网访问

如果你想让其他人扫码访问，可以运行：

```bash
python3 run_public.py
```

运行后会输出一个公网地址（ngrok 隧道），其他人可以通过该地址直接访问。

## 云部署

我建议使用 Render 部署，因为你已经有一个可用的 `Dockerfile`，并且 Render 支持直接从 GitHub 仓库部署。

### Render 部署步骤

1. 将项目提交到 GitHub：
   ```bash
git init
git add .
git commit -m "add meeting checkin app"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
2. 登录 Render，创建新服务：
   - 选择 `Web Service`
   - 选择 `Docker` 环境
   - 连接你的 GitHub 仓库
   - Render 会自动读取项目中的 `Dockerfile`
3. 你也可以直接在仓库根目录使用 `render.yaml` 配置，Render 会自动识别。

### 其他平台

如果你更倾向其他平台，也可使用以下方式：

- Docker：
  ```bash
docker build -t meeting-checkin .
docker run -p 3000:3000 meeting-checkin
```
- Heroku / Railway / DigitalOcean App Platform：
  ```bash
gunicorn -b 0.0.0.0:$PORT app:app --workers 2
```

- `Procfile` 已包含生产启动命令，适用于 Heroku 类平台。

## 页面

- `/` : 单页应用入口，包含数据仪表板、签到与管理
- `/checkin.html` : 自动重定向到单页入口的签到部分
- `/admin.html` : 自动重定向到单页入口的管理部分

## 数据

数据存储在 `data/` 文件夹中：
- `members.json` : 团队成员
- `checkins.json` : 签到记录
- `settings.json` : 位置设置