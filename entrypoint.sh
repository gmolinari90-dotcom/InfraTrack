#!/bin/bash
set -e

# Usa 'source activate', il comando corretto per gli script non interattivi
source activate infratrack

# Esegui il comando che viene passato dal Dockerfile
exec "$@"
