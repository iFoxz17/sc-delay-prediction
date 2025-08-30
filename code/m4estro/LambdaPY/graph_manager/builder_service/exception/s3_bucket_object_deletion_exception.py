class S3BucketObjectDeletionException(Exception):
    def __init__(self, bucket_name: str, object_key: str):
        super().__init__(f"Failed to delete object '{object_key}' from bucket '{bucket_name}'.")

        self.bucket_name: str = bucket_name
        self.object_key: str = object_key

    def __str__(self):
        return f"Failed to delete object '{self.object_key}' from bucket '{self.bucket_name}'."