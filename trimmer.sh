#!/usr/bin/env bash
# version 2.0

# Trims files using ffmpeg while maintaining proper color info. Works with arbitrary file types (tested with v210, FFV1, and ProRes)

# Version History
# 1.0
#   Works as it's supposed to
# 2.0
#   Added features
#   - probes for color info using mediainfo and puts that back in properly
#   - can handle delayed start using "Sleep" command
#   - handles extension properly so can be used with arbitrary file types

# Arguments:
# $1: Input File 1
# $2: Start timestamp in format HH:MM:SS. Use 00:00:00 for no head trim
# $3: End timestamp in format HH:MM:SS. Use 00:00:00 for no tail trim
# $4: Optional: The number of hours to delay the script before it runs

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") MOVIE_FILE.mov START_TIMESTAMP END_TIMESTAMP

  Explanation:
    This script will trim an input file based off the supplied Start Timestamp and End Timestamp.
    It can be used to trim master files and mezzanien files. It will also work on access files, but may be less accurate.

  Options
   -h  display this help

  Input Arguments
   MOVIE_FILE.mov: Input file. This works on any video file.
   START_TIMESTAMP: Start timestamp in format HH:MM:SS. Use 00:00:00 for no head trim
   END_TIMESTAMP: End timestamp in format HH:MM:SS. Use 00:00:00 for no tail trim

  Dependencies: FFmpeg
EOF
}



if [[ ${1} == "-h" ]]; then
    _usage ; exit 0
fi

if [ "$#" -lt 3 ]; then
    printf "ERROR: This script requires at least three arguments: the input file path, the start timestamp, and the end timestamp \n" >&2
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

if [[ ! -z ${4} ]] ; then
    if [[ ${4} =~ ^[0-9]+$ ]] ; then
      sleep_time=$( expr 3600 '*' "$4")
      printf "Delaying script for ${4} hours (${sleep_time} seconds) \n" >&2
      sleep ${sleep_time}
    else
        printf "ERROR: fourth argument must be a valid number \n" >&2
        exit
    fi
else
    printf "No delay entered, starting script now \n" >&2
fi

filename=$(basename -- "${1}")
extension="${filename##*.}"
colour_primaries=$(mediainfo "--Output=Video;%colour_primaries%" ${1})
transfer_characteristics=$(mediainfo "--Output=Video;%transfer_characteristics%" ${1})
matrix_coefficients=$(mediainfo "--Output=Video;%matrix_coefficients%" ${1})

if [[ ${colour_primaries} = "BT.601 NTSC" ]] ; then
    color_primaries_flag="smpte170m"
    printf "Color Primaries: ${color_primaries_flag} \n" >&2
elif [[ ${colour_primaries} = "BT.709" ]] ; then
    color_primaries_flag="bt709"
    printf "Color Primaries: ${color_primaries_flag} \n" >&2
else
    printf "ERROR: Could not determine Colour Primaries of original file \n" >&2
    exit
fi

if [[ ${transfer_characteristics} = "BT.601" ]] ; then
    transfer_characteristics_flag="smpte170m"
    printf "Transfer Characteristics: ${transfer_characteristics_flag} \n" >&2
elif [[ ${transfer_characteristics} = "BT.709" ]] ; then
    transfer_characteristics_flag="bt709"
    printf "Transfer Characteristics: ${transfer_characteristics_flag} \n" >&2
else
    printf "ERROR: Could not determine Colour Primaries of original file \n" >&2
    exit
fi

if [[ ${matrix_coefficients} = "BT.601" ]] ; then
    matrix_coefficients_flag="smpte170m"
    printf "Matrix Coefficients: ${matrix_coefficients_flag} \n" >&2
elif [[ ${matrix_coefficients} = "BT.709" ]] ; then
    matrix_coefficients_flag="bt709"
    printf "Matrix Coefficients: ${matrix_coefficients_flag} \n" >&2
else
    printf "ERROR: Could not determine Colour Primaries of original file \n" >&2
    exit
fi

ffmpeg -ss ${2} -to ${3} -i "${1}" -movflags write_colr -color_range mpeg -color_primaries ${color_primaries_flag} -color_trc ${transfer_characteristics_flag} -colorspace ${matrix_coefficients_flag} -c copy "${1%.*}_trimmed.${extension}"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -ss ${2} -to ${3} -i '${1}' -movflags write_colr -color_range mpeg -color_primaries ${color_primaries_flag} -color_trc ${transfer_characteristics_flag} -colorspace ${matrix_coefficients_flag} -c copy '${1%.*}_trimmed.${extension}' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
