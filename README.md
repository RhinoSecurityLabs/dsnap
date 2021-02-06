# DSnap

Utility for downloading EBS snapshots using the EBS Direct API's.

## Install

### PyPi

NOTE: This won't work until this package is published, for now see [Development](#Development)

```
% pip install 'dsnap[cli]'
```

## Examples

### Listing Snapshots
```
% dsnap --profile demo list
           Id          |   Owner ID   |   State
snap-0dbb0347f47e38b96   922105094392   completed
```

### Downloading a Snapshot
```
% dsnap --profile demo get snap-0dbb0347f47e38b96
Output Path: /cwd/output.img
```

If you don't specify a snapshot  you'll get a prompt to ask which one you want to download:
```
% python -m dsnap --profile chris get
0) i-01f0841393cd39f06 (ip-172-31-27-0.ec2.internal, vpc-04a91864355539a41, subnet-0e56cd55282fa9158)
Select Instance: 0
0) vol-0a1aab48b0bc3039d (/dev/sdb)
1) vol-0c616d718ab00e70c (/dev/xvda)
Select Volume: 0
No snapshots found, create one? [y/N]: y
Creating snapshot for Instance(s): i-01f0841393cd39f06 /dev/sdb, Volume: vol-0a1aab48b0bc3039d
Waiting for snapshot to complete.
Output Path: /cwd/output.img
Cleaning up snapshot: snap-0543a8681adce0086
```

### Converting to VDI
This requires virtualbox to be installed.

```
% VBoxManage convertdd output.img output.vdi
Converting from raw image file="output.img" to file="output.vdi"...
Creating dynamic image with size 8589934592 bytes (8192MB)...
```

### Attaching to Vagrant Box

You can attach the resulting vdi to virtualbox through vagrant with:

```
    vb.customize ['storageattach', :id, '--storagectl', 'SATA Controller', '--port', 1, '--device', 0, '--type', 'hdd', '--medium', "./output.vdi"]
```

A complete Vagrant config will look something like this:
```
# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-20.04"

  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder "vagrant", "/vagrant"

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "1024"
    vb.customize ['storageattach', :id, '--storagectl', 'SATA Controller', '--port', 1, '--device', 0, '--type', 'hdd', '--medium', "./output.vdi"]
  end

  config.vm.provision "shell", inline: <<-SHELL
    sudo mkdir /mnt/snapshot
    sudo mount /dev/sdb1 /mnt/snapshot
  SHELL
end
```

### Mounting With Docker

This uses libguestfs to work directly with the downloaded img file.

#### Build Docker Container
```
git clone https://github.com/RhinoSecurityLabs/dsnap.git
cd dsnap
make docker/build
```

#### Run Guestfish Shell

```
IMAGE=output.img make docker/run
```

This will take a second to start up. After it drops you into the shell you should be able to run commands like ls, cd, cat. However worth noting they don't always behave exactly like they do in a normal shell.

The output will give you the basics of how to use the guestfish shell. For a full list of command you can run `help --list`.

Below is an example of starting the shell and printing the contents of /etc/os-release.

```
% IMAGE=output2.img make docker/run
docker run -it -v "/cwd/dsnap/output2.img:/disks/output2.img" -w /disks mount --ro -a "output2.img" -m /dev/sda1:/

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


## Development

For CLI development make sure you include the `cli` extra shown below. You'll also want to invoke the package by using python's `-m` (shown below) for testing local changes, the dnsap binary installed to the environment will only update when you run pip install.

### Setup
```
git clone https://github.com/RhinoSecurityLabs/dsnap.git
cd dsnap
python3 -m venv venv
. venv/bin/activate
python -m pip install '.[cli]'
```

### Running With Local Changes
```
python -m dsnap --help
```

### Linting and Type Checking
```
make lint
```

### Testing
```
make test
```

