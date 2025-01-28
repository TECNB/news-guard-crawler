import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def main():
    config = CrawlerRunConfig(
        # e.g., first 30 items from Hacker News
        css_selector="#Con11"
    )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://news.sina.com.cn/hotnews/",
            config=config
        )
        print("Partial HTML length:", len(result.cleaned_html))
        print("Extracted content:", result.markdown)

if __name__ == "__main__":
    asyncio.run(main())