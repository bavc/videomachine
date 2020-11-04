#!/usr/bin/env bash

# Lighly transcodes adobe premiere SD/NTSC v210 files so that they conform to vrecord file specs

# Arguments:
# $1: Input File 1
# $2: Start timestamp in format HH:MM:SS. Use 00:00:00 for no head trim
# $3: End timestamp in format HH:MM:SS. Use 00:00:00 for no tail trim

if [ "$#" -ne 3 ]; then
    printf "ERROR: This script requires three arguments: the input file path, the start timestamp, and the end timestamp \n" >&2
    exit
fi

if [[ -f ${1} ]]; then
    printf "Input File: ${1} \n" >&2
else
    printf "ERROR: First argument must be a valid file \n" >&2
    exit
fi

if [[ ${2} =~ [0-9][0-9]:[0-5][0-9]:[0-5][0-9] ]] ; then
    printf "Start Time Stamp: ${2} \n" >&2
else
    printf "ERROR: Second argument must be a valid Timestamp (HH:MM:SS) \n" >&2
    exit
fi

if [[ ${3} =~ [0-9][0-9]:[0-5][0-9]:[0-5][0-9] ]] ; then
    printf "End Time Stamp: ${3} \n" >&2
else
    printf "ERROR: Third argument must be a valid Timestamp (HH:MM:SS) \n" >&2
    exit
fi


ffmpeg -ss ${2} -to ${3} -i "${1}" -movflags write_colr -c:v v210 -color_range mpeg -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -c copy "${1%.*}_trimmed.mov"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpge -ss ${2} -to ${3} -i '${1}' -movflags write_colr -c:v v210 -color_range mpeg -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -c copy '${1%.*}_trimmed.mov' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
