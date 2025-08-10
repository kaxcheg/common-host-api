import json
from filelock import FileLock

PRIVATE_DATA_FILE_PATH = "tests/private_data.json"
lock = FileLock(f"{PRIVATE_DATA_FILE_PATH}.lock")

def compare_dicts(
    dict1: dict[str, object],
    dict2: dict[str, object],
    dict1_name: str,
    dict2_name: str,
) -> None:
    """Print a diff of keys and values between two dictionaries.

    Args:
        dict1: Left dictionary to compare.
        dict2: Right dictionary to compare.
        dict1_name: Label for the left dictionary.
        dict2_name: Label for the right dictionary.

    Returns:
        None
    """
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    only_in_dict1 = keys1 - keys2
    only_in_dict2 = keys2 - keys1
    common_keys = keys1 & keys2

    if only_in_dict1:
        print(f"Keys only in {dict1_name}: {only_in_dict1}")
    if only_in_dict2:
        print(f"Keys only in {dict2_name}: {only_in_dict2}")

    value_differences = {
        key: (dict1[key], dict2[key])
        for key in common_keys
        if dict1[key] != dict2[key]
    }

    if value_differences:
        print("Value differences:")
        for key, (val1, val2) in value_differences.items():
            print(f"Key '{key}': {dict1_name}={val1} | {dict2_name}={val2}")

    if not (only_in_dict1 or only_in_dict2 or value_differences):
        print("The dictionaries are identical.")


def get_OTP_from_input(msg: str) -> str:
    """Read OTP code from stdin until a non-empty value is provided.

    Args:
        msg: Prompt message.

    Returns:
        OTP string.
    """
    OTP = ""
    while not OTP:
        OTP = input(msg)
    return OTP

def write_private_data_to_file(**kwargs) -> None:
    """Update tests/private_data.json with provided non-empty fields.

    Args:
        **kwargs: Arbitrary private data fields to persist.

    Returns:
        None
    """
    with lock:
        with open(PRIVATE_DATA_FILE_PATH, "r") as f:
            data = json.load(f)
        
        data.update({key: value for key, value in kwargs.items() if value})

        with open(PRIVATE_DATA_FILE_PATH, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def read_private_data(key: str) -> object:
    """Return a value from tests/private_data.json by key.

    Args:
        key: JSON key to read.

    Returns:
        Stored value for the key.
    """
    with lock:
        with open(PRIVATE_DATA_FILE_PATH, "r", encoding="utf-8") as f:
            secrets = json.load(f)
    return secrets[key]