#!/bin/sh
set -eu

cd /opt/foodgram
/usr/bin/docker compose -f infra/docker-compose.yml \
    exec -T nginx nginx -s reload
