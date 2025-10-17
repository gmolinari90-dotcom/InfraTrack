#!/bin/bash
set -e

# Non tentiamo di attivare l'ambiente.
# Usiamo 'conda run' per eseguire il comando passato
# direttamente DENTRO l'ambiente specificato.
exec conda run -n infratrack "$@"
