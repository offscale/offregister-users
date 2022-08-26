from collections import namedtuple
from io import StringIO

from offutils import ensure_quoted

User = namedtuple("User", ("name", "groups"))


def add_users0(*args, **kwargs):
    if "add_users" in kwargs:

        def one(user):
            user = User(
                user["name"], user.get("groups", (user["name"],)) or (user["name"],)
            )
            if (
                c.run(
                    "grep -q '{user.name}' /etc/passwd".format(user=user),
                    hide=True,
                    warn=True,
                ).exited
                != 0
            ):
                if (user.name,) == user.groups:
                    c.sudo("useradd -U '{user.name}'".format(user=user))
                else:
                    c.sudo(
                        "useradd '{user.name}' {groups}".format(
                            user=user,
                            groups=" -G ".join(map(ensure_quoted, user.groups)),
                        )
                    )
                return user

        return tuple(map(one, kwargs["add_users"]))
    elif "add_users_with_ssh" in kwargs:
        # TODO: All https://linux.die.net/man/8/useradd - I guess? - Or not worth the hassle?
        def one(user):
            if "ssh_authorized_keys" not in user:
                raise TypeError("Required: authorized_keys")
            elif "username" not in user:
                raise TypeError("Required: username")

            existent = c.sudo(
                "id -u {username}".format(username=user["username"]),
                warn=True,
                hide=True,
            )
            if existent.exited != 0:
                c.sudo(
                    "useradd -m {username} -s '{shell}' {rest}".format(
                        username=user["username"],
                        shell=user.get("shell", "/bin/bash"),
                        rest="-c '{name}'".format(name=user["fullname"])
                        if "fullname" in user
                        else "",
                    )
                )

                if "sudo" in user and user["sudo"]:
                    c.sudo(
                        "usermod -aG sudo {username}".format(username=user["username"])
                    )

            if not user["ssh_authorized_keys"]:
                return "{username}; skipped ssh_authorized_keys".format(
                    username=user["username"]
                )

            sio = StringIO()
            sio.write(user["ssh_authorized_keys"])
            ssh_dir = "/home/{username}/.ssh".format(username=user["username"])
            ssh_authorized_keys = "{ssh_dir}/authorized_keys".format(ssh_dir=ssh_dir)
            c.sudo(
                "mkdir -p '{}'".format(ssh_dir),
                user=user["username"],
            )
            c.put(
                sio,
                ssh_authorized_keys,
                # use_sudo=True
            )
            c.sudo(
                "chown {username} {ssh_authorized_keys}".format(
                    username=user["username"], ssh_authorized_keys=ssh_authorized_keys
                )
            )
            c.sudo(
                "chmod 0700 {ssh_dir}".format(
                    username=user["username"], ssh_dir=ssh_dir
                ),
                user=user["username"],
            )
            c.sudo(
                "chmod 0600 {ssh_authorized_keys}".format(
                    username=user["username"], ssh_authorized_keys=ssh_authorized_keys
                ),
                user=user["username"],
            )

            return user["username"]

        return tuple(map(one, kwargs["add_users_with_ssh"]))
