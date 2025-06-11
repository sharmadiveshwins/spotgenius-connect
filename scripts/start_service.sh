#!/usr/bin/env bash

# Script to start the backend service defined by docker-compose.yml
# Launch this script from the root of the repository.

# Write all environment variables provided by azure into a .env file
# so that we can start the container without an azure release later.

# Check if service is already running, and stop it.
running_id=$(docker-compose ps -q)

if [ -n "$running_id" ] && [ "$running_id" != " " ]; then
    echo "Stopping running docker-compose service $running_id"
    docker-compose down
fi

echo "Launching docker-compose.yml from directory: $PWD"
docker-compose up --build -d