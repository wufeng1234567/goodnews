"""Trafilatura extraction smoke test on a static HTML fixture."""

from app.crawler.extract import extract_article_from_html

SAMPLE_HTML = """
<!doctype html>
<html lang="zh">
<head>
  <meta property="og:title" content="埃菲尔铁塔简介">
  <meta property="article:published_time" content="2026-01-02">
</head>
<body>
  <nav>首页 新闻 体育</nav>
  <article>
    <h1>埃菲尔铁塔简介</h1>
    <p>埃菲尔铁塔位于法国巴黎，是当地著名的地标建筑。</p>
    <p>它建于十九世纪，每年吸引大量游客前来参观。</p>
    <p>铁塔周边还有战神广场和塞纳河等著名景点。</p>
  </article>
</body>
</html>
"""


def test_extracts_body_and_metadata() -> None:
    result = extract_article_from_html(SAMPLE_HTML, "https://example.com/eiffel")
    assert "埃菲尔铁塔" in result["text"]
    assert "巴黎" in result["text"]
    assert result["title"] == "埃菲尔铁塔简介"
