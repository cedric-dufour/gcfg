#!/bin/bash
# INDENTING (emacs/vi): -*- mode:bash; tab-width:2; c-basic-offset:2; intent-tabs-mode:nil; -*- ex: set tabstop=2 expandtab smartindent shiftwidth=2:


## Check 'source' invocation
if [ "${BASH_LINENO[0]}" != '0' ]; then
  source gcfg.config
  return $?
fi


## Delegate execution to our python sibling
exec "$(dirname $0)/gcfg-py" "$@"
