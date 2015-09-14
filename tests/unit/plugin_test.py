import mock
import pytest
import sleekxmpp

from httpupload.plugins import upload

@pytest.fixture
def client():
    """
    A sleekxmpp client with the upload plugin (and its dependencies) loaded.
    """

    c = sleekxmpp.ClientXMPP(
        'antonio@shakespeare.lit', 'supersecurepassword'
    )
    c.register_plugin('xep_0030')
    c.register_plugin('upload', module=upload)
    return c

@pytest.fixture
def upload_iq():
    return {
        'type': 'get'
    }


def test_handle_upload(client, upload_iq):
    """
    The upload handler should trigger an event.
    """

    client.plugin['upload'].xmpp = mock.Mock()
    client.plugin['upload']._handleUpload(upload_iq)
    client.plugin['upload'].xmpp.event.assert_called_once_with(
        'request_upload_slot',
        upload_iq
    )
