#Download Oracle RDBMS 11 XE from the website.
#unzip file to this folder, creating a subfolder Disk1 with oracle-xe-11.2.0-1.0.x86_64.rpm (amongst others)
#build with 'docker build --shm-size=4G -t oraclexe:latest .'
FROM centos:6
COPY Disk1/oracle-xe-11.2.0-1.0.x86_64.rpm /tmp
COPY autoconfig.response /tmp
RUN yum -y update
RUN yum -y install bc
RUN yum -y install /tmp/oracle-xe-11.2.0-1.0.x86_64.rpm
RUN /etc/init.d/oracle-xe configure responseFile=/tmp/autoconfig.response

EXPOSE 1521
EXPOSE 8080

RUN yum -y install epel-release
RUN yum -y install python-pip gcc python-devel
RUN pip install --upgrade pip
RUN ORACLE_HOME=/u01/app/oracle/product/11.2.0/xe pip install cx_Oracle
RUN ln -s /u01/app/oracle/product/11.2.0/xe/lib/libclntsh.so.11.1 /lib64
RUN ln -s /u01/app/oracle/product/11.2.0/xe/lib/libnnz11.so /lib64

COPY start_oracle /tmp
RUN chmod 755 /tmp/start_oracle

#You can now start the container with 'docker run --rm -ti --privileged --shm-size=4G -p 1521 -p 8080 oraclexe:latest /tmp/start_oracle'
