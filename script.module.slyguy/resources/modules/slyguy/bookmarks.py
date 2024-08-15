from slyguy import settings, log
from slyguy.constants import BOOKMARK_FILE
from slyguy.util import load_json, remove_file


def add(path, label=None, thumb=None, folder=1, playable=0):
    data = _load_favourites()
    data = [x for x in data if x['path'] != path]
    data.append({'path': path, 'label': label, 'thumb': thumb, 'folder': folder, 'playable': playable})
    _save_favourites(data)


def move(index, shift):
    data = _load_favourites()
    
    bookmark = data.pop(index)
    if not bookmark:
        return

    data.insert(index+shift, bookmark)
    _save_favourites(data)
    return data


def rename(index, name):
    data = _load_favourites()
    data[index]['label'] = name
    _save_favourites(data)
    return data


def delete(index):
    data = _load_favourites()
    data.pop(index)
    _save_favourites(data)
    return data


def get():
    return _load_favourites()


def _load_favourites():
    legacy = load_json(BOOKMARK_FILE, raise_error=False) or []
    if legacy:
        settings.BOOKMARKS_DATA.value = legacy
        remove_file(BOOKMARK_FILE)
        log.info("Migrated Bookmarks")

    return settings.BOOKMARKS_DATA.value


def _save_favourites(data):
    settings.BOOKMARKS_DATA.value = data
