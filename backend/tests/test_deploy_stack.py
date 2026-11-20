"""
Ticket: #12 Single-VM nginx Compose.
Guards the deploy files that must exist for one-host nginx + app + data stores.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_prod_compose_defines_frontend_api_mongo_redis_nginx():
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    for name in ("mongo:", "redis:", "api:", "web:", "nginx:", "certbot:", "taiko:"):
        assert name in compose
    assert "80:80" in compose
    assert "443:443" in compose
    # Opt-in so existing --prod --pull deploys do not require a taiko image.
    assert 'profiles: ["taiko"]' in compose
    assert "mem_limit: 64m" in compose


def test_nginx_proxies_site_and_api():
    proxy = (ROOT / "deployment" / "nginx" / "proxy.inc").read_text(encoding="utf-8")
    http = (ROOT / "deployment" / "nginx" / "http.conf").read_text(encoding="utf-8")
    ssl = (ROOT / "deployment" / "nginx" / "ssl.conf").read_text(encoding="utf-8")
    assert "location = /" in proxy
    assert "return 302 /zh-Hant" in proxy
    assert "proxy_pass http://api:8000/api/" in proxy
    assert "proxy_pass http://web:3000" in proxy
    assert "location /taiko/" in proxy
    assert "proxy_pass http://taiko:8080/" in proxy
    assert "location = /taiko" in proxy
    assert "Authorization" in proxy
    assert "acme-challenge" in http
    assert "listen 443 ssl" in ssl
    assert "/etc/letsencrypt/live/site/fullchain.pem" in ssl
