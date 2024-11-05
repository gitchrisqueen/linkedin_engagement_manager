#!/bin/bash
set -e

# Run the original entrypoint script
/usr/local/bin/docker-entrypoint.sh mysqld &

# Wait for MySQL to start
until mysqladmin ping -h "localhost" --silent; do
  echo 'waiting for mysqld to be connectable...'
  sleep 2
done

# Execute all SQL scripts in the migrations directory
for f in /docker-entrypoint-initdb.d/migrations/*.sql; do
  echo "Running $f"
  mysql -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} < "$f"
done

# Wait for the original entrypoint script to finish
wait