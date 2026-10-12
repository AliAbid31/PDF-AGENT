from azure.storage.blob import BlobServiceClient
from fastapi import HTTPException
from app.core.config import settings

class AzureStorage:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_client = self.blob_service_client.get_container_client(
            settings.AZURE_CONTAINER_NAME
        )

        try:
            if not self.container_client.exists():
                self.container_client.create_container()
        except Exception:
            pass

    def upload_file(self, filebytes: bytes, filename: str, content_type: str = "application/pdf") -> str:
        try:
            blob_client = self.container_client.get_blob_client(filename)
            blob_client.upload_blob(filebytes, overwrite=True, content_type=content_type)
            return blob_client.url
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

azure_storage = AzureStorage()