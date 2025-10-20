#!/bin/sh

docker compose down --remove-orphans
docker compose up
docker compose down