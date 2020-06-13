#!/bin/sh
# set -x
set -e

echo "Starting Jupyter Notebook..."

jupyter-notebook "$@" --ip 0.0.0.0 \
          --no-browser \
          --allow-root \
          --NotebookApp.allow_password_change=False \
          --NotebookApp.token="$JUPYTER_TOKEN" \
          --NotebookApp.password='' \
          --NotebookApp.notebook_dir='/notebooks'

