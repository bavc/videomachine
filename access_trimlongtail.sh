#!/usr/bin/env bash
# version 2.0

# Trims the last 30 seconds off access files, since we're finding files that have an extra 29 seconds here and there
# stream copies and makes file streamable

# Version History
# 1.0
#   Works as it's supposed to
# 2.0
#   User can enter an optional second arguemnt which is the trim time in seconds

# Arguments:
# $1: Input File 1
# $2: Trim time in seconds (OPTIONAL)

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") ACCESS_FILE.mp4 TAIL_TIME_TIME

  Explanation:
    This script will trim the last 29 seconds off an MP4 access file.
    It will streamcopy the file and make the files streamable with the faststarts movflag
    The user can enter a second optional

  Options
   -h  display this help

  Input Arguments
   ACCESS_FILE.mp4: Input file. This is made to work only with h.264 MP4 files
   TAIL_TIME_TIME: Number in seconds to cut off the tail. optional

  Dependencies: FFmpeg, mediainfo
EOF
}



if [[ ${1} == "-h" ]]; then
    _usage ; exit 0
fi

if [ "$#" -gt 2 ]; then
    printf "ERROR: This script can only accept a max of two arguments \n" >&2
    exit
fi

if [[ -f ${1} ]]; then
    printf "Input File: ${1} \n" >&2
else
    printf "ERROR: First argument must be a valid file \n" >&2
    exit
fi

if [[ ! -z ${2} ]] ; then
    if [[ ${2} =~ ^[0-9]+$ ]] ; then
      trimtime=24
    else
        printf "ERROR: Second argument must be a valid number \n" >&2
        exit
    fi
else
    printf "No custom trim time entered. Trimming by standard 29 seconds \n" >&2
    trimtime=29
fi

filename=$(basename -- "${1}")
extension="${filename##*.}"
durationMS=$(mediainfo "--Output=General;%Duration%" "${1}")
thousand=1000
durationSec=$((durationMS / thousand))
newDuration=$((durationSec - trimtime))

ffmpeg -i "${1}" -movflags faststart -c copy -t ${newDuration} "${1%.*}_trimmed.${extension}"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -i '${1}' -metadata:s language=eng -c copy -t ${newDuration} '${1%.*}_trimmed.${extension}' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
