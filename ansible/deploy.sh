#!/usr/bin/env bash
# Ejecuta el playbook desde WSL.
# ANSIBLE_CONFIG explícito: en /mnt/c (carpeta de Windows) Ansible ignora el
# ansible.cfg del directorio actual por considerarlo "world writable".
set -euo pipefail
cd "$(dirname "$0")"
export ANSIBLE_CONFIG="$PWD/ansible.cfg"
ansible-playbook site.yml --ask-vault-pass "$@"
