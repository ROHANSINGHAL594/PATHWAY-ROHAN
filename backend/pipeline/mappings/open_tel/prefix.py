open_tel_prefix = "_open_tel_"

def is_special_column(column_name: str) -> bool:
    """
    Check if a column is special (contains the _open_tel_ prefix).
    
    Args:
        column_name: Name of the column to check
    
    Returns:
        True if column is special, False otherwise
    """
    return open_tel_prefix in column_name