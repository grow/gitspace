## GCE configuration

    sudo mkdir /mnt/pd0
    sudo /usr/share/google/safe_format_and_mount -m "mkfs.ext4 -F" /dev/sdb /mnt/pd0
    sudo chmod a+w /mnt/pd0
    mkdir -p /mnt/pd0/growdata/git
