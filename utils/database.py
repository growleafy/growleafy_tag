import uuid # Add this import at the very top of the file if not already there

class DatabaseManager:
    # ... your existing init and methods ...

    def upload_image(self, file_bytes, original_filename):
        """
        Uploads an image to Supabase Storage and returns the public URL.
        """
        try:
            # 1. Generate a unique filename to prevent accidental overwrites
            file_extension = original_filename.split(".")[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            
            # 2. Upload the file to the 'plant-images' bucket
            self.client.storage.from_("plant-images").upload(
                file=file_bytes,
                path=unique_filename,
                file_options={"content-type": f"image/{file_extension}"}
            )
            
            # 3. Retrieve and return the permanent public URL
            public_url = self.client.storage.from_("plant-images").get_public_url(unique_filename)
            return public_url
            
        except Exception as e:
            # Log the error and return None if upload fails
            print(f"Supabase Storage Upload Error: {e}")
            return None
