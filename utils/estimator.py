from typing import Dict, List
import statistics
from ..config import SalesConfig
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class SalesEstimator:
    """销售额估算器"""
    
    def estimate_sales(self, products: List[Dict]) -> Dict:
        """
        估算月销售额
        
        算法:
        月销售额 = 平均产品价格 × 预估月销售量
        预估月销售量 = (评价数 / 评价率) × 重复购买率
        """
        
        if not products:
            return {
                "monthly_sales": 0,
                "confidence": 0,
                "details": {}
            }
        
        try:
            prices = []
            review_counts = []
            
            for product in products:
                # 提取价格
                if isinstance(product, dict):
                    # 从variants中获取价格
                    if "variants" in product and product["variants"]:
                        for variant in product["variants"]:
                            try:
                                price = float(variant.get("price", 0))
                                if price > 0:
                                    prices.append(price)
                            except (ValueError, TypeError):
                                continue
                    
                    # 获取评价数
                    if "metafield" in product:
                        try:
                            reviews = int(product["metafield"].get("reviews_count", 0))
                            if reviews > 0:
                                review_counts.append(reviews)
                        except (ValueError, TypeError):
                            continue
            
            if not prices:
                return {
                    "monthly_sales": 0,
                    "confidence": 0,
                    "details": {"error": "无产品价格数据"}
                }
            
            # 计算平均价格
            avg_price = statistics.mean(prices)
            
            # 根据评价数估算销售量
            if review_counts:
                total_reviews = sum(review_counts)
                # 假设只有5-10%的买家会留评
                estimated_sales_count = int(
                    (total_reviews / SalesConfig.AVG_REVIEW_RATE) * 
                    SalesConfig.REPEAT_PURCHASE_RATE
                )
                confidence = 0.75  # 有评价数据，信心较高
            else:
                # 根据产品数量估算
                product_count = len(products)
                estimated_sales_count = product_count * 50  # 假设每个产品平均月销50件
                confidence = 0.4  # 无具体数据，信心较低
            
            # 计算月销售额
            monthly_sales = int(avg_price * estimated_sales_count)
            
            details = {
                "avg_product_price": round(avg_price, 2),
                "estimated_monthly_units": estimated_sales_count,
                "total_reviews": sum(review_counts) if review_counts else 0,
                "products_count": len(products),
                "price_range": (round(min(prices), 2), round(max(prices), 2)) if prices else None,
            }
            
            logger.debug(f"💰 销售额估算 - 月销: ${monthly_sales:,}, 信心: {confidence:.0%}")
            
            return {
                "monthly_sales": monthly_sales,
                "confidence": confidence,
                "details": details
            }
            
        except Exception as e:
            logger.error(f"❌ 估算销售额失败: {str(e)}")
            return {
                "monthly_sales": 0,
                "confidence": 0,
                "details": {"error": str(e)}
            }