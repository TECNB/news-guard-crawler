import asyncio
import json
from crawl4ai import *
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def main():
    # 定义提取规则
    schema = {
        "name": "辟谣信息",
        "baseSelector": "ul#list li",  # 每一行是一个<li>元素
        "fields": [
            {
                "name": "date",
                "selector": "p.domPC",  # 日期位于<p>标签中
                "type": "text"
            },
            {
                "name": "link",
                "selector": "h2 a",  # 铯接位于<h2>标签中的<a>标签
                "type": "attribute",
                "attribute": "href"  # 提取href属性
            }
        ]
    }

    # 创建提取策略
    extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)

    # 设置爬虫配置
    config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        cache_mode=CacheMode.BYPASS  # 确保绕过缓存
    )

    # JavaScript代码，滚动并点击查看更多按钮
    js_click_more = """
    async function clickLoadMore() {
        let moreButton = document.querySelector("#more");
        let lastHeight = document.body.scrollHeight;

        while (moreButton) {
            window.scrollTo(0, document.body.scrollHeight);  // 滚动到页面底部
            console.log("滚动到页面底部");
            moreButton.click();  // 点击查看更多按钮
            console.log("点击了查看更多按钮");

            // 等待按钮点击后的加载
            await new Promise(resolve => setTimeout(resolve, 3000));  // 等待3秒加载更多内容

            // 检查页面是否已加载更多内容
            let newHeight = document.body.scrollHeight;
            if (newHeight === lastHeight) {
                break;  // 如果页面高度没变，表明没有更多内容了
            }
            lastHeight = newHeight;  // 更新页面高度
            moreButton = document.querySelector("#more");  // 查找“查看更多”按钮
        }
        console.log("没有更多的内容了");
    }

    clickLoadMore();  // 调用该函数启动点击加载更多逻辑
    """

    async with AsyncWebCrawler(
            headless=False,           # 无头模式运行（无 GUI）
            verbose=True
    ) as crawler:
        # 初次抓取数据
        result = await crawler.arun(
            url="https://www.piyao.org.cn/jrpy/index.htm",
            config=config,
        )

        if not result.success:
            print("抓取失败:", result.error_message)
            return

        # 解析提取的初始数据
        data = json.loads(result.extracted_content)
        print(f"初始提取了 {len(data)} 条辟谣信息")

        # 获取页面初始的<li>数量
        initial_items_count = len(data)
        total_items = initial_items_count

        # 使用集合保存已抓取过的链接，避免重复
        seen_links = set(item["link"] for item in data)

        # 设置会话ID，确保在同一会话中进行交互
        session_id = "piyao_session"

        # 持续执行直到没有更多数据加载
        while True:
            print("开始加载数据...")

            # 获取当前页面的所有 li 元素，并提取新数据
            result2 = await crawler.arun(
                url="https://www.piyao.org.cn/jrpy/index.htm",
                config=CrawlerRunConfig(
                    session_id=session_id,  # 使用会话ID，继续在同一会话中抓取数据
                    js_code=js_click_more,  # 执行滚动和点击查看更多按钮的JS代码
                    extraction_strategy=extraction_strategy,  # 应用提取策略
                    delay_before_return_html=2.0,    # 捕获内容前等待
                    cache_mode=CacheMode.BYPASS  # 确保绕过缓存
                )
            )
            await asyncio.sleep(3)  # 等待页面加载新数据

            if result2.success:
                # 解析新提取的数据
                new_data = json.loads(result2.extracted_content)
                new_items_count = len(new_data)
                print(f"提取了 {new_items_count} 条新辟谣信息")
                # 打印新数据
                for item in new_data:
                    print(item)

                # 只保留新增的部分：获取新加载的内容
                new_data = [item for item in new_data if item["link"] not in seen_links]

                # 如果有新的数据，更新总数据量并加入已抓取的链接集合
                if new_data:
                    data.extend(new_data)
                    total_items += len(new_data)
                    for item in new_data:
                        seen_links.add(item["link"])
                else:
                    print("没有更多的新数据，停止加载。")
                    break  # 如果没有新数据，提前结束
            else:
                print("数据提取失败，停止加载。")
                break

        # 处理链接并修复相对路径
        base_url = "https://www.piyao.org.cn"
        for item in data:
            raw_link = item["link"]
            fixed_link = raw_link.replace("<../", "/").replace(">", "").replace("/jrpy/", "")
            if not fixed_link.startswith("http"):
                fixed_link = base_url + fixed_link
            item["link"] = fixed_link

        # 保存数据到JSON文件
        output_file = "./data/links.json"
        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print(f"修复后的日期和链接已保存到 {output_file}")

if __name__ == "__main__":
    asyncio.run(main())