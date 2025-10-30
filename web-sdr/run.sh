#!/bin/sh

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose down --remove-orphans
docker compose up
docker compose down