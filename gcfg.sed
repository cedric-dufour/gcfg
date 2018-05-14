#!/bin/bash
# INDENTING (emacs/vi): -*- mode:bash; tab-width:2; c-basic-offset:2; intent-tabs-mode:nil; -*- ex: set tabstop=2 expandtab smartindent shiftwidth=2:


## Usage
[ $# -lt 2 -o "${1##*-}" == 'help' ] && cat << EOF && exit 1
USAGE: ${0##*/} <command> <file> [<file> ...]

SYNOPSIS:
  In-place link-safe/permission-safe wrapper to 'sed'.
EOF


## Arguments
SED_COMMAND="${1}" && shift


## Main
# ... create temporary file
SED_TMP="$(mktemp)" || exit 1
trap "rm -f '${SED_TMP}'" EXIT
# ... call 'sed' in a link-safe/permission-safe way
while [ -n "${1}" ]; do
  sed "${SED_COMMAND}" "${1}" > "${SED_TMP}" \
   && cat "${SED_TMP}" > "${1}"
  shift
done

