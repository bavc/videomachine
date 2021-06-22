#!/bin/bash
# Short script to split videos by filesize using ffmpeg by LukeLR (taken from stack overflow: https://stackoverflow.com/questions/38259544/using-ffmpeg-to-split-video-files-by-size)
# The BAVC version has been updated to be frame accurate. It was tested on 2021-06-22 to be completely frame accurate using an FFV1/MKV file
# This script currently only works losslessly with MKV files, it needs some updates to properly handle color metadata for MOV

if [ $# -ne 2 ]; then
    echo 'Illegal number of parameters. Needs at least 3 parameters:'
    echo 'Usage:'
    echo './split-video.sh FILE SIZELIMIT "FFMPEG_ARGS'
    echo
    echo 'Parameters:'
    echo '    - FILE:        Name of the video file to split'
    echo '    - SIZELIMIT:   Maximum file size of each part (in bytes)'
    echo '    - FFMPEG_ARGS: Additional arguments to pass to each ffmpeg-call'
    echo '                   (video format and quality options etc.)'
    echo '                   Opttional. If nothing is entered script will streamcopy'
    exit 1
fi

FFMPEG_ARGS="$3"

if [ $# -ne 3 ]; then
    echo 'No FFmpeg transcode parameters entered. The script will streamcopy'
    FFMPEG_ARGS="-c copy"
fi

FILE="$1"
SIZELIMIT="$2"

# Duration of the source video
DURATION=$(ffprobe -i "$FILE" -show_entries format=duration -v quiet -of default=noprint_wrappers=1:nokey=1)

# Duration that has been encoded so far
CUR_DURATION=0

# Filename of the source video (without extension)
BASENAME="${FILE%.*}"

# Extension for the video parts
EXTENSION="${FILE##*.}"
#EXTENSION="mkv"

# Number of the current video part
i=1

# Filename of the next video part
NEXTFILENAME="$BASENAME-$i.$EXTENSION"

echo "Duration of source video: $DURATION"

# Until the duration of all partial videos has reached the duration of the source video
while [[ $CUR_DURATION != $DURATION ]]; do
    # Encode next part
    echo ffmpeg -i "$FILE" -ss "$CUR_DURATION" -fs "$SIZELIMIT" $FFMPEG_ARGS "$NEXTFILENAME"
    ffmpeg -ss "$CUR_DURATION" -i "$FILE" -fs "$SIZELIMIT" $FFMPEG_ARGS "$NEXTFILENAME"

    # Duration of the new part
    NEW_DURATION=$(ffprobe -i "$NEXTFILENAME" -show_entries format=duration -v quiet -of default=noprint_wrappers=1:nokey=1)

    # Total duration encoded so far
    CUR_DURATION=$( echo "$CUR_DURATION + $NEW_DURATION" | bc )
    #CUR_DURATION=$((CUR_DURATION + NEW_DURATION))

    i=$((i + 1))

    echo "Duration of $NEXTFILENAME: $NEW_DURATION"
    echo "Part No. $i starts at $CUR_DURATION"

    NEXTFILENAME="$BASENAME-$i.$EXTENSION"
done
