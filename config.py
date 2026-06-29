"""
GrowLeafy Configuration
Environment variables and application settings
"""

import os
from typing import Dict, Any

class Config:
    """Application configuration"""
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    
    # DeepSeek API Configuration
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    
    # Application Settings
    APP_NAME = "GrowLeafy"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Nursery Database & Tag Printing Application"
    
    # Database Settings
    DATABASE_TABLES = [
        "plants",
        "fertilizers",
        "insecticides",
        "pesticides",
        "tag_history"
    ]
    
    # Tag Default Settings
    TAG_DEFAULTS = {
        "label_width": 8.5,  # cm
        "label_height": 5.5,  # cm
        "top_margin": 1.5,
        "bottom_margin": 1.5,
        "left_margin": 1.0,
        "right_margin": 1.0,
        "horizontal_gap": 0.3,
        "vertical_gap": 0.3,
        "nursery_name": "GrowLeafy Nursery",
        "include_qr": True,
        "include_barcode": True,
        "include_botanical_name": True,
        "include_image": False
    }
    
    # A4 Paper Dimensions
    A4_WIDTH = 21.0  # cm
    A4_HEIGHT = 29.7  # cm
    
    # File Upload Settings
    ALLOWED_EXTENSIONS = ['csv', 'xlsx', 'xls']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    @classmethod
    def get_supabase_config(cls) -> Dict[str, str]:
        """Get Supabase configuration"""
        return {
            "url": cls.SUPABASE_URL,
            "key": cls.SUPABASE_KEY
        }
    
    @classmethod
    def get_deepseek_config(cls) -> Dict[str, str]:
        """Get DeepSeek configuration"""
        return {
            "api_key": cls.DEEPSEEK_API_KEY,
            "base_url": cls.DEEPSEEK_BASE_URL
        }
