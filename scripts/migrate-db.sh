#!/bin/bash

# Migrates the development database

cd "$(dirname "$0")"

PGPASSWORD=postgres psql -h localhost  -U postgres -f ../db/init.sql
