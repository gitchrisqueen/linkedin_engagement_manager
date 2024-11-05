#!/bin/bash

# Source the .env file to load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

flyway -baselineOnMigrate=True -validateMigrationNaming=True -url=jdbc:mysql://${MYSQL_HOST}/${MYSQL_DATABASE} -schemas=${MYSQL_DATABASE} -user=${MYSQL_USER} -password=${MYSQL_PASSWORD} -connectRetries=3 repair
flyway -baselineOnMigrate=True -validateMigrationNaming=True -url=jdbc:mysql://${MYSQL_HOST}/${MYSQL_DATABASE} -schemas=${MYSQL_DATABASE} -user=${MYSQL_USER} -password=${MYSQL_PASSWORD} -connectRetries=3 migrate