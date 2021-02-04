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

### Downloading Snapshot
```
% dsnap --profile demo get snap-0dbb0347f47e38b96
Output Path: /cwd/output.img
```

If you don't specify a snapshot  you'll get a prompt to ask which one you want to download:
```
% dsnap --profile demo get
0) snap-0dbb0347f47e38b96 (Description: feb2, Size: 8GB)
1) snap-0772d047d81e0a5e5 (Description: test3, Size: 8GB)
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

