#!/usr/bin/env bash

# Deletes any hidden files in the specified folder

# Arguments:
# $1: Input File 1

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") MOVIE_FILE.mov

  Explanation:
    This script will delete any hidden files in the specified folder

  Options
   -h  display this help

  Input Arguments
   INPUT_DIR: Input Directory.

  Dependencies: FFmpeg
EOF
}

if [[ ${1} == "-h" ]]; then
    _usage ; exit 0
fi

if [ "$#" -ne 1 ]; then
    printf "ERROR: This script only takes one input arguement: the input video file \n" >&2
    exit
fi

if [[ -d ${1} ]]; then
    printf "Input Directory: ${1} \n" >&2
else
    printf "ERROR: First argument must be a valid directory \n" >&2
    exit
fi

sudo find ${1} -name ".*" -exec rm -vR {} \;
