#!/usr/bin/env bash
# version 1.0

# Trims the last 30 seconds off access files, since we're finding files that have an extra 30 seconds here and there
# stream copies and makes file streamable

# Version History
# 1.0
#   Works as it's supposed to

# Arguments:
# $1: Input File 1

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") ACCESS_FILE.mp4

  Explanation:
    This script will trim the last 30 seconds off an MP4 access file.
    It will streamcopy the file and make the files streamable with the faststarts movflag

  Options
   -h  display this help

  Input Arguments
   ACCESS_FILE.mp4: Input file. This is made to work only with h.264 MP4 files

  Dependencies: FFmpeg, mediainfo
EOF
}



if [[ ${1} == "-h" ]]; then
    _usage ; exit 0
fi

if [ "$#" -ne 1 ]; then
    printf "ERROR: This script can ony accept one arguement, the input file \n" >&2
    exit
fi

if [[ -f ${1} ]]; then
    printf "Input File: ${1} \n" >&2
else
    printf "ERROR: First argument must be a valid file \n" >&2
    exit
fi

filename=$(basename -- "${1}")
extension="${filename##*.}"
durationMS=$(mediainfo "--Output=General;%Duration%" "${1}")
thousand=1000
twentynine=29
durationSec=$((durationMS / thousand))
newDuration=$((durationSec - twentynine))

ffmpeg -i "${1}" -movflags faststart -c copy -t ${newDuration} "${1%.*}_trimmed.${extension}"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -i '${1}' -metadata:s language=eng -c copy -t ${newDuration} '${1%.*}_trimmed.${extension}' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
