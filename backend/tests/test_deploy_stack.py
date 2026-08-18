"""
Ticket: #12 Single-VM nginx Compose.
Guards the deploy files that must exist for one-host nginx + app + data stores.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_prod_compose_defines_frontend_api_mongo_redis_nginx():
    compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")
    for name in ("mongo:", "redis:", "api:", "web:", "nginx:"):
        assert name in compose
    assert "80:80" in compose


def test_nginx_proxies_site_and_api():
    conf = (ROOT / "deploy" / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_pass http://api:8000/api/" in conf
    assert "proxy_pass http://web:3000" in conf
    assert "Authorization" in conf
