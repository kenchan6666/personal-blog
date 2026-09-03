from viola.api.server import _timeout_notice


def test_timeout_notice_tells_the_owner_the_turn_stopped() -> None:
    text = _timeout_notice(120)
    assert "120" in text
    assert "已停止" in text
