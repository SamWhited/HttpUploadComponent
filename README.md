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

```component_jid```, ```component_secret``` and ```component_port``` have to match the corresponding entries in your XMPP
server config (Refer to the documentation of your server). 

```whitelist``` should contain a list of domains whos JIDs are allowed to
upload files. Remove the entry if you want to allow everyone (not really
recommended).

```get_url``` and ```put_url``` are prefixes to the URLs. The put_url is
usually a combination of your hostname and the port (Port can be ommited if
HTTP default ports are being used) The GET URL can use a different host if you
want to serve files using a standard nginx or another HTTP server that might be
more suitable for serving files than a python script.

For security purposes you should put the python script behind an HTTPS proxy or
stunnel (remember to adapt the URLs).  For quicker results you can also use the
built in TLS encryption by setting ```http_keyfile``` and ```http_certfile``` in the
config file.

For the configuration of the XMPP server side have a look into the contrib
directory or check the server documentation.

#### Expiry and user quotas

Expiry and user quotas are controlled by four config options:

```expire_interval``` determines how often (in seconds) files should be
deleted. As every expiry run needs to check all uploaded files of all
users this should not be set too small.

Files older than ```expire_maxage``` (in seconds) will be deleted by an
expiry run. Set this to ```0``` to disable deletions based on file age.

After an expiry run at most ```user_quota_soft``` space (in bytes) will be
occupied per user. The oldest files will be deleted first until the occupied
space is less than ```user_quota_soft```. Set this to ```0``` to disable
file deletions based on a users occupied space.

```user_quota_hard``` sets a hard limit how much space (in bytes) a user
may occupy. If an upload would make his files exceed this size it will be
rejected. This setting is not dependend on ```expire_interval```. Set
this to ```0``` to disable upload rejection based on occupied space.

```expire_maxage``` and ```user_quota_soft``` depend on ```expire_interval```.

```user_quota_hard``` is honoured even without expiry runs. But some kind
of expiry is recommended otherwise a user will not be able to upload
anymore files once his hard quota is reached.

The difference between ```user_quota_hard``` and ```user_quota_soft```
determines how much a user may upload per ```expire_interval```.

### Run

Running the component is as easy as invoking ```python server.py```

Some (unoffical) init scripts can be found in the contrib directory. Feel free
to write your own init scripts if necessary and contribute them back by
creating a pull request.

### Clients

Currently the only client with build in support is
[Conversations](http://conversations.im) where it is being used to send files
to Multi User Conferences and to multiple resources in 1 on 1 chats.
