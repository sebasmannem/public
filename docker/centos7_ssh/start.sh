for type in ecdsa rsa ed25519
do 
    ssh-keygen -t ${type} -f /etc/ssh/ssh_host_${type}_key -N ''
done
/usr/sbin/sshd
cat
