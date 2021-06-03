#!/usr/bin/env bash

# Adds english language tag back into video files that it got removed from

# Arguments:
# $1: Input File 1

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") MOVIE_FILE.mov

  Explanation:
    This script will add the english laguage tag back to every stream of the input file

  Options
   -h  display this help

  Input Arguments
   MOVIE_FILE.mov: Input file

  Dependencies: FFmpeg
EOF
}

if [[ ${1} == "-h" ]]; then
    _usage ; exit 0
fi

if [[ -f ${1} ]]; then
    printf "Input File: ${1} \n" >&2
else
    printf "ERROR: Input argument must be a valid file \n" >&2
    exit
fi

if [ "$#" -ne 1 ]; then
    printf "ERROR: This script only accepts one argument, the input file path \n" >&2
    exit
fi

ffmpeg -i "${1}" -metadata:s language=eng -c copy "${1%.*}_addEnglishTag.mov"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -i '$1' -metadata:s language=eng -c copy '${1%.*}_addEnglishTag.mov' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
