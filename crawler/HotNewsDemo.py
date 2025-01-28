import os
import asyncio
from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

# 加载环境变量
load_dotenv()

# 定义爬虫配置
async def main():

    # 等待策略
    js_wait_for = """
    js:() => {
        let element = document.querySelector('#Con11 > table > tbody > tr:nth-child(4) > td.ConsTi');
        if (element !== null) {
            console.log("元素已加载完毕，开始抓取数据...");
            return true;
        } else {
            console.log("未加载该元素，继续等待...");
            return false;
        }
    }
    """

    # 配置爬虫
    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,  # 每次都重新获取最新数据
        wait_for=js_wait_for,  # 等待页面加载完成
    )

    # 浏览器配置
    browser_cfg = BrowserConfig(headless=False)  # 使用无头浏览器模式,设置浏览器不自动关闭

    # 创建爬虫对象并启动爬取
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        url = "https://news.sina.com.cn/hotnews/"  # 替换为目标新闻网站 URL

        result = await crawler.arun(url=url, config=crawl_config)

        if result.success:
            # 确保内容不为 None
            markdown_content = result.markdown

            if markdown_content:
                # 保存 Markdown 格式的文件
                markdown_file = "../data/hot_news.md"

                # 确保目标文件夹存在，如果不存在则创建
                os.makedirs(os.path.dirname(markdown_file), exist_ok=True)

                with open(markdown_file, "w", encoding="utf-8") as file:
                    file.write(markdown_content)  # 将提取的 Markdown 内容保存到文件
                print(f"提取到的热点新闻已保存为 Markdown 文件: {markdown_file}")
            else:
                print("爬取失败，未提取到任何内容。")
        else:
            print(f"爬取失败: {result.error_message}")

# 程序入口
if __name__ == "__main__":
    asyncio.run(main())