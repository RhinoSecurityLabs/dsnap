#!/usr/bin/env bash

strings snap-*.img \
  | tee >(grep -A1 -E "aws_access_key_id = ((?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16})" 1>&2) \
  >/dev/null
