#!/bin/bash

IFS=$'\n'                                   #this is necessary to deal with spaces in filepath. (found a better way to do this so I commented it out to be safe)\
source `dirname "$0"`/bash_logging.config    #this sets the path for the config file, which should be nested next to the script
logDir=`pwd` # The log will be created at the working directory
logName='log'  # The script will be named log.log
logName+='.log'
logPath="$logDir/$logName"
logCreate $logPath
logOpen

logNewLine "Starting Audio Normalization Script"

filename=$(basename -- "${1}")
extension="${filename##*.}"
logNewLine "Testing for fileype (audio or video)"
audioSampleRate=$(mediainfo -f "${1}" | grep -m1 'Sampling rate' | sed 's@.*:@@' )
logNewLine "The audio sampling rate is $audioSampleRate Hz"
audioBitRate=$(mediainfo "${1}"| awk '/Audio/{p=1}p' | grep 'Bit rate\|Kbps' | grep -v 'Overall\|mode' | sed 's@.*:@@' )
logNewLine "The audio bit rate is $audioBitRate"
if ffprobe "${1}" 2>&1 >/dev/null | grep -q Stream.*Video; then #greps the output of ffprobe for the word "video"
	format=Video && logNewLine "Video stream detected" #if grep returns "ture" then assigns the variable $format to "Video" and adds a line to the log
else
	logNewLine "No video stream detected" #if grep does not find the word "Video" in the ffprobe output it leaves $format unassigned and adds a line to the log
fi
logNewLine "Detecting max volume for ${filename}......."
maxVolume=$(ffmpeg -hide_banner -i "${1}" -af "volumedetect" -vn -sn -dn -f null - 2>&1 | grep 'max_volume' | awk '{print $(NF-1)}')
logCurrentLine "Complete! Max volume is: ${maxVolume} dB"
volumeBoost="${maxVolume:1}"
audioCodec=$(ffprobe "${1}" 2>&1 >/dev/null |grep Stream.*Audio | sed -e 's/.*Audio: //' -e 's/[, ].*//')

if [[ $format = "Video" ]] ; then #if the variable $format is "Video", then run ffmpeg command with -c:v copy, otherwise omit it
	logNewLine "Processing as Video"
	logLog ffmpeg -hide_banner -loglevel error -i "${1}" -af "volume="${volumeBoost}"dB" -c:v copy -c:a ${audioCodec} -ar ${audioSampleRate} -y "${1%.*}_normalized.${extension}"
else
	logNewLine "Processing as Audio, collecting metadata"
	audioBitRate=$(mediainfo "${1}" --Inform="General;%OverallBitRate%" )
	logNewLine "Bitrate is $audioBitRate"
	metadataAlbum=$(mediainfo "${1}" --Inform="General;%Album%" )
	logNewLine "The album name is $metadataAlbum"
	metadataTrack=$(mediainfo "${1}" --Inform="General;%Track%" )
	logNewLine "The album name is $metadataTrack"
	metadataArtist=$(mediainfo "${1}" --Inform="General;%Performer%" )
	logNewLine "The album name is $metadataArtist"
	metadataDate=$(mediainfo "${1}" --Inform="General;%Recorded_Date%" )
	logNewLine "The album name is $metadataDate"
	logLog ffmpeg -hide_banner -loglevel error -i "${1}" -af "volume="${volumeBoost}"dB" -c:a ${audioCodec} -ar ${audioSampleRate} -b ${audioBitRate} -y -write_xing 0 "${1%.*}_normalized.${extension}"
	logNewLine "File created. Now inserting metadata"
	logLog id3v2 -a "${metadataArtist}" -A  "${metadataAlbum}" -t "${metadataTrack}" -y "${metadataDate}" "${1%.*}_normalized.${extension}"
fi
logNewLine "Script Complete!\n\n"
