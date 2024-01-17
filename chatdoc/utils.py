import os
from datetime import date
from pathlib import Path
from werkzeug.utils import secure_filename
import re


class Utils:
    """
    A utility class that provides various helper functions.
    """

    @staticmethod
    def get_env_variable(variable_name: str) -> str:
        """
        Retrieves the value of an environment variable.

        Args:
            variable_name (str): The name of the environment variable.

        Returns:
            str: The value of the environment variable.

        Raises:
            ValueError: If the environment variable is not set.
        """
        if variable_name not in os.environ:
            raise ValueError(f"{variable_name} not set in environment")
        else:
            return os.environ[variable_name]

    @staticmethod
    def get_unique_filename(raw_filename: str) -> str:
        """
        Generate a unique filename based on the current date and the given raw filename.

        Args:
            raw_filename (str): The original filename.

        Returns:
            str: The unique filename in the format 'filename_current_date.extension'.
        """
        # current_date: str = date.today().strftime("%Y-%m-%d")
        secure_file_name = secure_filename(raw_filename)
        secure_path = Path(secure_file_name)
        return f"{secure_path.stem}{secure_path.suffix}"

    @staticmethod
    def remove_date_from_filename(filename: str) -> str:
        """
        Remove the date from the given filename.

        Args:
            filename (str): The filename.

        Returns:
            str: The filename without the date.
        """
        pattern = r"_\d{4}-\d{2}-\d{2}_"
        return re.sub(pattern, "", filename)
