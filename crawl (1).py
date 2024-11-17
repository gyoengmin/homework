from argparse import ArgumentParser, Namespace
from multiprocessing.pool import Pool
from time import sleep
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests
import ujson as json
from bs4 import BeautifulSoup
from tqdm import tqdm
from trafilatura import extract, fetch_url

argparser = ArgumentParser("Crawl Naver news articles")
argparser.add_argument("--output_path", type=str, default="news.json")
argparser.add_argument("--query", type=str, default="강원대학교")
argparser.add_argument("--start_date", type=str, default="2024.10.01")
argparser.add_argument("--end_date", type=str, default="2024.10.08")
argparser.add_argument("--max_articles", type=int, default=1000)
argparser.add_argument("--num-workers", type=int, default=10)


def get_article_body(url: str) -> Optional[Dict[str, Any]]:
    try:
        downloaded = fetch_url(url)
        extracted_news_content = extract(
            downloaded, output_format="json", with_metadata=True
        )
        extracted_news_content = json.loads(extracted_news_content)
    except:
        return None

    return extracted_news_content


def crawl_articles(args: Namespace) -> List[Dict[str, str]]:
    encoded_query = quote(args.query)
    current_index = 1
    next_url = (
        "https://s.search.naver.com/p/newssearch/search.naver?"
        f"de={args.end_date}&ds={args.start_date}&query={encoded_query}&sort=0&"
        f"start={current_index}&where=news_tab_api"
    )

    crawled_articles = []
    progress_bar = tqdm(total=args.max_articles)

    while len(crawled_articles) < args.max_articles:
        if next_url == "":
            print("No more articles to crawl")
            break

        request_result = requests.get(next_url)
        request_result = request_result.json()

        contents = request_result["contents"]
        next_url = request_result["nextUrl"]

        article_urls = []
        for content in contents:
            content_soup = BeautifulSoup(content, features="lxml")
            news = content_soup.find("a", {"class": "news_tit"})
            news_url = news["href"]
            article_urls.append(news_url)

        with Pool(args.num_workers) as pool:
            for article_body in pool.imap_unordered(get_article_body, article_urls):
                if article_body is not None:
                    crawled_articles.append(article_body)
                    progress_bar.update(1)

        sleep(1)

    return crawled_articles


if __name__ == "__main__":
    args = argparser.parse_args()

    crawled_articles = crawl_articles(args)

    with open(args.output_path, "w") as f:
        json.dump(crawled_articles, f, ensure_ascii=False)
