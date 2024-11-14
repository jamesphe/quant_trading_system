import os
import json
import logging

logger = logging.getLogger(__name__)

class Config:
    """配置管理类"""
    
    def __init__(self):
        self.config_file = os.path.join(
            os.path.dirname(__file__),
            'config.json'
        )
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"配置文件 {self.config_file} 不存在")
                return {}
        except Exception as e:
            logger.error(f"读取配置文件失败: {e}")
            return {}
    
    def get_api_key(self, model: str) -> str:
        """获取指定模型的API密钥"""
        api_keys = self.config.get('api_keys', {})
        api_key = api_keys.get(model)
        if not api_key:
            raise ValueError(f"未找到 {model} 的API密钥")
        return api_key 