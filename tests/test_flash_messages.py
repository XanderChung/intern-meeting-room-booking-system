import pytest
from flask import flash, redirect, url_for

from app import app


app.config.update(TESTING=True, SECRET_KEY="test-only-key")


@app.get("/_test/flash/<category>")
def trigger_flash_for_test(category):
    flash("Flash message test.", category)
    return redirect(url_for("rooms_page"))


@pytest.mark.parametrize(
    ("category", "notice_class", "role"),
    [
        ("success", "notice--success", "status"),
        ("error", "notice--error", "alert"),
    ],
)
def test_flash_messages_render_after_redirect(category, notice_class, role):
    response = app.test_client().get(
        f"/_test/flash/{category}",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Flash message test." in response.data
    assert f'class="notice {notice_class}"'.encode() in response.data
    assert f'role="{role}"'.encode() in response.data