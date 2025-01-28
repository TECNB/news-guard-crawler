import os
import json
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy

# 加载环境变量
load_dotenv()

# 定义数据提取的结构化模式
class FakeNews(BaseModel):
    headline: str  # 新闻标题
    field: str      # 新闻领域分类
    source: str    # 新闻来源
    date: str  # 新闻发布日期
    predicted_fake_headline: str  # 大模型预测的虚假新闻标题

async def main():
    # 优化后的浏览器配置
    browser_cfg = BrowserConfig(
        headless=True,  # 使用无头浏览器模式
    )

    # 优化后的爬虫配置
    crawl_config = CrawlerRunConfig(
        extraction_strategy=LLMExtractionStrategy(
            provider="deepseek/deepseek-chat",
            api_token=os.getenv("OPENAI_API_KEY"),
            api_base=os.getenv("OPENAI_BASE_URL"),
            schema=FakeNews.model_json_schema(),
            extraction_type="schema",
            instruction="从页面中提取新闻总排行中的这10条新闻，包括标题、领域分类、来源媒体、发布时间和大模型预测的虚假新闻标题。",
            chunk_token_threshold=1500,  # 降低分块token阈值
            overlap_rate=0.3,  # 增加重叠率保证上下文连贯
            apply_chunking=True,
            verbose=True,
            extra_args={"temperature": 0.1, "max_tokens": 1000},
        ),
        css_selector="#Con11",  # 选择新闻总排行的区域
        cache_mode=CacheMode.BYPASS,
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        url = "https://news.sina.com.cn/hotnews/"
        result = await crawler.arun(url=url, config=crawl_config)

        if result.success:
            output_file = "../data/hot_news.json"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(json.loads(result.extracted_content), file, indent=4, ensure_ascii=False)
            print(f"数据已保存到 {output_file}")
        else:
            print(f"爬取失败: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())