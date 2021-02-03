# DSnap

Utility for downloading EBS snapshots using the EBS Direct API's.

## Install

```
git clone https://github.com/RyanJarv/dsnap.git
cd dsnap
python -m venv venv 
pip install -r requirements.txt
. venv/bin/activate
python -m dsnap --help 
```

## Examples

### Listing Snapshots
```
% python -m dsnap --profile demo list
           Id          |   Owner ID   |   State
snap-0dbb0347f47e38b96   922105094392   completed
```

### Downloading Snapshot
```
% python -m dsnap --profile demo get snap-0dbb0347f47e38b96
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
