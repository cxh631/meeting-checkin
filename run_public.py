from pyngrok import ngrok
from app import app

if __name__ == '__main__':
    public_url = ngrok.connect(3000, "http").public_url
    print(f"Public URL: {public_url}")
    print("本地应用已通过 ngrok 暴露到公网，扫码可访问此地址。")
    try:
        app.run(host='0.0.0.0', port=3000)
    finally:
        ngrok.kill()
