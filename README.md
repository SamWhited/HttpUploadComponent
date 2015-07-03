# HttpUploadComponent
The HttpUploadComponent is a plugin extension to your XMPP server that allows users to upload files to a HTTP host and eventually share the link to those files.
It runs as a stand alone process on the same host as your XMPP server and connects to that server using the [Jabber Component Protocol](http://xmpp.org/extensions/xep-0114.html).

A detailed introduction into the necessity of such a component and the simple protocol can be found on the [XMPP Standards email list](http://mail.jabber.org/pipermail/standards/2015-June/029969.html).

###Configuration
Configuration happens in config.yml and is pretty straight forward.

```jid``` and ```secret``` have to match the corresponding entries in your XMPP server config (Refer to the documentation of your server).

```whitelist``` should contain a list of domains whos JIDs are allowed to upload files. Remove the entry if you want to allow everyone (not really recommended).

```get_url``` and ```put_url``` are prefixes to the URLs. The put_url is usually a combination of your hostname and the port (Port can be ommited if HTTP default ports are being used) The GET URL can use a different host if you want to serve files using a standard nginx or another HTTP server that might be more suitable for serving files than a python script.

For security purposes you should put the python script behind an HTTPS proxy or stunnel (remember to adapt the URLs)

###Run
Running the component is as easy as invoking ```python server.py```

Feel free to write your own init scripts if necessary and contribute them back by creating a pull request.

###Clients
Currently the only client with build in support is [Conversations](http://conversations.im). (unreleased version 1.5). Conversations uses this to send files to Multi User Conferences and to multiple resources in 1 on 1 chats.
