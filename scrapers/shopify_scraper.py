import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Optional
from datetime import datetime

from ..config import ScraperConfig, SalesConfig, ChinaShippingConfig
from ..utils.logger import setup_logger
from ..utils.estimator import SalesEstimator
from ..utils.detector import ChinaShippingDetector

logger = setup_logger(__name__)

class ShopifyScraper:
    """Shopify 独立站爬虫 - 专注中国发货卖家"""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.session: Optional[aiohttp.ClientSession] = None
        self.estimator = SalesEstimator()
        self.detector = ChinaShippingDetector()
    
    async def scrape_store(self, store_url: str) -> Dict:
        """爬取单个店铺"""
        logger.info(f"🔍 开始爬取: {store_url}")
        
        try:
            # 规范化URL
            store_url = self._normalize_url(store_url)
            
            # 创建会话
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # 获取店铺主页信息
            store_data = await self._fetch_store_info(store_url)
            if not store_data:
                return {"error": "无法获取店铺信息", "url": store_url}
            
            # 获取产品数据
            products = await self._fetch_products(store_url)
            store_data["products_count"] = len(products)
            
            # 估算月销售额
            if products:
                sales_estimate = self.estimator.estimate_sales(products)
                store_data["estimated_monthly_sales"] = sales_estimate["monthly_sales"]
                store_data["sales_confidence"] = sales_estimate["confidence"]
            
            # 检测中国发货
            china_shipping = self.detector.detect_china_shipping(store_data)
            store_data["is_china_shipper"] = china_shipping["is_china_shipper"]
            store_data["confidence_score"] = china_shipping["confidence"]
            store_data["shipping_evidence"] = china_shipping.get("evidence", [])
            
            # 检查是否符合条件
            sales = store_data.get("estimated_monthly_sales", 0)
            is_china = store_data.get("is_china_shipper", False)
            match = (SalesConfig.MIN_MONTHLY_SALES <= sales <= SalesConfig.MAX_MONTHLY_SALES 
                     and is_china)
            
            store_data["match_criteria"] = match
            store_data["last_updated"] = datetime.now().isoformat()
            
            if match:
                logger.info(f"✅ 完美匹配! {store_url} | 销售额: ${sales:,.0f} | 中国发货: ✓")
            else:
                if not is_china:
                    logger.info(f"⚠️  不是中国发货: {store_url}")
                else:
                    logger.info(f"⚠️  销售额不符: {store_url} (${sales:,.0f})")
            
            return store_data
            
        except Exception as e:
            logger.error(f"❌ 爬取失败 {store_url}: {str(e)}")
            return {"error": str(e), "url": store_url, "success": False}
    
    async def scrape_multiple(self, store_urls: List[str]) -> List[Dict]:
        """批量爬取多个店铺"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        logger.info(f"📊 准备爬取 {len(store_urls)} 个店铺...")
        
        # 创建限制并发的信号量
        semaphore = asyncio.Semaphore(ScraperConfig.MAX_WORKERS)
        
        async def limited_scrape(url):
            async with semaphore:
                await asyncio.sleep(ScraperConfig.DELAY_BETWEEN_REQUESTS)
                return await self.scrape_store(url)
        
        # 执行所有任务
        tasks = [limited_scrape(url) for url in store_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"任务异常: {result}")
                processed_results.append({"error": str(result), "success": False})
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _fetch_store_info(self, store_url: str) -> Optional[Dict]:
        """获取店铺基本信息"""
        try:
            async with self.session.get(
                store_url,
                timeout=aiohttp.ClientTimeout(total=ScraperConfig.REQUEST_TIMEOUT),
                headers=self._get_headers()
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    store_info = {
                        "store_url": store_url,
                        "store_name": self._extract_store_name(html, store_url),
                        "contact_email": self._extract_email(html),
                        "phone": self._extract_phone(html),
                        "social_links": self._extract_social_links(html),
                        "payment_methods": self._extract_payment_methods(html),
                        "shipping_info": await self._fetch_shipping_info(store_url, html),
                        "company_info": self._extract_company_info(html),
                    }
                    
                    return store_info
                else:
                    logger.warning(f"HTTP {response.status}: {store_url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏱️  超时: {store_url}")
            return None
        except Exception as e:
            logger.error(f"获取店铺信息失败: {str(e)}")
            return None
    
    async def _fetch_products(self, store_url: str) -> List[Dict]:
        """获取店铺产品列表"""
        products = []
        
        try:
            # 方式1: 通过 /products.json API
            products_api_url = f"{store_url.rstrip('/')}/products.json"
            
            try:
                async with self.session.get(
                    products_api_url,
                    timeout=aiohttp.ClientTimeout(total=ScraperConfig.REQUEST_TIMEOUT),
                    headers=self._get_headers()
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        products = data.get("products", [])
                        logger.debug(f"📦 通过API获取 {len(products)} 个产品")
                        return products
            except:
                pass
            
            # 方式2: 爬取首页产品
            try:
                async with self.session.get(
                    store_url,
                    timeout=aiohttp.ClientTimeout(total=ScraperConfig.REQUEST_TIMEOUT),
                    headers=self._get_headers()
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        products = self._extract_products_from_html(html)
                        logger.debug(f"📦 从HTML提取 {len(products)} 个产品")
            except:
                pass
                    
        except Exception as e:
            logger.debug(f"获取产品列表失败: {str(e)}")
        
        return products
    
    async def _fetch_shipping_info(self, store_url: str, html: str = "") -> Dict:
        """获取运输信息"""
        shipping_info = {
            "regions": [],
            "methods": [],
            "has_china_shipping": False,
        }
        
        try:
            # 检查主页中的运输信息
            if html:
                shipping_info["regions"] = self._extract_shipping_regions(html)
                shipping_info["methods"] = self._extract_shipping_methods(html)
            
            # 尝试获取运输政策页面
            shipping_urls = [
                f"{store_url.rstrip('/')}/pages/shipping",
                f"{store_url.rstrip('/')}/policies/shipping",
            ]
            
            for shipping_url in shipping_urls:
                try:
                    async with self.session.get(
                        shipping_url,
                        timeout=aiohttp.ClientTimeout(total=5),
                        headers=self._get_headers()
                    ) as response:
                        if response.status == 200:
                            policy_html = await response.text()
                            regions = self._extract_shipping_regions(policy_html)
                            methods = self._extract_shipping_methods(policy_html)
                            
                            shipping_info["regions"].extend(regions)
                            shipping_info["methods"].extend(methods)
                            break
                except:
                    continue
            
            # 检查是否包含中国发货
            shipping_text = " ".join(shipping_info["regions"] + shipping_info["methods"]).lower()
            shipping_info["has_china_shipping"] = any(
                keyword in shipping_text 
                for keyword in ChinaShippingConfig.KEYWORDS["china"]
            )
                    
        except Exception as e:
            logger.debug(f"获取运输信息失败: {str(e)}")
        
        return shipping_info
    
    def _normalize_url(self, url: str) -> str:
        """规范化URL"""
        if not url.startswith("http"):
            url = f"https://{url}"
        return url.rstrip("/")
    
    def _get_headers(self) -> Dict:
        """获取请求头"""
        headers = ScraperConfig.DEFAULT_HEADERS.copy()
        
        if ScraperConfig.USER_AGENT_ROTATION:
            try:
                from fake_useragent import UserAgent
                ua = UserAgent()
                headers["User-Agent"] = ua.random
            except:
                pass
        
        return headers
    
    def _extract_store_name(self, html: str, url: str) -> str:
        """提取店铺名称"""
        # 从title标签
        match = re.search(r"<title>([^<]+)</title>", html, re.I)
        if match:
            return match.group(1).strip()
        
        # 从URL
        return url.split("//")[-1].split(".")[0]
    
    def _extract_email(self, html: str) -> Optional[str]:
        """提取联系邮箱"""
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(pattern, html)
        return match.group(0) if match else None
    
    def _extract_phone(self, html: str) -> Optional[str]:
        """提取电话号码"""
        patterns = [
            r"\+?1?\s?[\(\-\.]?[0-9]{3}[\)\-\.]?\s?[0-9]{3}[\-\.]?[0-9]{4}",
            r"1[3-9]\d{9}",  # 中国手机
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_social_links(self, html: str) -> Dict[str, str]:
        """提取社交媒体链接"""
        social = {}
        
        socials = {
            "instagram": r"instagram\.com/([a-zA-Z0-9_.]+)",
            "facebook": r"facebook\.com/([a-zA-Z0-9_.]+)",
            "tiktok": r"tiktok\.com/(@[a-zA-Z0-9_.]+)",
            "twitter": r"twitter\.com/([a-zA-Z0-9_]+)",
            "youtube": r"youtube\.com/(@[a-zA-Z0-9_\-]+|c/[a-zA-Z0-9_\-]+)",
        }
        
        for platform, pattern in socials.items():
            match = re.search(pattern, html, re.I)
            if match:
                handle = match.group(1)
                social[platform] = f"https://{platform}.com/{handle}"
        
        return social
    
    def _extract_payment_methods(self, html: str) -> List[str]:
        """提取支付方式"""
        methods = set()
        
        payment_keywords = {
            r"stripe": "Stripe",
            r"paypal": "PayPal",
            r"alipay|支付宝": "Alipay",
            r"wechat|微信": "WeChat Pay",
            r"credit card|visa|mastercard": "Credit Card",
            r"apple pay": "Apple Pay",
            r"google pay": "Google Pay",
        }
        
        html_lower = html.lower()
        for keyword, method in payment_keywords.items():
            if re.search(keyword, html_lower):
                methods.add(method)
        
        return list(methods)
    
    def _extract_company_info(self, html: str) -> Dict:
        """提取公司信息"""
        info = {
            "company_name": None,
            "address": None,
            "location": None,
        }
        
        # 查找地址
        address_pattern = r"(?:Address|地址):\s*([^<\n]+)"
        match = re.search(address_pattern, html, re.I)
        if match:
            info["address"] = match.group(1).strip()
            
            # 判断位置
            if any(cn_keyword in info["address"] for cn_keyword in ChinaShippingConfig.CHINA_KEYWORDS_CN):
                info["location"] = "China"
        
        return info
    
    def _extract_shipping_regions(self, html: str) -> List[str]:
        """提取发货地区"""
        regions = set()
        
        region_keywords = [
            "United States", "USA", "Canada", "UK", "Europe",
            "China", "中国", "Asia", "Worldwide", "International",
            "Australia", "New Zealand", "Japan", "India"
        ]
        
        for region in region_keywords:
            if region in html or region.lower() in html.lower():
                regions.add(region)
        
        return list(regions)
    
    def _extract_shipping_methods(self, html: str) -> List[str]:
        """提取物流方式"""
        methods = set()
        
        method_keywords = {
            r"standard|standard shipping": "Standard Shipping",
            r"express|express shipping": "Express Shipping",
            r"overnight|overnight shipping": "Overnight",
            r"dhl": "DHL",
            r"fedex": "FedEx",
            r"ups": "UPS",
            r"usps": "USPS",
            r"epacket|e-packet": "ePacket",
            r"china post": "China Post",
            r"sf express|顺丰": "SF Express",
        }
        
        html_lower = html.lower()
        for keyword, method in method_keywords.items():
            if re.search(keyword, html_lower):
                methods.add(method)
        
        return list(methods)
    
    def _extract_products_from_html(self, html: str) -> List[Dict]:
        """从HTML提取产品信息"""
        products = []
        
        # 查找产品容器
        product_pattern = r'data-product-id="(\d+)"'
        price_pattern = r'\$[\d,]+\.?\d*'
        
        product_ids = re.findall(product_pattern, html)
        prices = re.findall(price_pattern, html)
        
        for i, prod_id in enumerate(product_ids[:20]):  # 限制20个
            product = {
                "id": prod_id,
                "price": prices[i] if i < len(prices) else None
            }
            products.append(product)
        
        return products
    
    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()