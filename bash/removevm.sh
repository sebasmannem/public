#!/bin/bash
VMNAME=${1:-vm_centos_cloud_1}

sudo virsh destroy "$VMNAME"
sudo virsh undefine "$VMNAME"
sudo lvremove -y /dev/Volume00/"$VMNAME"
