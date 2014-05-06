## GCE configuration

    # For building growsdk.
    sudo apt-get install libxml2-dev
    sudo apt-get install libxslt1-dev

    sudo apt-get install upstart
    sudo apt-get install nginx
    sudo apt-get install libpcre3 libpcre3-dev
    sudo apt-get install uwsgi

    sudo ln -s gitspace_uwsgi.conf /etc/init/
    sudo ln -s gitspace_nginx.conf /etc/nginx/sites-enabled/

    sudo mkdir /mnt/pd0
    sudo /usr/share/google/safe_format_and_mount -m "mkfs.ext4 -F" /dev/sdb /mnt/pd0
    sudo chmod a+w /mnt/pd0
    mkdir -p /mnt/pd0/growdata/git

### Installing PageSpeed

    svn checkout http://gyp.googlecode.com/svn/trunk/ gyp-read-only
    python setup.py install
