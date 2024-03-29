#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BAVC DVD Transcoder
# Version History
#   1.0.0 - 20220907
#       improved error handling, removed old python2 code, removed unused imports. Prime Time!
#   0.2.0 - 20220906
#       Combined Bash Cat and FFmpeg Cat into a single script.
#
#
#
#
# import modules used here -- sys is a very standard one
import os, sys
import subprocess                   # used for running ffmpeg, qcli, and rsync
import argparse                     # used for parsing input arguments
def main():


    media_info_list = []

    ####init the stuff from the cli########
    parser = argparse.ArgumentParser(description="dvd_transcoder version 0.1.0: Creates a concatenatd video file from an DVD-Video ISO")
    parser.add_argument('-i','--input',dest='i', help="the path to the input directory or files")
    parser.add_argument('-f','--format',dest='f', help="The output format (defaults to v210. Pick from v210, ProRes, H.264, FFv1)")
    parser.add_argument('-o','--output',dest='o', help="the output file path (optional, defaults to the same as the input)")
    parser.add_argument('-m','--mode',dest='m', help="Selects concatenation mode. 1 = Simple Bash Cat, 2 = FFmpeg Cat")
    parser.add_argument('-v','--verbose',dest='v',action='store_true',default=False,help='run in verbose mode (including ffmpeg info)')
    args = parser.parse_args()


    #handling the input args. This is kind of a mess in this version
    if args.i is None:
        print(bcolors.FAIL + "Please enter an input file!" + bcolors.ENDC)
        quit()
    if args.m is None:
        print(bcolors.OKGREEN + "Running in Simple Bash Cat mode" + bcolors.ENDC)
        mode = 1
    elif args.m == "1":
        print(bcolors.OKGREEN + "Running in Simple Bash Cat mode" + bcolors.ENDC)
        mode = 1
    elif args.m == "2":
        print(bcolors.OKGREEN + "Running in FFmpeg Cat mode" + bcolors.ENDC)
        mode = 2
    else:
        print(bcolors.FAIL + "Please select a valid mode (1 or 2)!" + bcolors.ENDC)
        quit()
    if args.f is None:
        output_format = "ProRes"
        transcode_string = " -c:v prores -profile:v 3 -c:a pcm_s24le -ar 48000 "
        output_ext = ".mov"
    elif "v210" in args.f:
        output_format = "v210"
        transcode_string = " -movflags write_colr+faststart -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -color_range mpeg -vf 'setfield=bff,setdar=4/3' -c:v v210 -c:a pcm_s24l -ar 48000 "
        output_ext = ".mov"
    elif "ProRes" in args.f:
        output_format = "ProRes"
        transcode_string = " -c:v prores -profile:v 3 -c:a pcm_s24le -ar 48000 "
        output_ext = ".mov"
    elif "H.264" in args.f:
        output_format = "H.264"
        transcode_string = " -c:v libx264 -pix_fmt yuv420p -movflags faststart -b:v 3500000 -b:a 160000 -ar 48000 -s 640x480 -vf yadif "
        output_ext = ".mp4"
    elif "FFv1" in args.f:
        output_format = "FFv1"
        transcode_string = " -map 0 -dn -c:v ffv1 -level 3 -coder 1 -context 1 -g 1 -slicecrc 1 -slices 24 -field_order bb -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -c:a copy "
        output_ext = ".mkv"
    else:
        output_format = "v210"
        transcode_string = " -movflags write_colr+faststart -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -color_range mpeg -vf 'setfield=bff,setdar=4/3' -c:v v210 -c:a pcm_s24l -ar 48000 "
        output_ext = ".mov"
    if args.o is None:
        output_path = os.path.dirname(args.i) + "/"

    if args.v:
        ffmpeg_command = "/usr/local/bin/ffmpeg "
        print("Running in Verbose Mode")
    else:
        ffmpeg_command = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic "

    #This parts mounts the iso
    print("Mounting ISO...")
    mount_point = mount_Image(args.i)
    print("Finished Mounting ISO!")

    ##this part processes the vobs
    try:
        ##move each vob over as a seperate file, adding each vob to a list to be concatenated
        if mode == 1:
            print("Moving VOBs to Local directory and concatonating...")
            if cat_move_VOBS_to_local(args.i, mount_point, ffmpeg_command):
                print("Finished moving VOBs to local directory and concatonating!")
                #transcode vobs into the target format
                print("Transcoding VOBS to %s..." % (output_format))
                cat_transcode_VOBS(args.i, transcode_string, output_ext, ffmpeg_command)
                print("Finished transcoding VOBS to %s!" % (output_format))
            else:
                print("No VOBs found. Quitting!")
        elif mode == 2:
            print("Transcoding VOBs to %s and moving to local directory..." % (output_format))
            if ffmpeg_move_VOBS_to_local(args.i, mount_point, ffmpeg_command, transcode_string, output_ext):
                print("Finished transcoding VOBs to %s and moving to local directory..." % (output_format))
                #concatenate vobs into a sungle file, format of the user's selection
                print("Concatonating %s files..." % (output_format))
                ffmpeg_concatenate_VOBS(args.i, transcode_string, output_ext, ffmpeg_command)
                print("Finished concatonating %s files!" % (output_format))
            else:
                print("No VOBs found. Quitting!")

        #CLEANUP
        print("Removing Temporary Files...")
        remove_temp_files(args.i)
        #Delete all fo the leftover files
        print("Finished Removing Temporary Files!")

        #This parts unmounts the iso
        print("Unmounting ISO")
        unmount_Image(mount_point)
        print("Finished Unmounting ISO!")

        return

    #If the user quits the script mid-processes the script cleans up after itself
    except KeyboardInterrupt:
        print(bcolors.FAIL + "User has quit the script" + bcolors.ENDC)
        try:
            unmount_Image(mount_point)
            remove_temp_files(args.i)
        except:
            pass
        quit()

# FUNCTION DEFINITIONS

def mount_Image(ISO_Path):
    mount_point_exists = True
    mount_increment = 0

    ##figure out what the mountpoint will be
    while mount_point_exists:
        mount_point = "ISO_Volume_" + str(mount_increment)
        mount_point_exists = os.path.isdir("/Volumes/" + mount_point)
        mount_increment = mount_increment + 1

    ##mount ISO
    try:
        mount_point = "/Volumes/" + mount_point
        mount_command = "hdiutil attach '" + ISO_Path + "' -mountpoint " + mount_point
        os.mkdir(mount_point)
        hdiutil_return = run_command(mount_command)
        if hdiutil_return == 1:
            print(bcolors.FAIL + "Mounting Failed. Quitting Script" + bcolors.ENDC)
            quit()
        return mount_point
    except PermissionError:
        print(bcolors.FAIL + "Mounting failed due to permission error. Try running script in sudo mode" + bcolors.ENDC)
        quit()


def unmount_Image(mount_point):
    unmount_command = "hdiutil detach '" + mount_point + "'"
    run_command(unmount_command)
    ##os.remove(mount_point)     #thought we needed this but i guess not...
    return True



def cat_move_VOBS_to_local(first_file_path, mount_point, ffmpeg_command):

    file_name_root = (os.path.splitext(os.path.basename(first_file_path))[0])
    input_vobList = []
    input_discList = []
    lastDiscNum = 1

    #find all of the vobs we want to concatenate
    for dirName, subdirList, fileList in os.walk(mount_point):
        for fname in fileList:
            if fname.split("_")[0] == "VTS" and fname.split(".")[-1] == "VOB":
                discNum = fname.split("_")[1]
                discNumInt = discNum.split("_")[0]
                vobNum = fname.split("_")[-1]
                vobNum = vobNum.split(".")[0]
                vobNumInt = int(vobNum)
                discNumInt = int(discNum)
                if discNumInt == lastDiscNum:
                    if vobNumInt > 0:
                        input_vobList.append(dirName + "/" + fname)
                if discNumInt > lastDiscNum:
                    input_vobList.sort()
                    input_discList.append(input_vobList)
                    input_vobList = []
                    if vobNumInt > 0:
                        input_vobList.append(dirName + "/" + fname)
                lastDiscNum = discNumInt


    ##Returns False if there are no VOBs found, otherwise it moves on
    if len(input_vobList) == 0:
        has_vobs = False
    else:
        has_vobs = True
        input_vobList.sort()
        input_discList.append(input_vobList)

      ##this portion performs the copy of the VOBs to the local storage. They are moved using the cat bash command

    try:
        delset_path = os.path.dirname(first_file_path)
        os.mkdir(first_file_path + ".VOBS/")
    except OSError:
        pass

#       Creating the cat command here

    cat_command = ""
    output_disc_count = 1
    out_vob_path = first_file_path + ".VOBS/" + file_name_root

    if len(input_discList) > 1:

        for disc in input_discList:
            cat_command += "/bin/cat "
            for vob in disc:
                cat_command += vob + " "
            cat_command += "> '" + out_vob_path + "_" + str(output_disc_count) + ".vob' && "
            output_disc_count += 1

        cat_command = cat_command.strip(" &&")

    else:
        cat_command += "cat "
        for disc in input_discList:
            for vob in disc:
                cat_command += vob + " "
            cat_command += "> '" + out_vob_path + ".vob'"

    run_command(cat_command)
    return has_vobs

def ffmpeg_move_VOBS_to_local(first_file_path, mount_point, ffmpeg_command, transcode_string, output_ext):

    input_vobList = []


    #find all of the vobs we want to concatenate
    for dirName, subdirList, fileList in os.walk(mount_point):
        for fname in fileList:
            if fname.split("_")[0] == "VTS" and fname.split(".")[-1] == "VOB":
                vobNum = fname.split("_")[-1]
                vobNum = vobNum.split(".")[0]
                vobNum = int(vobNum)
                if vobNum > 0:
                	input_vobList.append(dirName + "/" + fname)

    ##Returns False if there are no VOBs found, otherwise it moves on
    if len(input_vobList) == 0:
        has_vobs = False
    else:
        has_vobs = True
        input_vobList.sort()


      ##this portion performs the copy of the VOBs to the SAN. They are concatenated after the copy so the streams are in the right order

    try:
        delset_path = os.path.dirname(first_file_path)
        os.mkdir(first_file_path + ".VOBS/")
    except OSError:
        pass

    input_vobList_length = len(input_vobList)
    iterCount = 1
    for v in input_vobList:
        v_name = v.split("/")[-1]
        v_name = v_name.replace('.VOB',output_ext)
        out_vob_path = first_file_path + ".VOBS/" + v_name
        #ffmpeg_vob_copy_string = ffmpeg_command + " -i " + v + " -map 0:v:0 -map 0:a:0 -f vob -b:v 9M -b:a 192k -y '" + out_vob_path + "'"        #original without more recent additions
        #ffmpeg_vob_copy_string = ffmpeg_command + " -i " + v + " -map 0:v:0 -map 0:a:0 -video_track_timescale 90000 -f vob -b:v 9M -b:a 192k -y '" + out_vob_path + "'"    #version with just tbs fix
        #ffmpeg_vob_copy_string = ffmpeg_command + " -i " + v + " -map 0:v:0 -map 0:a:0 -af apad -c:v copy -c:a ac3 -ar 48000 -shortest -avoid_negative_ts make_zero -fflags +genpts -f vob -b:v 9M -b:a 192k -y '" + out_vob_path + "'"    #version with only audio pad
        ffmpeg_vob_copy_string = ffmpeg_command + " -i " + v + " -map 0:v:0 -map 0:a:0 -video_track_timescale 90000 -af apad -shortest -avoid_negative_ts make_zero -fflags +genpts -b:a 192k -y " + transcode_string + " '" + out_vob_path + "'"    #version with tbs fix and audio pad
        run_command(ffmpeg_vob_copy_string)


    ##see if mylist already exists, if so delete it.
    remove_cat_list(first_file_path)

    #writing list of vobs to concat
    f = open(first_file_path + ".mylist.txt", "w")
    for v in input_vobList:
        v_name = v.split("/")[-1]
        v_name = v_name.replace('.VOB',output_ext)
        out_vob_path = first_file_path + ".VOBS/" + v_name
        f.write("file '" + out_vob_path + "'")
        f.write("\n")
    f.close()

    return has_vobs

def cat_transcode_VOBS(first_file_path, transcode_string, output_ext, ffmpeg_command):
    extension = os.path.splitext(first_file_path)[1]
    vob_folder_path = first_file_path + ".VOBS/"
    vob_list = []
    for v in os.listdir(vob_folder_path):
        if not v.startswith('.'):
            if v.endswith('.vob'):
                vob_list.append(first_file_path + ".VOBS/" + v)

    if len(vob_list) == 1:
        output_path = first_file_path.replace(extension,output_ext)
        ffmpeg_vob_concat_string = ffmpeg_command + " -i '" + vob_list[0] + "' -dn -map 0:v:0 -map 0:a:0 " + transcode_string + " '" + output_path + "'"
        run_command(ffmpeg_vob_concat_string)
    else:
        inc = 1
        for vob_path in vob_list:
            output_path = first_file_path.replace(extension,"") + "_" + str(inc) + output_ext
            ffmpeg_vob_concat_string = ffmpeg_command + " -i '" + vob_path + "' " + transcode_string + " '" + output_path + "'"
            run_command(ffmpeg_vob_concat_string)
            inc += 1

def ffmpeg_concatenate_VOBS(first_file_path, transcode_string, output_ext, ffmpeg_command):
    catList = first_file_path + ".mylist.txt"
    extension = os.path.splitext(first_file_path)[1]
    output_path = first_file_path.replace(extension,output_ext)
    ffmpeg_vob_concat_string = ffmpeg_command + " -f concat -safe 0 -i '" + catList + "' -c copy '" + output_path + "'"
    run_command(ffmpeg_vob_concat_string)
    remove_cat_list(first_file_path)

def run_command(command):
    try:
        run = subprocess.call([command], shell=True)
        return run
    except Exception as e:
        print(e)
        return e

def remove_temp_files(input_dir):
    for the_file in os.listdir(input_dir + ".VOBS"):
        file_path = os.path.join(input_dir + ".VOBS", the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            #elif os.path.isdir(file_path): shutil.rmtree(file_path)
        except Exception as e:
            print(e)
    os.rmdir(input_dir + ".VOBS")
    remove_cat_list(input_dir)

def remove_cat_list(input_file):
    try:
        os.remove(input_file + ".mylist.txt")
        print("Removing Cat List")
    except OSError:
        pass

# Used to make colored text
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
