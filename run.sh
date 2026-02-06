#!/bin/bash

AGENT_DIR_UNIX="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
USER_PROJECT_PATH=$(pwd)

OS_TYPE="unknown"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    OS_TYPE="windows"
fi

if [ "$OS_TYPE" == "windows" ]; then
    export MSYS_NO_PATHCONV=1
    ENV_PATH=$(cygpath -w "$AGENT_DIR_UNIX/.env")
    DOCKER_MOUNT_POINT="//project"
else
    ENV_PATH="$AGENT_DIR_UNIX/.env"
    DOCKER_MOUNT_POINT="/project"
fi


echo "AI Migrator: Аналіз середовища..."
if [[ "$(docker images -q library-migrator:latest 2> /dev/null)" == "" ]]; then
    echo "Образ не знайдено. Збираю..."
    cd "$AGENT_DIR_UNIX" && docker-compose build
    cd "$USER_PROJECT_PATH"
fi

INTERNAL_PROJECT_PATH="/project"

docker run --rm -it \
    -v "$USER_PROJECT_PATH":"$DOCKER_MOUNT_POINT" \
    --env-file "$ENV_PATH" \
    -u $(id -u):$(id -g) \
    -e HOME=/tmp \
    library-migrator:latest \
    python main.py "$INTERNAL_PROJECT_PATH" "$@"