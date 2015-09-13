import mock
import pytest

from httpupload import server

@pytest.fixture
def fakeos():
    with mock.patch('httpupload.server.os') as fakeos:
        server.os.listdir.return_value = ('bar.jpg', 'baz.jpg')
        server.os.walk.return_value = (
            ('', None, ('bar.jpg', 'baz.jpg')),
        )
        return fakeos

def test_file_not_found_error_exists():
    """
    Ensure that FileNotFound error exists (as a fallback for Python 2.7).
    """

    try:  # pragma: no cover
        FileNotFoundError
    except NameError:  # pragma: no cover
        server.FileNotFoundError

def test_path_normalization():
    """
    Ensure that paths are properly normalized to prevent accessing '../'
    directories.
    """

    cases = {
        '../': '..',
        '../../': '../..',
        '../..': '../..',
        '/': '/',
        '/..': '/',
        '/../../': '/',
        '/../..': '/',
        'base': 'base',
        'base/': 'base',
        'base/../': '.',
        'base/..': '.',
        'base/../../': '..',
        'base/../..': '..',
        'base/../.': '.',
        '../base': '../base',
        './base/': 'base',
        './base': 'base',
    }

    for key in cases.keys():
        assert cases[key] == server.normalize_path(key)

def test_expire_no_kill_event(fakeos):
    """
    Ensure that an error is thrown if no kill event is specified.
    """

    with pytest.raises(AttributeError):
        server.expire(quotaonly=False, kill_event=None)
