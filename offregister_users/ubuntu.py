from collections import namedtuple
from itertools import imap

from cStringIO import StringIO
from fabric.operations import sudo, run, put

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
    elif 'add_users_with_ssh' in kwargs:
        # TODO: All https://linux.die.net/man/8/useradd - I guess? - Or not worth the hassle?
        def one(user):
            if 'ssh_authorized_keys' not in user:
                raise TypeError('Required: authorized_keys')
            elif 'username' not in user:
                raise TypeError('Required: username')

            existent = sudo('id -u {username}'.format(username=user['username']), warn_only=True, quiet=True)
            if existent.failed:
                sudo("useradd -m {username} -s '{shell}' {rest}".format(
                    username=user['username'],
                    shell=user.get('shell','/bin/bash'),
                    rest="-c '{name}'".format(name=user['fullname']) if 'fullname' in user else ''
                ), shell_escape=False)

                if 'sudo' in user and user['sudo']:
                    sudo('usermod -aG sudo {username}'.format(username=user['username']))

            if not user['ssh_authorized_keys']:
                return '{username}; skipped ssh_authorized_keys'.format(username=user['username'])

            sio = StringIO()
            sio.write(user['ssh_authorized_keys'])
            ssh_dir = '/home/{username}/.ssh'.format(username=user['username'])
            ssh_authorized_keys ='{ssh_dir}/authorized_keys'.format(ssh_dir=ssh_dir)
            sudo("mkdir -p '{}'".format(ssh_dir), shell_escape=False, user=user['username'])
            put(sio, ssh_authorized_keys, use_sudo=True)
            sudo('chown {username} {ssh_authorized_keys}'.format(
                username=user['username'], ssh_authorized_keys=ssh_authorized_keys
            ))
            sudo('chmod 0700 {ssh_dir}'.format(
                username=user['username'], ssh_dir=ssh_dir
            ), user=user['username'])
            sudo('chmod 0600 {ssh_authorized_keys}'.format(
                username=user['username'], ssh_authorized_keys=ssh_authorized_keys
            ), user=user['username'])

            return user['username']

        return tuple(imap(one, kwargs['add_users_with_ssh']))
