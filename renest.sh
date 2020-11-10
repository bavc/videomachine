#!/usr/bin/env bash

# Lighly transcodes adobe premiere SD/NTSC v210 files so that they conform to vrecord file specs

# Arguments:
# $1: Input Folder

_usage(){
cat <<EOF
$(basename "${0}")
  Usage
   $(basename "${0}") INPUT_DIRECTORY

  Explanation:
    This script will renest a directory by BAVC Barcode

  Options
   -h  display this help

  Input Arguments
   INPUT_DIRECTORY Input Directory. All files within this directory with BAVC barcode numbers will be renamed

  Dependencies: bash
EOF
}

inputDir=$1
inputDir2="${inputDir}/*"

if [[ -d ${inputDir} ]]; then
  printf "Processing Directory: ${inputDir} \n" >&2

else
  printf "ERROR: The inputm ust be a valid directory \n" >&2
  exit
fi

for filename in ${inputDir2}; do
  #if [ -d "$file" ]; then
      echo basename "$filename"
  #fi
done
