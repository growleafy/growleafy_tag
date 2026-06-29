"""
Database Manager for Supabase PostgreSQL
Handles all database operations
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
from config import Config
import streamlit as st
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manage all database operations"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.config = Config()
        self.client: Optional[Client] = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            supabase_config = self.config.get_supabase_config()
            if supabase_config["url"] and supabase_config["key"]:
                self.client = create_client(
                    supabase_config["url"],
                    supabase_config["key"]
                )
                logger.info("Supabase client initialized successfully")
            else:
                logger.warning("Supabase credentials not configured")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            
    # ==================== Plant Database Operations ====================
    
    def create_plants_table(self):
        """Create plants table if not exists"""
        if not self.client:
            return False
            
        try:
            # Create table using SQL
            query = """
            CREATE TABLE IF NOT EXISTS plants (
                id SERIAL PRIMARY KEY,
                plant_name VARCHAR(255) NOT NULL,
                botanical_name VARCHAR(255),
                local_name VARCHAR(255),
                category VARCHAR(100),
                flowering_season VARCHAR(255),
                nursery_preparation_time VARCHAR(255),
                propagation_method VARCHAR(255),
                plant_type VARCHAR(100),
                plant_features TEXT,
                uses TEXT,
                growing_season VARCHAR(255),
                growing_location VARCHAR(255),
                sunlight_requirement VARCHAR(255),
                water_requirement VARCHAR(255),
                pot_size VARCHAR(100),
                mrp DECIMAL(10, 2),
                selling_price DECIMAL(10, 2),
                barcode VARCHAR(255),
                qr_code TEXT,
                plant_image_url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.client.rpc('execute_sql', {'query': query}).execute()
            logger.info("Plants table created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating plants table: {e}")
            return False
    
    def add_plant(self, plant_data: Dict[str, Any]) -> bool:
        """Add a new plant"""
        try:
            if not self.client:
                return False
                
            # Generate barcode if not provided
            if not plant_data.get('barcode'):
                from utils.barcode_generator import BarcodeGenerator
                barcode_gen = BarcodeGenerator()
                plant_data['barcode'] = barcode_gen.generate_unique_barcode('PL')
                
            # Generate QR code if not provided
            if not plant_data.get('qr_code'):
                from utils.qr_generator import QRGenerator
                qr_gen = QRGenerator()
                qr_data = f"Plant: {plant_data['plant_name']}\nMRP: ₹{plant_data.get('mrp', 'N/A')}"
                plant_data['qr_code'] = qr_gen.generate_qr_base64(qr_data)
                
            result = self.client.table('plants').insert(plant_data).execute()
            logger.info(f"Plant added successfully: {plant_data['plant_name']}")
            return True
        except Exception as e:
            logger.error(f"Error adding plant: {e}")
            return False
    
    def get_plants(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get plants with optional filters"""
        try:
            if not self.client:
                return []
                
            query = self.client.table('plants').select('*')
            
            if filters:
                for key, value in filters.items():
                    if value:
                        query = query.filter(key, 'ilike', f'%{value}%')
                        
            result = query.order('created_at', desc=True).limit(limit).offset(offset).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching plants: {e}")
            return []
    
    def update_plant(self, plant_id: int, plant_data: Dict[str, Any]) -> bool:
        """Update plant information"""
        try:
            if not self.client:
                return False
                
            plant_data['updated_at'] = datetime.now().isoformat()
            self.client.table('plants').update(plant_data).eq('id', plant_id).execute()
            logger.info(f"Plant updated successfully: {plant_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating plant: {e}")
            return False
    
    def delete_plant(self, plant_id: int) -> bool:
        """Delete a plant"""
        try:
            if not self.client:
                return False
                
            self.client.table('plants').delete().eq('id', plant_id).execute()
            logger.info(f"Plant deleted successfully: {plant_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting plant: {e}")
            return False
    
    def search_plants(self, search_term: str) -> List[Dict]:
        """Search plants by multiple fields"""
        try:
            if not self.client:
                return []
                
            # Search across multiple columns
            search_columns = [
                'plant_name', 'botanical_name', 'local_name', 'category',
                'plant_features', 'uses', 'growing_season'
            ]
            
            results = []
            for column in search_columns:
                result = self.client.table('plants').select('*').filter(
                    column, 'ilike', f'%{search_term}%'
                ).execute()
                results.extend(result.data)
                
            # Remove duplicates
            seen_ids = set()
            unique_results = []
            for r in results:
                if r['id'] not in seen_ids:
                    seen_ids.add(r['id'])
                    unique_results.append(r)
                    
            return unique_results
        except Exception as e:
            logger.error(f"Error searching plants: {e}")
            return []
    
    def bulk_import_plants(self, df: pd.DataFrame) -> Dict[str, int]:
        """Bulk import plants from DataFrame"""
        stats = {'success': 0, 'failed': 0, 'errors': []}
        
        for _, row in df.iterrows():
            plant_data = row.to_dict()
            # Clean data
            plant_data = {k: (v if pd.notna(v) else None) for k, v in plant_data.items()}
            
            if self.add_plant(plant_data):
                stats['success'] += 1
            else:
                stats['failed'] += 1
                stats['errors'].append(f"Failed to add: {plant_data.get('plant_name', 'Unknown')}")
                
        return stats
    
    # ==================== Fertilizer Database Operations ====================
    
    def create_fertilizers_table(self):
        """Create fertilizers table"""
        if not self.client:
            return False
            
        try:
            query = """
            CREATE TABLE IF NOT EXISTS fertilizers (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                brand VARCHAR(255),
                category VARCHAR(100),
                organic_inorganic VARCHAR(50),
                composition TEXT,
                npk_value VARCHAR(100),
                dosage TEXT,
                suitable_plants TEXT,
                mrp DECIMAL(10, 2),
                barcode VARCHAR(255),
                qr_code TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.client.rpc('execute_sql', {'query': query}).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating fertilizers table: {e}")
            return False
    
    def add_fertilizer(self, fertilizer_data: Dict[str, Any]) -> bool:
        """Add fertilizer"""
        try:
            if not self.client:
                return False
                
            if not fertilizer_data.get('barcode'):
                from utils.barcode_generator import BarcodeGenerator
                barcode_gen = BarcodeGenerator()
                fertilizer_data['barcode'] = barcode_gen.generate_unique_barcode('FE')
                
            if not fertilizer_data.get('qr_code'):
                from utils.qr_generator import QRGenerator
                qr_gen = QRGenerator()
                qr_data = f"Fertilizer: {fertilizer_data['product_name']}\nNPK: {fertilizer_data.get('npk_value', 'N/A')}"
                fertilizer_data['qr_code'] = qr_gen.generate_qr_base64(qr_data)
                
            self.client.table('fertilizers').insert(fertilizer_data).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding fertilizer: {e}")
            return False
    
    def get_fertilizers(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get fertilizers"""
        try:
            if not self.client:
                return []
                
            query = self.client.table('fertilizers').select('*')
            
            if filters:
                for key, value in filters.items():
                    if value:
                        query = query.filter(key, 'ilike', f'%{value}%')
                        
            result = query.order('created_at', desc=True).limit(limit).offset(offset).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching fertilizers: {e}")
            return []
    
    def update_fertilizer(self, fertilizer_id: int, data: Dict[str, Any]) -> bool:
        """Update fertilizer"""
        try:
            if not self.client:
                return False
                
            data['updated_at'] = datetime.now().isoformat()
            self.client.table('fertilizers').update(data).eq('id', fertilizer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating fertilizer: {e}")
            return False
    
    def delete_fertilizer(self, fertilizer_id: int) -> bool:
        """Delete fertilizer"""
        try:
            if not self.client:
                return False
                
            self.client.table('fertilizers').delete().eq('id', fertilizer_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting fertilizer: {e}")
            return False
    
    # ==================== Insecticide Database Operations ====================
    
    def create_insecticides_table(self):
        """Create insecticides table"""
        if not self.client:
            return False
            
        try:
            query = """
            CREATE TABLE IF NOT EXISTS insecticides (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                brand VARCHAR(255),
                active_ingredient TEXT,
                target_pest TEXT,
                dosage TEXT,
                suitable_plants TEXT,
                safety_instructions TEXT,
                mrp DECIMAL(10, 2),
                barcode VARCHAR(255),
                qr_code TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.client.rpc('execute_sql', {'query': query}).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating insecticides table: {e}")
            return False
    
    def add_insecticide(self, data: Dict[str, Any]) -> bool:
        """Add insecticide"""
        try:
            if not self.client:
                return False
                
            if not data.get('barcode'):
                from utils.barcode_generator import BarcodeGenerator
                barcode_gen = BarcodeGenerator()
                data['barcode'] = barcode_gen.generate_unique_barcode('IN')
                
            if not data.get('qr_code'):
                from utils.qr_generator import QRGenerator
                qr_gen = QRGenerator()
                qr_data = f"Insecticide: {data['product_name']}\nTarget: {data.get('target_pest', 'N/A')}"
                data['qr_code'] = qr_gen.generate_qr_base64(qr_data)
                
            self.client.table('insecticides').insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding insecticide: {e}")
            return False
    
    def get_insecticides(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get insecticides"""
        try:
            if not self.client:
                return []
                
            query = self.client.table('insecticides').select('*')
            
            if filters:
                for key, value in filters.items():
                    if value:
                        query = query.filter(key, 'ilike', f'%{value}%')
                        
            result = query.order('created_at', desc=True).limit(limit).offset(offset).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching insecticides: {e}")
            return []
    
    def update_insecticide(self, insecticide_id: int, data: Dict[str, Any]) -> bool:
        """Update insecticide"""
        try:
            if not self.client:
                return False
                
            data['updated_at'] = datetime.now().isoformat()
            self.client.table('insecticides').update(data).eq('id', insecticide_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating insecticide: {e}")
            return False
    
    def delete_insecticide(self, insecticide_id: int) -> bool:
        """Delete insecticide"""
        try:
            if not self.client:
                return False
                
            self.client.table('insecticides').delete().eq('id', insecticide_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting insecticide: {e}")
            return False
    
    # ==================== Pesticide Database Operations ====================
    
    def create_pesticides_table(self):
        """Create pesticides table"""
        if not self.client:
            return False
            
        try:
            query = """
            CREATE TABLE IF NOT EXISTS pesticides (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(255) NOT NULL,
                brand VARCHAR(255),
                active_ingredient TEXT,
                target_disease TEXT,
                dosage TEXT,
                waiting_period VARCHAR(255),
                suitable_plants TEXT,
                mrp DECIMAL(10, 2),
                barcode VARCHAR(255),
                qr_code TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.client.rpc('execute_sql', {'query': query}).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating pesticides table: {e}")
            return False
    
    def add_pesticide(self, data: Dict[str, Any]) -> bool:
        """Add pesticide"""
        try:
            if not self.client:
                return False
                
            if not data.get('barcode'):
                from utils.barcode_generator import BarcodeGenerator
                barcode_gen = BarcodeGenerator()
                data['barcode'] = barcode_gen.generate_unique_barcode('PE')
                
            if not data.get('qr_code'):
                from utils.qr_generator import QRGenerator
                qr_gen = QRGenerator()
                qr_data = f"Pesticide: {data['product_name']}\nTarget: {data.get('target_disease', 'N/A')}"
                data['qr_code'] = qr_gen.generate_qr_base64(qr_data)
                
            self.client.table('pesticides').insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding pesticide: {e}")
            return False
    
    def get_pesticides(self, filters: Dict = None, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get pesticides"""
        try:
            if not self.client:
                return []
                
            query = self.client.table('pesticides').select('*')
            
            if filters:
                for key, value in filters.items():
                    if value:
                        query = query.filter(key, 'ilike', f'%{value}%')
                        
            result = query.order('created_at', desc=True).limit(limit).offset(offset).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching pesticides: {e}")
            return []
    
    def update_pesticide(self, pesticide_id: int, data: Dict[str, Any]) -> bool:
        """Update pesticide"""
        try:
            if not self.client:
                return False
                
            data['updated_at'] = datetime.now().isoformat()
            self.client.table('pesticides').update(data).eq('id', pesticide_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating pesticide: {e}")
            return False
    
    def delete_pesticide(self, pesticide_id: int) -> bool:
        """Delete pesticide"""
        try:
            if not self.client:
                return False
                
            self.client.table('pesticides').delete().eq('id', pesticide_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting pesticide: {e}")
            return False
    
    # ==================== Statistics & Analytics ====================
    
    def get_statistics(self) -> Dict[str, int]:
        """Get dashboard statistics"""
        stats = {
            'total_plants': 0,
            'total_fertilizers': 0,
            'total_insecticides': 0,
            'total_pesticides': 0,
            'total_printed_tags': 0
        }
        
        try:
            if not self.client:
                return stats
                
            # Get counts
            plants = self.client.table('plants').select('id', count='exact').execute()
            stats['total_plants'] = plants.count if plants.count else 0
            
            fertilizers = self.client.table('fertilizers').select('id', count='exact').execute()
            stats['total_fertilizers'] = fertilizers.count if fertilizers.count else 0
            
            insecticides = self.client.table('insecticides').select('id', count='exact').execute()
            stats['total_insecticides'] = insecticides.count if insecticides.count else 0
            
            pesticides = self.client.table('pesticides').select('id', count='exact').execute()
            stats['total_pesticides'] = pesticides.count if pesticides.count else 0
            
            # Get printed tags count
            tags = self.client.table('tag_history').select('id', count='exact').execute()
            stats['total_printed_tags'] = tags.count if tags.count else 0
            
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            
        return stats
    
    def get_recent_items(self, limit: int = 10) -> Dict[str, List[Dict]]:
        """Get recently added items"""
        recent = {
            'plants': [],
            'fertilizers': [],
            'insecticides': [],
            'pesticides': []
        }
        
        try:
            if not self.client:
                return recent
                
            recent['plants'] = self.get_plants(limit=limit) or []
            recent['fertilizers'] = self.get_fertilizers(limit=limit) or []
            recent['insecticides'] = self.get_insecticides(limit=limit) or []
            recent['pesticides'] = self.get_pesticides(limit=limit) or []
            
        except Exception as e:
            logger.error(f"Error fetching recent items: {e}")
            
        return recent
    
    # ==================== Tag History ====================
    
    def create_tag_history_table(self):
        """Create tag history table"""
        if not self.client:
            return False
            
        try:
            query = """
            CREATE TABLE IF NOT EXISTS tag_history (
                id SERIAL PRIMARY KEY,
                item_type VARCHAR(50),
                item_id INTEGER,
                item_name VARCHAR(255),
                tags_count INTEGER,
                printed_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.client.rpc('execute_sql', {'query': query}).execute()
            return True
        except Exception as e:
            logger.error(f"Error creating tag history table: {e}")
            return False
    
    def log_tag_print(self, item_type: str, item_id: int, item_name: str, count: int) -> bool:
        """Log tag printing"""
        try:
            if not self.client:
                return False
                
            data = {
                'item_type': item_type,
                'item_id': item_id,
                'item_name': item_name,
                'tags_count': count
            }
            self.client.table('tag_history').insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error logging tag print: {e}")
            return False
    
    # ==================== Universal Search ====================
    
    def universal_search(self, search_term: str) -> Dict[str, List[Dict]]:
        """Search across all databases"""
        results = {
            'plants': [],
            'fertilizers': [],
            'insecticides': [],
            'pesticides': []
        }
        
        try:
            if not self.client or not search_term:
                return results
                
            results['plants'] = self.search_plants(search_term)
            
            # Search fertilizers
            fert_query = self.client.table('fertilizers').select('*').or_(
                f"product_name.ilike.%{search_term}%,brand.ilike.%{search_term}%,category.ilike.%{search_term}%"
            ).execute()
            results['fertilizers'] = fert_query.data if fert_query.data else []
            
            # Search insecticides
            insect_query = self.client.table('insecticides').select('*').or_(
                f"product_name.ilike.%{search_term}%,brand.ilike.%{search_term}%,target_pest.ilike.%{search_term}%"
            ).execute()
            results['insecticides'] = insect_query.data if insect_query.data else []
            
            # Search pesticides
            pest_query = self.client.table('pesticides').select('*').or_(
                f"product_name.ilike.%{search_term}%,brand.ilike.%{search_term}%,target_disease.ilike.%{search_term}%"
            ).execute()
            results['pesticides'] = pest_query.data if pest_query.data else []
            
        except Exception as e:
            logger.error(f"Error in universal search: {e}")
            
        return results
    
    # ==================== Initialize All Tables ====================
    
    def initialize_tables(self):
        """Initialize all database tables"""
        self.create_plants_table()
        self.create_fertilizers_table()
        self.create_insecticides_table()
        self.create_pesticides_table()
        self.create_tag_history_table()
        logger.info("All tables initialized")
