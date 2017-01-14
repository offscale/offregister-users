from collections import namedtuple
from itertools import imap

from fabric.operations import sudo, run

User = namedtuple('User', ('name', 'groups'))


def add_users0(*args, **kwargs):
    if 'add_users' in kwargs:
        def one(user):
            user = User(user['name'], user.get('groups', (user['name'],)) or (user['name'],))
            if run("grep -q '{user.name}' /etc/passwd".format(user=user), quiet=True, warn_only=True).failed:
                if (user.name,) == user.groups:
                    sudo("useradd -U '{user.name}'".format(user=user))
                else:
                    sudo("useradd '{user.name}' {groups}".format(user=user,
                                                                 groups=' -G '.join(imap(lambda n: "'{}'".format(n),
                                                                                         user.groups))))
                return user

        return tuple(imap(one, kwargs['add_users']))
