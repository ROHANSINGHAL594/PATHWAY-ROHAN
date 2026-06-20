FROM postgres:17


COPY pipeline_db_init.sh /docker-entrypoint-initdb.d/init.sh
EXPOSE 5432
# Make file executable
RUN chmod +x /docker-entrypoint-initdb.d/init.sh