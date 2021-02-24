![Python package](https://github.com/RhinoSecurityLabs/dsnap/workflows/Python%20package/badge.svg?branch=main)

# dsnap

Utility for downloading EBS snapshots using the EBS Direct API's.

## Install

### PyPi

```shell
% pip install -U pip
% pip install 'dsnap[cli]'
```

## Command Reference

```shell
% dsnap --help
Usage: dsnap [OPTIONS] COMMAND [ARGS]...

  A utility for managing snapshots via the EBS Direct API.

Options:
  --region REGION                 Sets the AWS region.  [default: us-east-1]
  --profile PROFILE               Shared credential profile to use.
  --install-completion [bash|zsh|fish|powershell|pwsh]
                                  Install completion for the specified shell.
  --show-completion [bash|zsh|fish|powershell|pwsh]
                                  Show completion for the specified shell, to
                                  copy it or customize the installation.

  --help                          Show this message and exit.

Commands:
  create  Create a snapshot for the given instances default device volume.
  delete  Delete a given snapshot.
  get     Download a snapshot for a given instance or snapshot ID.
  init    Write out a Vagrantfile template to explore downloaded snapshots.
  list    List snapshots in AWS.
```

## Examples

### Recording

![Alt Text](./docs/demo.gif)

### Listing Snapshots
```shell
% dsnap list
           Id          |   Owner ID   |   State
snap-0dbb0347f47e38b96   922105094392   completed
```

### Downloading a Snapshot
```shell
% dsnap get snap-0dbb0347f47e38b96
Output Path: /cwd/snap-0dbb0347f47e38b96.img
```

If you don't specify a snapshot  you'll get a prompt to ask which one you want to download:
```shell
% dsnap get
0) i-01f0841393cd39f06 (ip-172-31-27-0.ec2.internal, vpc-04a91864355539a41, subnet-0e56cd55282fa9158)
Select Instance: 0
0) vol-0a1aab48b0bc3039d (/dev/sdb)
1) vol-0c616d718ab00e70c (/dev/xvda)
Select Volume: 0
No snapshots found, create one? [y/N]: y
Creating snapshot for Instance(s): i-01f0841393cd39f06 /dev/sdb, Volume: vol-0a1aab48b0bc3039d
Waiting for snapshot to complete.
Output Path: /cwd/snap-0dbb0347f47e38b96.img
Cleaning up snapshot: snap-0543a8681adce0086
```

### Mounting in Vagrant
This requires virtualbox to be installed. dsnap init will write a Vagrantfile to the current directory that can be used to mount a specific downloaded snapshot. Conversion to a VDI disk is handled in the Vagrantfile, it will look for the disk file specified in the IMAGE environment variable, convert it to a VDI using `VBoxManage convertdd`. The resulting VDI is destroyed when the Vagrant box is, however the original raw .img file will remain and can be reused as needed.

```shell
% dsnap init
% IMAGE=snap-0543a8681adce0086.img vagrant up
% vagrant ssh
```

### Mounting With Docker

This uses libguestfs to work directly with the downloaded img file.

#### Build Docker Container
```shell
% git clone https://github.com/RhinoSecurityLabs/dsnap.git
% cd dsnap
% make docker/build
```

#### Run Guestfish Shell

```shell
% IMAGE=snap-0dbb0347f47e38b96.img make docker/run
```

This will take a second to start up. After it drops you into the shell you should be able to run commands like ls, cd, cat. However worth noting they don't always behave exactly like they do in a normal shell.

The output will give you the basics of how to use the guestfish shell. For a full list of command you can run `help --list`.

Below is an example of starting the shell and printing the contents of /etc/os-release.

```shell
% IMAGE=snap-0dbb0347f47e38b96.img make docker/run
docker run -it -v "/cwd/dsnap/snap-0dbb0347f47e38b96.img:/disks/snap-0dbb0347f47e38b96.img" -w /disks mount --ro -a "snap-0dbb0347f47e38b96.img" -m /dev/sda1:/

Welcome to guestfish, the guest filesystem shell for
editing virtual machine filesystems and disk images.

Type: ‘help’ for help on commands
      ‘man’ to read the manual
      ‘quit’ to quit the shell

><fs> cat /etc/os-release
NAME="Amazon Linux"
VERSION="2"
ID="amzn"
ID_LIKE="centos rhel fedora"
VERSION_ID="2"
PRETTY_NAME="Amazon Linux 2"
ANSI_COLOR="0;33"
CPE_NAME="cpe:2.3:o:amazon:amazon_linux:2"
HOME_URL="https://amazonlinux.com/"
```

## Library Use

dsnap is also meant to be used as a library, however for this purpose it is worth keeping in mind this is an early version and it is still being developed. The interfaces will likely change as new functionality is added.

We'll do our best to make sure we follow SemVer versioning to avoid any breaking changes in minor and patch versions.

## Development

For CLI development make sure you include the `cli` extra shown below. You'll also want to invoke the package by using python's `-m` (shown below) for testing local changes, the dnsap binary installed to the environment will only update when you run pip install.

### Setup
```shell
% git clone https://github.com/RhinoSecurityLabs/dsnap.git
% cd dsnap
% python3 -m venv venv
% . venv/bin/activate
% python -m pip install '.[cli]'
```

### Running With Local Changes
```shell
% python -m dsnap --help
```

### Linting and Type Checking
```shell
% make lint
```

### Testing
```shell
% make test
```

