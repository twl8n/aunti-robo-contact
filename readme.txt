

feb 24 2010

New read_config() calls read_config_core() so that the name of the
config file is read from local .config and the real config is not in a
web accessible area.

By convention, the read config files are ~/name_config.txt as in
bug_config.txt, bmw_config.txt, etc.

Also added a new "from" value because it needs to be an email address
that resolves to the sending domain. Google checks this apparently as
an anti-spam measure. No surprise.

