# HttpUploadComponent

The HttpUploadComponent is a plugin extension to your XMPP server that allows
users to upload files to a HTTP host and eventually share the link to those
files.

It runs as a stand alone process on the same host as your XMPP server and
connects to that server using the [Jabber Component
Protocol](http://xmpp.org/extensions/xep-0114.html).

A detailed introduction into the necessity of such a component and the simple
protocol can be found on the [XMPP Standards email
list](http://mail.jabber.org/pipermail/standards/2015-June/029969.html).

### Configuration

Configuration happens in `config.yml` and is pretty straight forward.

`jid` and `secret` have to match the corresponding entries in your XMPP server
config (Refer to the documentation of your server).

`whitelist` should contain a list of domains who's JIDs are allowed to upload
files. Remove the entry if you want to allow everyone (not really recommended).

`get_url` and `put_url` are prefixes to the URLs. The PUT URL is usually a
combination of your hostname and the port (Port can be omitted if HTTP default
ports are being used) The GET URL can use a different host if you want to serve
files using nginx or another HTTP server that might be more suitable for
serving files than the Python script. If you intend to delegate storage to
Amazon S3, the various `aws_` prefixed keys should be uncommented and filled
out in the config, and the GET URL should be set to:
`https://s3[-region].amazonaws.com/<yourbucket>` (where `region` is the region
you've placed your bucket in, eg. `us-east-1`, or left off if the default was
used).

For security purposes you should put the Python script behind an HTTPS proxy or
tunnel (remember to adapt the URLs). For quicker results you can also use the
built in TLS encryption by setting `keyfile` and `certfile` in the config file.

For XMPP server configuration help, have a look in the `contrib` directory or
check your chosen server's documentation.

### Run

Running the component is as easy as invoking `python server.py`

Some (unofficial) init scripts can be found in the contrib directory. Feel free
to write your own init scripts if necessary and contribute them back by
creating a pull request.

### Clients

Currently the only client with build in support is
[Conversations](http://conversations.im) where it is being used to send files
to Multi User Conferences and to multiple resources in 1 to 1 chats.
