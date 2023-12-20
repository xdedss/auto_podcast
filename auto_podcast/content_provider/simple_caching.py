
import os
import hashlib
import logging

logger = logging.getLogger(__name__)

def calculate_md5(input_string):
    md5_hash = hashlib.md5()
    md5_hash.update(input_string.encode('utf-8'))
    md5_hex = md5_hash.hexdigest()
    return md5_hex

def get_text_cache(temp_path: str, identifier: str):
    if (os.path.isdir(temp_path)):
        fname = calculate_md5(identifier) + '.txt'
        fpath = os.path.join(temp_path, fname)
        if (os.path.isfile(fpath)):
            with open(fpath, 'r', encoding='utf-8') as f:
                return f.read()
    return None

def save_text_cache(temp_path: str, identifier: str, text: str):
    os.makedirs(temp_path, exist_ok=True)
    fname = calculate_md5(identifier) + '.txt'
    fpath = os.path.join(temp_path, fname)
    if (os.path.exists(fpath)):
        logger.warn(f'possible cache hash collision for {fpath}')
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(text)

# def cached_func(temp_path: str):
#     def wrapper(fn):
#         pass
#     return wrapper
