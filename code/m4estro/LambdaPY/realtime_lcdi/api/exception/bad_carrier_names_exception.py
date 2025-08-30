class BadCarrierNamesException(Exception):
    """
    Exception raised when a carrier name is invalid.
    """

    def __init__(self, bad_names: str) -> None:
        super().__init__(f"Invalid carrier names: {bad_names}")
        self.bad_names: str = bad_names

    def __str__(self):
        return f"'{self.bad_names}' are not valid carrier names."