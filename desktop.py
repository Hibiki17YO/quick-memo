import webview
import logging

logger = logging.getLogger(__name__)


def create_window(url: str = "http://127.0.0.1:18080/api/editor-html"):
    window = webview.create_window(
        title="Quick Memo",
        url=url,
        width=420,
        height=380,
        on_top=True,
        background_color="#fafafa",
        min_size=(350, 280),
    )
    return window
