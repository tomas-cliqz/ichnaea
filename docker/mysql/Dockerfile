FROM mysql:5.6.27
ENV MYSQL_ROOT_PASSWORD=mysql
COPY my.cnf /etc/mysql/conf.d/my.cnf
VOLUME /var/lib/mysql

COPY setup.sh run.sh /
EXPOSE "3306"
CMD ["/bin/bash", "/run.sh"]
