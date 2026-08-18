#!/usr/bin/env python3
"""One-time Kakao OAuth: opens browser for consent, captures the code on
localhost, exchanges it for tokens, and saves them (tokens.json + state/tokens.enc).

Prereq: on developers.kakao.com the app must have
  - 카카오 로그인 ON, Redirect URI: http://localhost:8899/callback
  - 동의항목: 카카오톡 메시지 전송(talk_message)
Run: KAKAO_REST_KEY=xxxx [KAKAO_CLIENT_SECRET=yyyy] [TOKEN_KEY=zzz] python3 get_token.py
"""
import http.server
import os
import threading
import urllib.parse
import webbrowser

import requests

import kakao

PORT = 8899
REDIRECT = f"http://localhost:{PORT}/callback"
code_holder = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(q.query))
        if q.path == "/callback" and "code" in params:
            code_holder["code"] = params["code"]
            body = "<h2>완니: 인증 완료. 이 창을 닫으세요.</h2>".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


def main():
    rest_key = os.environ.get("KAKAO_REST_KEY") or input("KAKAO REST API 키: ").strip()
    os.environ["KAKAO_REST_KEY"] = rest_key
    auth_url = ("https://kauth.kakao.com/oauth/authorize?response_type=code"
                f"&client_id={rest_key}&redirect_uri={urllib.parse.quote(REDIRECT)}"
                "&scope=talk_message")
    print("브라우저에서 동의를 진행하세요:\n ", auth_url)
    webbrowser.open(auth_url)
    srv = http.server.HTTPServer(("localhost", PORT), Handler)
    srv.serve_forever()  # shut down by handler after code arrives

    data = {"grant_type": "authorization_code", "client_id": rest_key,
            "redirect_uri": REDIRECT, "code": code_holder["code"]}
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        data["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    r = requests.post(kakao.KAUTH, data=data, timeout=30)
    r.raise_for_status()
    j = r.json()
    tok = {"access_token": j["access_token"], "refresh_token": j["refresh_token"]}
    kakao.save_tokens(tok)
    print("scope:", j.get("scope"))
    print("저장 완료:", kakao.PLAIN_PATH,
          "+ state/tokens.enc" if os.environ.get("TOKEN_KEY") else "(TOKEN_KEY 미설정 — enc 생략)")


if __name__ == "__main__":
    main()
