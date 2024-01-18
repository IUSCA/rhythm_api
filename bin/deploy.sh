RELEASE=$1

if [ -z "$RELEASE" ]; then
    echo "Production mode"
    sudo docker compose -f "docker-compose-prod.yml" build api
    sudo docker compose -f "docker-compose-prod.yml" up -d
else
    echo "Dev mode"
    sudo docker compose -f "docker-compose-dev.yml" build api
    sudo docker compose -f "docker-compose-dev.yml" up -d
fi
