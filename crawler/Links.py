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

    # 等待策略
    js_wait_for = """
    js:() => {
        // 只在点击了三次后，开始等待新内容加载
        let click_count = localStorage.getItem('click_count');
        console.log("点击次数：", click_count);
        if (click_count && click_count >= 1) {
            return true
        }
        console.log("未达到点击次数或未加载新内容");
        return false;
    }
    """

    # JavaScript代码，滚动并点击查看更多按钮
    js_click_more = """
    async function clickLoadMore(maxClicks) {
        localStorage.removeItem('click_count'); // 清除点击次数
        let moreButton = document.querySelector("#more");
        let lastHeight = document.body.scrollHeight;
        let clickCount = localStorage.getItem('click_count') || 0;  // 获取点击次数，若没有则为 0

        while (moreButton && clickCount < maxClicks) {
            window.scrollTo(0, document.body.scrollHeight);  // 滚动到页面底部
            console.log("滚动到页面底部");
            moreButton.click();  // 点击查看更多按钮
            console.log("点击了查看更多按钮");

            // 等待按钮点击后的加载
            await new Promise(resolve => setTimeout(resolve, 1000));  // 等待1秒加载更多内容
            
            clickCount++;  // 增加点击计数
            localStorage.setItem('click_count', parseInt(clickCount));  // 更新点击次数

            // 检查页面是否已加载更多内容
            let newHeight = document.body.scrollHeight;
            if (newHeight === lastHeight) {
                break;  // 如果页面高度没变，表明没有更多内容了
            }
            lastHeight = newHeight;  // 更新页面高度
            moreButton = document.querySelector("#more");  // 查找“查看更多”按钮
        }
        console.log("加载完成或达到最大点击次数");
    }

    clickLoadMore(1);  // 限制最多执行 3 次点击
    """

    async with AsyncWebCrawler(
            headless=True,           # 无头模式运行（无 GUI）
            verbose=True
    ) as crawler:
        # 获取当前页面的所有 li 元素，并提取数据
        result = await crawler.arun(
            url="https://www.piyao.org.cn/jrpy/index.htm",
            config=CrawlerRunConfig(
                js_code=js_click_more,  # 执行滚动和点击查看更多按钮的JS代码
                wait_for=js_wait_for,  # 等待新内容加载的JS代码
                extraction_strategy=extraction_strategy,  # 应用提取策略
                # delay_before_return_html=10.0,    # 捕获内容前等待
                cache_mode=CacheMode.BYPASS  # 确保绕过缓存
            )
        )

        if result.success:
            # 解析新提取的数据
            data = json.loads(result.extracted_content)
            new_items_count = len(data)
            print(f"提取了 {new_items_count} 条辟谣信息")
            # 打印新数据
            for item in data:
                print(item)

            # 处理链接并修复相对路径
            base_url = "https://www.piyao.org.cn"
            for item in data:
                raw_link = item["link"]
                # 修复相对路径，去掉多余的 '..'
                fixed_link = raw_link.replace("../", "/").replace(">", "").replace("/jrpy/", "")

                if not fixed_link.startswith("http"):
                    fixed_link = base_url + fixed_link
                item["link"] = fixed_link

            # 保存数据到JSON文件
            output_file = "./data/links.json"
            with open(output_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            print(f"修复后的日期和链接已保存到 {output_file}")

        else:
            print("数据提取失败，停止加载。")

if __name__ == "__main__":
    asyncio.run(main())