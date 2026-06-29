"""
utils/database.py – Supabase Database Manager for Nursery Management System
Covers: Statistics, CRUD, image upload, and safe error handling.
"""
import uuid
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self, url: str, key: str):
        """
        Initialize Supabase client.
        :param url: Supabase project URL
        :param key: Supabase anon/public API key
        """
        self.url = url
        self.key = key
        try:
            self.client: Client = create_client(url, key)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")

    # -------------------------------------------------------------------------
    # SAFE COUNT / STATISTICS
    # -------------------------------------------------------------------------
    def get_statistics(self):
        """
        Returns total counts for main collections.
        Uses count='exact' for speed – fetches no rows.
        If a table doesn't exist or any error, returns 0 for that count.
        """
        stats = {
            'total_plants': 0,
            'total_fertilizers': 0,
            'total_insecticides': 0,
            'total_pesticides': 0,
            'total_printed_tags': 0
        }
        table_map = {
            'total_plants': 'plants',
            'total_fertilizers': 'fertilizers',
            'total_insecticides': 'insecticides',
            'total_pesticides': 'pesticides',
            # 'total_printed_tags': 'printed_tags'   # uncomment if you have a tags table
        }
        for key, table_name in table_map.items():
            try:
                # Exact count without downloading data
                res = self.client.table(table_name).select("*", count='exact').execute()
                stats[key] = res.count if res.count is not None else 0
            except Exception as e:
                print(f"[Statistics] Error counting {table_name}: {e}")
                # Keep default 0
        return stats

    # -------------------------------------------------------------------------
    # RECENT ITEMS (Dashboard feed)
    # -------------------------------------------------------------------------
    def get_recent_items(self, table_name: str, limit: int = 5, order_column: str = "created_at"):
        """
        Fetch most recent rows from a table.
        Change order_column to 'id' if you don't have a timestamp.
        """
        try:
            res = (
                self.client.table(table_name)
                .select("*")
                .order(order_column, desc=True)
                .limit(limit)
                .execute()
            )
            return res.data if res.data else []
        except Exception as e:
            print(f"[Recent Items] Error fetching from {table_name}: {e}")
            return []

    # -------------------------------------------------------------------------
    # IMAGE UPLOAD TO SUPABASE STORAGE
    # -------------------------------------------------------------------------
    def upload_image(self, file_bytes: bytes, original_filename: str, bucket: str = "plant-images"):
        """
        Upload an image to a Supabase storage bucket.
        Returns the public URL on success, None on failure.
        """
        try:
            # Generate unique filename to prevent collisions
            file_extension = original_filename.split(".")[-1] if "." in original_filename else "jpg"
            unique_name = f"{uuid.uuid4()}.{file_extension}"

            # Upload
            self.client.storage.from_(bucket).upload(
                file=file_bytes,
                path=unique_name,
                file_options={"content-type": f"image/{file_extension}"}
            )

            # Get public URL
            public_url = self.client.storage.from_(bucket).get_public_url(unique_name)
            return public_url

        except Exception as e:
            print(f"[Upload] Error uploading image: {e}")
            return None

    # -------------------------------------------------------------------------
    # GENERIC CRUD HELPERS (so the rest of the app doesn’t need raw Supabase)
    # -------------------------------------------------------------------------
    def fetch_all(self, table_name: str, order_column: str = None, ascending: bool = True):
        """
        Get all rows from a table, optionally sorted.
        """
        try:
            query = self.client.table(table_name).select("*")
            if order_column:
                query = query.order(order_column, desc=not ascending)
            res = query.execute()
            return res.data if res.data else []
        except Exception as e:
            print(f"[FetchAll] Error: {e}")
            return []

    def insert_one(self, table_name: str, data: dict):
        """
        Insert a single record. Returns the inserted data or None.
        """
        try:
            res = self.client.table(table_name).insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"[Insert] Error in {table_name}: {e}")
            return None

    def update_one(self, table_name: str, record_id, data: dict, id_column: str = "id"):
        """
        Update a record by its ID column.
        """
        try:
            res = (
                self.client.table(table_name)
                .update(data)
                .eq(id_column, record_id)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            print(f"[Update] Error in {table_name}: {e}")
            return None

    def delete_one(self, table_name: str, record_id, id_column: str = "id"):
        """
        Delete a record by its ID column.
        """
        try:
            res = (
                self.client.table(table_name)
                .delete()
                .eq(id_column, record_id)
                .execute()
            )
            return True
        except Exception as e:
            print(f"[Delete] Error in {table_name}: {e}")
            return False

# Optional: Provide a simple singleton getter if you want to reuse one connection
_db_instance = None

def get_db() -> DatabaseManager:
    """
    Use this in your Streamlit pages to get a single, persistent DatabaseManager.
    Requires SUPABASE_URL and SUPABASE_KEY in st.secrets or environment.
    """
    global _db_instance
    if _db_instance is None:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        _db_instance = DatabaseManager(url, key)
    return _db_instance
