import asyncio
import json
from pathlib import Path

from utils.logger import setup_logger
from scrapers.shopify_scraper import ShopifyScraper
from config import OutputConfig

logger = setup_logger(__name__)

async def main():
    logger.info("Shopify独立站卖家爬虫启动")
    scraper = ShopifyScraper(debug=False)
    logger.info("爬虫已初始化")

if __name__ == "__main__":
    asyncio.run(main())