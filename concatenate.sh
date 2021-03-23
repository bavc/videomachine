#!/usr/bin/env bash

# Repeats/Loops the input file as many times as requested

# Parameters:
# $1: Input File
# $2: Number of repeats (default is 2)

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") [OPTIONS] INPUT_FILE_1 REPEATS
  Options
   -h  display this help
   -p  previews in FFplay
   -s  saves to file with FFmpeg

  Parameters:
  INPUT_FILE_1 First file
  INPUT_FILE_2 Second file

  Outcome
   Repeats/Loops the input file as many times as requested
   dependencies: ffmpeg 4.3 or later
EOF
}

filename1=$(basename -- "$1")
filename2=$(basename -- "$2")
extension1="${filename1##*.}"
extension2="${filename2##*.}"
firstchar1=${1:0:1}
firstchar2=${2:0:1}
pwd=$(pwd)


if [[ $firstchar1 == "." ]]; then
   filepath1="$pwd${1:1}"
else
   filepath1=$1
fi

if [[ $firstchar2 == "." ]]; then
   filepath2="$pwd${1:1}"
else
   filepath2=$2
fi


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

echo file \'$filepath1\' > /tmp/catlist.txt
echo file \'$filepath2\' >> /tmp/catlist.txt

ffmpeg -hide_banner -f concat -safe 0 -i /tmp/catlist.txt -movflags write_colr -color_range mpeg -color_primaries ${color_primaries_flag} -color_trc ${transfer_characteristics_flag} -colorspace ${matrix_coefficients_flag} -c copy  "${1%.*}_concatenated.${extension1}"
printf "\n\n*******START FFMPEG COMMANDS*******\n" >&2
printf "ffmpeg -hide_banner -f concat -safe 0 -i /tmp/catlist.txt -c copy '${1%.*}_concatenated.${extension1}' \n" >&2
printf "********END FFMPEG COMMANDS********\n\n" >&2
