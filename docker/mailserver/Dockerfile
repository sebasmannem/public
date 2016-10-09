FROM sebasmannem/c7-systemd
#FROM centos:latest
MAINTAINER Sebastiaan Mannem <sebas@mannem.nl>

RUN yum -y install postfix dovecot

EXPOSE 25
EXPOSE 110
EXPOSE 465
EXPOSE 995

ADD run_all.sh /run_all.sh
RUN chmod +x /run_all.sh

#CMD ["/run_all.sh"]
