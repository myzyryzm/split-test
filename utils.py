import os
import sysconfig

def fstr(val:float):
    return str(round(val,3))

def file_exist_check(location: str):
    """
    Check if a file exists on the system. If so return the location.
    Otherwise assert.
    """
    loc_abs = os.path.abspath(location)
    assert os.path.exists(loc_abs), '%s does not exist on the filesystem!' % loc_abs
    return loc_abs

def make_directory(location: str):
    """
    Make a directory if it does not exist
    """
    if not os.path.exists(location):
        os.makedirs(location)
    return

def get_file_name(file_path: str) -> str:
    """
    Get the file name given the file path.
    """
    return file_path.split('/')[-1]  # os.path.basename(file_path)

def append_slash(to_append: str) -> str:
    if to_append[-1] == '/':
        return to_append
    return to_append + '/'

def append_postfix(media_file_path: str, post_fix: str) -> str:
    """
    Appends a postfix string before the extension.
    """
    return '.'.join([media_file_path.split('.')[0] + post_fix, media_file_path.split('.')[1]])
