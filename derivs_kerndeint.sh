#!/usr/bin/env bash

# Lighly transcodes adobe premiere SD/NTSC v210 files so that they conform to vrecord file specs

# Arguments:
# $1: Input File 1
# $2: Start timestamp in format HH:MM:SS. Use 00:00:00 for no head trim
# $3: End timestamp in format HH:MM:SS. Use 00:00:00 for no tail trim

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") MOVIE_FILE.mov

  Explanation:
    This script will create a BAVC Standard Access File and Deinterlad Mezzanine File using the kerndeint filter to deinterliace

  Options
   -h  display this help

  Input Arguments
   MOVIE_FILE.mov: Input file. This works on any interlaced NTSC Preservation file.

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

if [[ -f ${1} ]]; then
    printf "Input File: ${1} \n" >&2
else
    printf "ERROR: First argument must be a valid file \n" >&2
    exit
fi

ffmpeg -vsync 0 -i "${1}" -c:v libx264 -pix_fmt yuv420p -movflags faststart -crf 18 -b:a 160000 -ar 48000 -aspect 4:3 -s 640x480 -vf setdar=4/3,crop=720:480:0:4,kerndeint "${1%.*}_access_kerndeint.mp4" -c:v prores -profile:v 3 -vf kerndeint -c:a pcm_s24le "${1%.*}_mezzanine_kerndeint.mov"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -vsync 0 -i '${1}' -c:v libx264 -pix_fmt yuv420p -movflags faststart -crf 18 -b:a 160000 -ar 48000 -aspect 4:3 -s 640x480 -vf setdar=4/3,crop=720:480:0:4,kerndeint '${1%.*}_access_kerndeint.mp4' -c:v prores -profile:v 3 -vf kerndeint -c:a pcm_s24le '${1%.*}_mezzanine_kerndeint.mov' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n " >&2
