#!/bin/bash
set -e

# Attiva l'ambiente Conda
conda activate infratrack

# Esegui il comando passato dal Dockerfile
exec "$@"
