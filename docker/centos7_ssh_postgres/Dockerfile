#docker build --rm -t centos7_ssh_postgres .
#docker run -id centos7_ssh
#docker inspect [new container]
#ssh [inspect>NetworkSettings>IPAddres] -i id_rsa

FROM centos7_ssh
MAINTAINER S. Mannem
RUN yum -y install http://yum.postgresql.org/9.4/redhat/rhel-latest-x86_64/pgdg-centos94-9.4-2.noarch.rpm
RUN yum -y install postgresql94-server
RUN su - postgres -c '/usr/pgsql-9.4/bin/pg_ctl init -D /var/lib/pgsql/9.4/data ; mkdir /var/lib/pgsql/9.4/data/conf.d'
RUN echo -e "include_dir = 'conf.d'\nlisten_addresses = '*'" >> /var/lib/pgsql/9.4/data/postgresql.conf
COPY start.sh master.sh standby.sh /
