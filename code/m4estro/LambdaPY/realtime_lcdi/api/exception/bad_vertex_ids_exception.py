class BadVertexIdsException(Exception):
    """
    Exception raised when a vertex ID is invalid.
    """

    def __init__(self, bad_ids: str) -> None:
        super().__init__(f"Invalid vertex IDs: {bad_ids}")
        self.bad_ids: str = bad_ids

    def __str__(self):
        return f"'{self.bad_ids}' are not valid vertex IDs."