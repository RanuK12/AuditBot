import pytest
from spider import Spider

def test_spider_walk():
    spider = Spider()
    assert spider.walk() == "walking"
