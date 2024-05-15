# pyhelper-utils

Repository for various python utilities

## Installation

```bash
python3 -m pip install pyhelper-utils
```

## Release new version

### requirements:

- Export GitHub token

```bash
export GITHUB_TOKEN=<your_github_token>
```

- [release-it](https://github.com/release-it/release-it)

- Run the following once (execute outside repository dir for example `~/`):

```bash
sudo npm install --global release-it
npm install --save-dev @j-ulrich/release-it-regex-bumper
rm -f package.json package-lock.json
```

### usage:

- Create a release, run from the relevant branch.
  To create a new release, run:

```bash
git checkout main
git pull
release-it # Follow the instructions
```

### Examples:

Enables running a command against a remote server over SSH. It expects a host object, created using [python-rrmngmnt](https://github.com/rhevm-qe-automation/python-rrmngmnt).

#### Sample code:

```bash
from rrmngmnt import Host, UserWithPKey
host = Host("1.1.1.1")
user = UserWithPKey('user', '/path/to/pkey'))
host.executor_user =  user
run_ssh_command(host=host, commands=shlex.split("ls -l"))
```
