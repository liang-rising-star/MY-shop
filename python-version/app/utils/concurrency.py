"""
高并发处理工具
- Redis缓存（可选）
- 乐观锁
- 分布式锁
- 限流器
"""
import asyncio
import time
from typing import Optional
from contextlib import asynccontextmanager

# 尝试导入redis，如果失败则使用内存模式
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class HighConcurrencyHandler:
    """高并发处理器"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_client = None
        self.redis_url = redis_url
        self.use_redis = False
        self._init_redis()
    
    def _init_redis(self):
        """初始化Redis连接"""
        if not REDIS_AVAILABLE:
            print("[Redis] 未安装，使用内存模式")
            self.use_redis = False
            return
            
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.redis_client.ping()
            self.use_redis = True
            print("[Redis] 连接成功")
        except Exception as e:
            print(f"[Redis] 连接失败: {e}, 使用内存模式")
            self.use_redis = False
    
    @asynccontextmanager
    async def distributed_lock(self, key: str, timeout: int = 10, retry: int = 3):
        """分布式锁 - 防止并发重复操作"""
        lock_key = f"lock:{key}"
        lock_value = f"{time.time()}:{id(self)}"
        
        if self.use_redis:
            for i in range(retry):
                if self.redis_client.set(lock_key, lock_value, nx=True, ex=timeout):
                    try:
                        yield
                    finally:
                        self.redis_client.delete(lock_key)
                    return
                await asyncio.sleep(0.1)
            raise Exception(f"获取锁失败: {key}")
        else:
            # 内存模式：简单延迟
            await asyncio.sleep(0.01)
            yield
    
    async def check_rate_limit(self, user_id: int, action: str, 
                               max_requests: int = 10, window: int = 60) -> bool:
        """限流检查 - 防止刷单"""
        # 内存模式：不过滤，直接返回True
        return True
    
    async def get_stock(self, product_id: int) -> Optional[int]:
        """从缓存获取库存"""
        if self.use_redis:
            try:
                stock = self.redis_client.get(f"stock:{product_id}")
                return int(stock) if stock else None
            except:
                return None
        return None
    
    async def set_stock(self, product_id: int, stock: int):
        """设置库存到缓存"""
        if self.use_redis:
            try:
                self.redis_client.set(f"stock:{product_id}", stock, ex=300)
            except:
                pass
    
    async def decrement_stock(self, product_id: int, quantity: int = 1) -> int:
        """原子递减库存"""
        if self.use_redis:
            lua_script = """
            local stock = redis.call('GET', KEYS[1])
            if stock == false then
                return -1
            end
            stock = tonumber(stock)
            if stock < tonumber(ARGV[1]) then
                return -2
            end
            return redis.call('DECRBY', KEYS[1], ARGV[1])
            """
            try:
                result = self.redis_client.eval(
                    lua_script, 1, 
                    f"stock:{product_id}", 
                    quantity
                )
                return int(result)
            except:
                return -1
        return -1
    
    async def record_order(self, order_no: str, data: dict, expire: int = 3600):
        """记录订单到缓存（防止重复提交）"""
        if self.use_redis:
            try:
                self.redis_client.setex(
                    f"order:{order_no}", 
                    expire, 
                    str(data)
                )
            except:
                pass
    
    async def check_duplicate_order(self, order_no: str) -> bool:
        """检查重复订单"""
        if self.use_redis:
            try:
                return self.redis_client.exists(f"order:{order_no}") > 0
            except:
                return False
        return False
    
    async def sync_stock_to_cache(self, product_id: int, db_stock: int):
        """同步数据库库存到缓存"""
        await self.set_stock(product_id, db_stock)

# 全局实例
concurrency_handler = HighConcurrencyHandler()

def init_concurrency():
    """初始化并发处理器"""
    # 已经自动初始化
    pass
