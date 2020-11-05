#!/usr/bin/env bash

# Lighly transcodes adobe premiere SD/NTSC v210 files so that they conform to vrecord file specs

# Arguments:
# $1: Input File 1

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") MOVIE_FILE.mov

  Explanation:
    This script will reformat any files that come out of Adobe Premiere to match the vrecord format.
    You should use this script on ANY file that is exported from Premiere

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

ffmpeg -i "${1}" -dn -map_metadata '-1' -movflags write_colr -c:v v210 -color_range mpeg -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -vf 'setfield=bff,setsar=40/27,setdar=4/3' -c:a copy "${1%.*}_adobeFix.mov"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -i '$1' -dn -map_metadata '-1' -movflags write_colr -c:v v210 -color_range mpeg -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -vf 'setfield=bff,setsar=40/27,setdar=4/3' -c:a copy '${1%.*}_adobeFix.mov' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
