#!/usr/bin/env bash

mediainfo "$1" | sed 's/[[:space:]]*:/:/'
