#!/usr/bin/env bash

# delays the audio in a file without transcoding

# Arguments:
# $1: Input File 1
# $2: Delay time in seconds

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") MOVIE_FILE.mov

  Explanation:
    This script will delay the audio of a file without retranscoding either the audio of video streams

  Options
   -h  display this help

  Input Arguments
   MOVIE_FILE.mov: Input file
   Delay time in seconds

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

if [ "$#" -ne 2 ]; then
    printf "ERROR: This script requires two arguments to run, the input file path and the delay time in seconds \n" >&2
    exit
fi

ffmpeg -i "${1}" -itsoffset ${2} -i "${1}" -map 0:v -map 1:a -c copy "${1%.*}_delayedAudio.mov"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -i '$1' -itsoffset $2 -i '$1' -map 0:v -map 1:a -c copy  '${1%.*}_delayedAudio.mov' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
