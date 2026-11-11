"""Offline parser tests for social platform adapters."""

from __future__ import annotations

from app.models.social import SocialFetchRequest, SocialPlatform
from app.platforms.base import detect_platform, parse_count
from app.platforms.bilibili import parse_bilibili_comment, parse_bilibili_video
from app.platforms.douyin import parse_douyin_comments, parse_douyin_content
from app.platforms.xiaohongshu import (
    parse_xhs_comments,
    parse_xhs_content,
)


def test_platform_detection_and_count_parser() -> None:
    assert detect_platform("https://www.bilibili.com/video/BV1gHWg6GEqj") is SocialPlatform.BILIBILI
    assert detect_platform("https://www.douyin.com/video/7388149561765760266") is SocialPlatform.DOUYIN
    assert detect_platform("https://www.xiaohongshu.com/explore/65422393000000001e022228") is SocialPlatform.XIAOHONGSHU
    assert parse_count("1.2万") == 12_000
    assert parse_count("10万+") == 100_000
    assert parse_count("3.4w") == 34_000
    assert parse_count(1234) == 1234


def test_social_request_extracts_url_from_share_text() -> None:
    request = SocialFetchRequest(
        url="复制打开抖音 https://www.douyin.com/video/7388149561765760266 一起看",
        max_comments=10,
    )
    assert request.url == "https://www.douyin.com/video/7388149561765760266"


def test_bilibili_video_and_comment_mapping() -> None:
    video = parse_bilibili_video(
        {
            "bvid": "BV1gHWg6GEqj",
            "aid": 117590970140555,
            "title": "测试视频",
            "desc": "视频简介",
            "pic": "https://example.com/cover.jpg",
            "pubdate": 1794370762,
            "duration": 201,
            "tname": "动画",
            "owner": {"mid": 123, "name": "测试UP"},
            "stat": {
                "view": 1184004,
                "vv": 1184004,
                "like": 78597,
                "reply": 7457,
                "share": 7262,
                "favorite": 22280,
                "coin": 32788,
                "danmaku": 3226,
            },
        }
    )
    assert video.title == "测试视频"
    assert video.metrics.view_count == 1_184_004
    assert video.duration_seconds == 201
    assert video.metrics.total_engagement > 0

    comment = parse_bilibili_comment(
        {
            "rpid": 1,
            "member": {"mid": "2", "uname": "评论者", "avatar": "https://example.com/a.jpg"},
            "content": {"message": "这条评论很有用"},
            "like": 3416,
            "rcount": 4,
            "ctime": 1794370762,
        },
        content_id="BV1gHWg6GEqj",
    )
    assert comment.text == "这条评论很有用"
    assert comment.like_count == 3416
    assert comment.reply_count == 4


def test_douyin_detail_and_comments_mapping() -> None:
    aweme = {
        "aweme_id": "7388149561765760266",
        "desc": "这是抖音视频标题 #影视解说",
        "create_time": 1790179142,
        "duration": 201000,
        "text_extra": [{"hashtag_name": "影视解说"}],
        "author": {
            "uid": "85832802810",
            "sec_uid": "MS4wSEC",
            "unique_id": "donglegeqiang",
            "nickname": "糖叔不说剧",
            "follower_count": 1035832,
        },
        "statistics": {
            "digg_count": 1135614,
            "comment_count": 35977,
            "share_count": 199136,
            "collect_count": 108095,
            "play_count": 0,
        },
        "video": {
            "duration": 201000,
            "cover": {"url_list": ["https://example.com/douyin.jpg"]},
        },
    }
    content = parse_douyin_content(aweme)
    assert content.title == "这是抖音视频标题 #影视解说"
    assert content.author.name == "糖叔不说剧"
    assert content.metrics.like_count == 1_135_614
    assert content.metrics.comment_count == 35977
    assert content.duration_seconds == 201

    comments, has_more = parse_douyin_comments(
        [
            {
                "comments": [
                    {
                        "cid": "c1",
                        "text": "好看",
                        "digg_count": 8,
                        "reply_comment_total": 1,
                        "create_time": 1790179142,
                        "user": {"uid": "u1", "nickname": "用户一"},
                    }
                ],
                "has_more": 1,
            }
        ],
        content_id=content.content_id,
        max_comments=10,
    )
    assert len(comments) == 1
    assert comments[0].author_name == "用户一"
    assert has_more is True


def test_xhs_note_and_comment_mapping() -> None:
    note = parse_xhs_content(
        {
            "note_id": "65422393000000001e022228",
            "display_title": "一篇小红书笔记",
            "desc": "正文内容",
            "type": "normal",
            "user": {"user_id": "u1", "nickname": "小红书作者"},
            "interact_info": {
                "liked_count": "1.2万",
                "collected_count": "300",
                "comment_count": "45",
                "share_count": "12",
            },
        }
    )
    assert note.title == "一篇小红书笔记"
    assert note.metrics.like_count == 12_000
    assert note.author.name == "小红书作者"

    comments, has_more = parse_xhs_comments(
        [
            {
                "data": {
                    "comments": [
                        {
                            "id": "x1",
                            "content": "评论内容",
                            "like_count": "2万",
                            "sub_comment_count": 1,
                            "create_time": 1790179142000,
                            "user_info": {"user_id": "u2", "nickname": "评论者"},
                        }
                    ],
                    "has_more": False,
                }
            }
        ],
        content_id=note.content_id,
        max_comments=10,
    )
    assert len(comments) == 1
    assert comments[0].like_count == 20_000
    assert has_more is False
