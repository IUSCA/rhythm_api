#!/bin/sh
RELEASE=$2

if [ -z "$RELEASE" ]; then
    echo "Production mode"
    sudo docker compose -f docker-compose-prod.yml logs -t -f $1 
else
    echo "Dev mode"
    sudo docker compose -f docker-compose-dev.yml logs -t -f $1 
fi