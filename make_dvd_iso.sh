#!/bin/bash
# make a specific dvd image file 

[ ! `which ffmpeg` ] && { echo Missing ffmpeg ; exit 1 ;};
[ ! `which ffprobe` ] && { echo Missing ffprobe ; exit 1 ;};
[ ! `which dvdauthor` ] && { echo Missing dvdauthor ; exit 1 ;};
[ ! `which mkisofs` ] && { echo Missing mkisofs ; exit 1 ;};

# we love functions
get_maxdvdbitrate(){
    DURATION=$(ffprobe "$1" -show_format 2> /dev/null | grep duration= | cut -d = -f 2)
    local DVDCAPACITY=33840000000 # in bits, minus 10%
    local CAPDVDBITRATE=6000000 # in bits/second
    MAXDVDBITRATE=$(echo "($DVDCAPACITY - ( $DURATION * 448000 )) / $DURATION" | bc)
    echo "Video data rate could be up to $MAXDVDBITRATE"
    if ! [[ "$MAXDVDBITRATE" =~ ^[0-9]+$ ]] ; then
        echo "Calculation of dvd bitrate failed. Evaluated to ${MAXDVDBITRATE}. Using 4000000 as bitrate instead."
        MAXDVDBITRATE=4000000
    elif [ "$MAXDVDBITRATE" -gt "$CAPDVDBITRATE" ] ; then
        MAXDVDBITRATE="$CAPDVDBITRATE"
    fi
    echo "Data rate for DVD is evaluated to $MAXDVDBITRATE"
}

#trap clean_up SIGHUP SIGINT SIGTERM

[ ! -s "$1" ] && { echo Please run the script with one or many arguments. Arguments should be video files to be transcoded. ; exit 1 ;};

while [ "$*" != "" ] ; do
OUTPUT="${1%.*}.iso"
name=$(basename ${1%.*})
[ -s $OUTPUT ] && { echo "$OUTPUT already existing, skipping transcode for $1" ; shift ; continue ;};
#ffmpeg -n -loop 1 -i "$SLATEFILE" -f lavfi -i aevalsrc=0::d=5:s=44100 -vf 'scale=720:480,setsar=8/9,fps=fps=ntsc,fade=in:0:30,fade=out:120:30' -t 5 -r:v ntsc -c:v ffv1 -pix_fmt yuv422p -s 720x480 -c:a pcm_s24le -r:a 48000 -ac 2 "$TMPSLATE"
get_maxdvdbitrate "$1"
dvdffmpegcommand="ffmpeg -y -i \"$1\" -r:v ntsc -c:v mpeg2video -c:a ac3 -f dvd -mbd rd -s 720x480 -pix_fmt yuv420p -g 18 -bf 2 -b:v $MAXDVDBITRATE -maxrate $MAXDVDBITRATE -vf crop=720:480:0:2 -bt 400k -top 0 -flags +ildct+ilme -minrate 0 -bufsize 3600k -packetsize 2048 -muxrate 10080000 -lmin 1 -lmax 200000 -b:a 448000 -ar 48000 \"${1%.*}.mpeg\""
eval "$dvdffmpegcommand"
export VIDEO_FORMAT=NTSC
dvdauthor --title -v ntsc -a ac3+en -c 0,5:00,10:00,15:00,20:00,25:00,30:00,35:00,40:00,45:00,50:00,55:00,1:00:00,1:05:00,1:10:00,1:15:00,1:20:00,1:25:00,1:30:00,1:35:00,1:40:00,1:45:00,1:50:00,1:55:00,2:00:00,2:05:00 -f "${1%.*}.mpeg" -o "${1%.*}_DVD"
dvdauthor_err="$?"
if [ "$dvdauthor_err" -gt "0" ] ; then
echo "ERROR dvdauthor reported error code $dvdauthor_err. Please review ${1%.*}_DVD" 1>&2
shift
continue
else
rm "${1%.*}.mpeg"
fi
dvdauthor -T -o "${1%.*}_DVD/"
echo "HEY ${1%.*:0:32} HEY"
mkisofs -f -dvd-video -udf -V "${name:0:32}" -v -v -o "$OUTPUT" "${1%.*}_DVD"
mkisofs_err="$?"
if [ "$mkisofs_err" -gt "0" ] ; then
echo "ERROR mkisofs reported error code $mkisofs_err. Please review ${OUTPUT}." 1>&2
shift
continue
else
rm -r "${1%.*}_DVD"
fi
shift
done
