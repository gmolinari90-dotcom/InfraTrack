#!/bin/bash
set -e

# Attiva l'ambiente Conda
conda activate infratrack

# Esegui il comando che viene passato dal Dockerfile (il nostro "streamlit run ...")
exec "$@"
