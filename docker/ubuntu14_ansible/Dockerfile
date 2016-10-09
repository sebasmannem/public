FROM ubuntu:14.04
MAINTAINER S. Mannem
RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get -y install git make gcc python python-dev libffi-dev libssl-dev python-pip libgmp-dev sshpass
RUN pip install --upgrade setuptools
RUN useradd -m ansible_user
RUN su - ansible_user -c 'mkdir git ; cd git ; git clone https://github.com/ansible/ansible.git ; cd ansible ; git submodule update --init --recursive ; make'
RUN bash -c 'cd /home/ansible_user/git/ansible ; make install'

