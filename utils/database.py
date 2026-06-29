import uuid
class DatabaseManager:
    def __init__(self, url, key):
        # your existing init...
        pass

    # ... other existing methods ...

    # INSERT THE NEW METHOD HERE, after any existing methods but inside the class
    def get_statistics(self):
        """Fetches counts for all main nursery collections."""
        try:
            total_plants = self.client.table("plants").select("*", count='exact').execute().count
            total_fertilizers = self.client.table("fertilizers").select("*", count='exact').execute().count
            total_insecticides = self.client.table("insecticides").select("*", count='exact').execute().count
            total_pesticides = self.client.table("pesticides").select("*", count='exact').execute().count
            total_printed_tags = 0  # adjust if you have a tags table
            return {
                'total_plants': total_plants,
                'total_fertilizers': total_fertilizers,
                'total_insecticides': total_insecticides,
                'total_pesticides': total_pesticides,
                'total_printed_tags': total_printed_tags
            }
        except Exception as e:
            print(f"Error fetching statistics: {e}")
            return {
                'total_plants': 0, 'total_fertilizers': 0,
                'total_insecticides': 0, 'total_pesticides': 0,
                'total_printed_tags': 0
            }
