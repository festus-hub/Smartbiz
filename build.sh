#!/usr/bin/env bash
set -o errexit

cd smartbiz

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
