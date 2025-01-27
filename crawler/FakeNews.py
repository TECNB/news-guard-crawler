import os
import asyncio
import json
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.async_dispatcher import SemaphoreDispatcher
from crawl4ai import CrawlerMonitor, DisplayMode
from crawl4ai import RateLimiter
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 获取 API 密钥和基础 URL
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")

# 定义数据提取的结构化模式
class FakeNews(BaseModel):
    headline: str  # 虚假新闻标题
    field: str      # 虚假新闻领域分类
    truth: str   # 虚假新闻内容
    source: str    # 虚假新闻来源
    measures: str     # 虚假新闻注意事项
    date: str  # 新闻发布日期

# 读取本地 JSON 文件的内容
def load_fake_news_links_json():
    try:
        with open('links.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"Error loading JSON file: {e}")

async def fetch_and_process_link(result, date):
    if result.success:
        # 检查是否有有效的提取内容
        if not result.extracted_content:
            print(f"警告：链接提取结果为空，链接：{result.url}")
            return []

        try:
            # 解析提取到的 JSON 数据
            data = json.loads(result.extracted_content)
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误，链接：{result.url}, 错误信息：{str(e)}")
            return []

        # 移除 'error' 字段
        cleaned_data = [{k: v for k, v in item.items() if k != 'error'} for item in data]

        # 添加日期属性
        for item in cleaned_data:
            item['date'] = date

        print(f"提取到的虚假新闻：{cleaned_data}")
        return cleaned_data
    else:
        print(f"错误：{result.error_message}, 链接：{result.url}")
        return []

async def main():
    # 读取 JSON 文件中的链接和日期
    links_data = load_fake_news_links_json()

    # 定义 LLM 提取策略
    llm_strategy = LLMExtractionStrategy(
        provider="deepseek/deepseek-chat",  # 使用 deepseek 进行提取
        api_token=api_key,  # DeepSeek 提供的 API Key
        api_base=base_url,
        schema=FakeNews.model_json_schema(),  # 指定提取的 JSON 模式
        extraction_type="schema",  # 使用 schema 提取模式
        instruction="从页面中提取所有谣言以及误区，包括标题、领域分类、真相、来源和注意事项。",  # 提示模型需要提取的内容
        chunk_token_threshold=1000,  # 每个分块的最大 token 数
        overlap_rate=0.1,  # 分块的重叠率，确保上下文连续
        apply_chunking=True,  # 启用分块
        input_format="html",  # 使用清理后的 HTML 数据作为输入
        extra_args={"temperature": 0.1, "max_tokens": 1000},  # LLM 的额外参数
        verbose=True  # 输出详细信息
    )

    # 配置爬虫
    crawl_config = CrawlerRunConfig(
        extraction_strategy=llm_strategy,  # 使用定义好的提取策略
        cache_mode=CacheMode.BYPASS  # 每次都重新获取最新数据
    )

    # 浏览器配置
    browser_cfg = BrowserConfig(headless=True)  # 使用无头浏览器模式

    # 设置 RateLimiter
    rate_limiter = RateLimiter(
        base_delay=(0.1, 0.2),  # 设置请求间隔为1到2秒，加速请求
        max_delay=15.0,         # 最大等待15秒
        max_retries=5,          # 最大重试次数为5次
        rate_limit_codes=[429, 503]  # 如果返回429或503状态码，则会重试
    )

    # 配置 CrawlerMonitor
    monitor = CrawlerMonitor(
        max_visible_rows=15,           # 显示最大行数
        display_mode=DisplayMode.DETAILED  # 显示详细模式
    )

    # 配置 SemaphoreDispatcher
    dispatcher = SemaphoreDispatcher(
        max_session_permit=30,          # 增加最大并发任务数至 30
        rate_limiter=rate_limiter,      # 使用上面定义的RateLimiter
        monitor=monitor                 # 使用监控器
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 使用 arun_many 批量爬取所有链接
        all_news = []  # 存储所有提取的新闻

        # 创建所有链接的请求任务
        results = await crawler.arun_many(
            urls=[link_data['link'] for link_data in links_data],
            config=crawl_config,
            dispatcher=dispatcher  # 使用自定义的dispatcher
        )

        # 处理每个结果并提取新闻数据
        for result, link_data in zip(results, links_data):
            news_data = await fetch_and_process_link(result, link_data['date'])
            all_news.extend(news_data)

        # 保存提取到的数据
        output_file = "./data/fake_news.json"
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(all_news, file, indent=4, ensure_ascii=False)
        print(f"提取到的虚假新闻已保存到 {output_file}")

        # 显示使用情况统计
        llm_strategy.show_usage()

# 程序入口
if __name__ == "__main__":
    asyncio.run(main())