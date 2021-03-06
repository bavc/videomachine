#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

#Current Version: 1.2.5
#Version History
#   0.1.0 - 20171113
#       Got it mostly working. current known issues:
#           Can't handle non BlackMagic mediainfo files (but will fail gracefully and still make checksums)
#           Doesn't output Rsync info as it's happening
#           No logging
#   0.2.0 - 20171114
#       Will ask user for valid input if the user input doesn't match expected
#       Puts out Rsync Output
#       Throws mediainfo parsing errors by the field, rather than by the file
#       No logging, no mediainfo fixing
#   0.3.0 - 20171205
#       Skips hidden files
#       Creates sidecar checksum files upon request
#   0.4.0 - 20171211
#       Changed --Output=XML to --Output=OLDXML to keep up to date with latest version of Mediainfo
#       Fixed bug where choosing No Checksum would crash it
#   0.5.0 - 20180111
#       Updated controlled vocabs for Digital Object Elements. removed .mov from filename
#   0.6.0 - 20180123
#       Changed input args to be the -i method
#       updated so 0 derivatives can be chosen so just the other methods are used.
#       Fixed all of the indent/spaces nightmares happening throughout the script
#   0.7.0 - 20180409
#       Fixed 4 channel issue. 4 channel MOV can now be properly processed
#   0.8.0 - 20180625
#       Added Autio support
#   0.9.0 - 20180629
#       Added bext and ID3 Support
#       Fixed presraid move so it happens after transcoding
#   0.9.1 - 20180703
#       Fixed bugs introduced in verion 0.9.1, added more comments
#   1.0.0 - 20181012
#       Added MKV support!
#   1.0.1 - 20181024
#       Patched to fix itunes duration error for mp3 files! added "-write_xing 0" to audio ffmpeg string
#   1.0.2 - Fixed typos in user interface (Derivatitves to Derivatives)
#   1.1.0 - 20190321
#       -Added support for DV
#   1.1.1 - 20190321
#       -Added support for NYU Deliverables
#   1.1.2 - 20190419
#       -Added support for NYU Metadata names (stripping barcodes in metadata)
#   1.1.3 - 20200401
#       -Fixed metadata harvesting for DV files
#   1.1.4 - 20200608
#       -Added support for DV wrapped in .mov
#       -no longer supports .dv files
#   1.2.0 - 202000608
#       -Moving towards python 3 entirely
#       -Adding simple_salesforce support for auto-updating salesfroce records with CSV metadata
#       -rearranged order of operations a bit so that syncing to presraid happens last
#       -added -nsf option to skip salesfroce sync (--NoSalesForce)
#       -scripts now checks file size of destination files agianst source files after rsync and updates salesforce field "Loaded to PresRADID" upon success!
#   1.2.1 - 20200612
#       -Added shebang #!/usr/local/bin/python3 so that we don't need to pt python3 before the script
#   1.2.2 - 20200625
#       -Changed mp4 string to include -crf 18 instead of -b:v 3500000 to get better quality out of nasty videos.
#       -inserted setdar=3/4 string into mp4 string to force apsect ratio
#   1.2.3 - 20201013
#       -Hardcoded mezzanine audio sample rate to 48kHz
#   1.2.4 - 2020410
#       -Fixed minor bug that kept coding history from working properly for second Minidisc deck
#   1.2.5 - 2020429
#       -Added Tascam DA-20 to arsenal of coding history decks
#
#   STILL NEEDS
#       Logging
#       User Verification
#
#   REQUIREMENTS
#       ffmpeg
#       QCLI
#       bwfmetaedit
#       id3v2
###REQUIRED LIBRARIES####
###simple_salesforce

# import modules used here -- sys is a very standard one
import os, sys
import datetime
import re                           # used for parsing checksum out of sidecar Files
import config                       # used for getting saleforce login and api key
import csv                          # used for creating the csv
import json                         # used for uploading csv info into salesfroce
import hashlib                      # used for creating the md5 checksum
import subprocess                   # used for running ffmpeg, qcli, and rsync
import shlex                        # used for properly splitting the ffmpeg/rsync strings
import argparse                     # used for parsing input arguments
from simple_salesforce import Salesforce

# Gather our code in a main() function
def main():


    media_info_list = []

    ####init the stuff from the cli########
    parser = argparse.ArgumentParser(description="Harvests Mediainfo of input file or files in input directory")
    parser.add_argument('-i','--input',dest='i', help="the path to the input directory or files")
    parser.add_argument('-o','--output',dest='o', help="the output file path (optional)")
    parser.add_argument('-c','--csvname',dest='c', help="the name of the csv file (optional)")
    parser.add_argument('-mkv','--Matroska',dest='mkv',action ='store_true',default=False, help="Allows input file type to be mkv rather than default mov")
    parser.add_argument('-dv','--DV',dest='dv',action ='store_true',default=False, help="Allows input file type to be dv rather than default mov. Processes as 720x480 rather than 720x486")
    parser.add_argument('-nsf', '--NoSalesForce',dest='nsf',action='store_true',default=False,help="Turns off 'No SalesForce' flag, which will avoid syncing the CSV to SF automatically. By defualt this script will sync CSV files to SalesForce")
    args = parser.parse_args()


    #handling the input args. This is kind of a mess in this version
    if args.i is None:
        print(bcolors.FAIL + "Please enter an input path!" + bcolors.ENDC)
        quit()
    if args.o is None:
        print(bcolors.OKBLUE +  "No output path defined, using default path" + bcolors.ENDC)
        out_path = ""
    else:
        out_path = args.o
        print(bcolors.OKBLUE +  "User output path defined as " + out_path + bcolors.ENDC)


    # This part can tell if we're processing a file or directory. Handles it accordingly
    inPath = args.i
    inType = fileOrDir(inPath)

    #processDict contains the info the script needs to run each subprocess, inlcuding the options that the user selected, and the paths to the files
    processDict = {}
    processDict = createProcessDict(processDict)

    #initialize master file extension in processDict
    if args.mkv is True:
        processDict['masterExtension'] = ".mkv"
    elif args.dv is True:
        processDict['masterExtension'] = ".mov"
    else:
        processDict['masterExtension'] = ".mov"

    # Initialize CSV output info
    if args.c is None:
        csv_name = "mediainfo.csv"
    elif ".csv" in args.c:
        csv_name = args.c
    else:
        csv_name = args.c + ".csv"

    # If we are processing a single file
    if inType == "F":
        print(bcolors.OKBLUE + "\nProcessing Input File: " + os.path.basename(inPath) + "\n\n" + bcolors.ENDC)

        #Set the paths of the CSV files
        if out_path == "":
            csv_path = os.path.dirname(inPath) + "/" + csv_name
        else:
            csv_path = out_path
        print(bcolors.OKBLUE + "Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC)

        #Process as Audio
        if inPath.endswith(".wav"):
            #Harvest mediainfo metadata, there is a subprocess in this script that inserts the BWAV metadata
            mediaInfoDict = createMediaInfoDict(inPath, inType, processDict)

            #Transcode the File
            processVideo(inPath, processDict)

            getSFAudioMD()

            #insert ID3 tags in MP3
            insertID3(mediaInfoDict, inPath.replace(".wav","_access.mp3"))

            #remove audio metadata from CSV Metadata Dict, necessary to keep the output CSV clean
            del mediaInfoDict['audioMetaDict']
            media_info_list.append(mediaInfoDict) # Turns the dicts into lists


        # Make the mediainfo CSV
        print(bcolors.OKGREEN + "DONE! Creating CSV File " + "\n" + bcolors.ENDC)
        createCSV(media_info_list, csv_path)	# this processes a list with a single dict in it (this is the case that only one file was given as the input)
        updateSalesForceCSV(csv_path, args.nsf)    # syncs CSV file to salesforce

        # Rsync the File
        inPathList = []
        inPathList.append(inPath)
        moveToBackup(inPathList, processDict, args.nsf)

        print(bcolors.OKBLUE + "DONE!" + "\n\n" + bcolors.ENDC)
        quit()


    # If we are processing an entire directory file
    elif inType == "D":
        print(bcolors.OKBLUE + "Processing Input Directory: " + os.path.dirname(inPath) + "\n\n" + bcolors.ENDC)

        #Set path of output csv file
        if out_path == "":
            csv_path = inPath + "/" + csv_name
        else:
            csv_path = out_path
        print(bcolors.OKBLUE + "Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC)


        # Need this part to get the number of Mov files.
        movCount = 0
        for root, directories, filenames in os.walk(inPath):
            for filename in filenames:
                tempFilePath = os.path.join(root,filename)
                if tempFilePath.endswith(processDict['masterExtension']) and not tempFilePath.endswith('_mezzanine.mov') and not filename.startswith('.'):
                    movCount = movCount + 1

        #If no MOV/MKV files are found, we're going to run as audio, so count the number of WAV files
        if movCount == 0:
            wavCount = 0
            for root, directories, filenames in os.walk(inPath):
                for filename in filenames:
                    tempFilePath = os.path.join(root,filename)
                    if tempFilePath.endswith('.wav') and not tempFilePath.endswith('_mezzanine.wav') and not filename.startswith('.'):
                        wavCount = wavCount + 1

        #now we walk through the directory to process each file
        for root, directories, filenames in os.walk(inPath):
            fileNum = 0
            inPathList = []
            for filename in filenames:
                #Process the file
                tempFilePath = os.path.join(root,filename)
                #Process as Audio
                if tempFilePath.endswith('.wav') and not tempFilePath.endswith('_mezzanine.wav') and not filename.startswith('.'):
                    #Harvest mediainfo metadata, there is a subprocess in this script that inserts the BWAV metadata
                    mediaInfoDict = createMediaInfoDict(tempFilePath, inType, processDict)

                    #Transcode the file
                    processVideo(tempFilePath, processDict)

                    #Insert ID3 metadata into MP3
                    insertID3(mediaInfoDict, tempFilePath.replace(".wav","_access.mp3"))

                    #remove audio metadata from CSV Metadata Dict
                    del mediaInfoDict['audioMetaDict']
                    media_info_list.append(mediaInfoDict) # Turns the dicts into lists

                    # Add to the list of paths to be rsynced
                    inPathList.append(tempFilePath)
                    fileNum += 1

                    print(bcolors.OKBLUE + "Done!\n" + bcolors.ENDC)

                    #create CSV
                    print(bcolors.OKGREEN + "DONE! Creating CSV File " + "\n\n" + bcolors.ENDC)
                    createCSV(media_info_list,csv_path)	# this instances process the big list of dicts

                #process as video
                elif tempFilePath.endswith(processDict['masterExtension']) and not tempFilePath.endswith('_mezzanine.mov') and not filename.startswith('.'):

                    #Harvest mediainfo metadata
                    mediaInfoDict = createMediaInfoDict(tempFilePath, inType, processDict)

                    #remove audio metadata from CSV Metadata Dict
                    del mediaInfoDict['audioMetaDict']
                    media_info_list.append(mediaInfoDict) # Turns the dicts into lists

                    # Quick little method to see if we're going to crop the file. This should eventually be its own function that does tons of pre-ffmpeg processing :->
                    frameSize = media_info_list[0]['essenceTrackFrameSize__c']
                    if "486" in frameSize:
                        processDict['crop'] = 1
                    else:
                        processDict['crop'] = 2

                    # FFmpeg and QCTools the file
                    if processDict['derivDetails'] == "NoDerivs":
                        print(bcolors.OKBLUE + "User Select Zero Derivatives, Skipping Transcode of " + filename + "\n\n" + bcolors.ENDC)
                        if processDict['createQCT'] == 1:
                            runCommand("qcli -i '" + tempFilePath + "'")
                    else:
                        processVideo(tempFilePath, processDict)

                    # Add to the list of paths to be rsynced
                    inPathList.append(tempFilePath)
                    fileNum += 1

                    #Progress bar fun
                    #numFiles = movCount
                    #percentDone = float(float(fileIndex)/float(numFiles)*100.0)
                    #sys.stdout.write('\r')
                    #sys.stdout.write("[%-20s] %d%% %s \n" % ('='*int(percentDone/5.0), percentDone, filename))
                    #sys.stdout.flush()

        print(bcolors.OKBLUE + "Done!\n" + bcolors.ENDC)
        print(bcolors.OKGREEN + "DONE! Creating CSV File " + "\n\n" + bcolors.ENDC)

        createCSV(media_info_list,csv_path)	# this instances process the big list of dicts
        updateSalesForceCSV(csv_path, args.nsf) # syncs CSV file to salesforce

        # Rsync the Files that were trasncoded
        moveToBackup(inPathList, processDict, args.nsf)


        quit()


# Determine whether input is a file or a Directory, returns F or D respectively, quits otherwise
def fileOrDir(inPath):
    if os.path.isdir(inPath):
        return "D"
    elif os.path.isfile(inPath):
        return "F"
    else:
        print("I couldn't determine or find the input type!")
        quit()

#Process a single file
def createMediaInfoDict(filePath, inType, processDict):
    media_info_text = getMediaInfo(filePath)
    media_info_dict = parseMediaInfo(filePath, media_info_text, processDict['hashType'], processDict['sidecar'], processDict['masterExtension'])
    return media_info_dict

#gets the Mediainfo text
def getMediaInfo(filePath):
    print(bcolors.OKGREEN + "Running Mediainfo and Checksums (If Selected)\n\n" + bcolors.ENDC)
    cmd = [ '/usr/local/bin/mediainfo', '-f', '--Output=OLDXML', filePath ]
    media_info = subprocess.Popen( cmd, stdout=subprocess.PIPE,encoding='utf8').communicate()[0]
    return media_info

#process mediainfo object into a dict
def parseMediaInfo(filePath, media_info_text, hashType, sidecar, masterExtension):
    # The following line initializes the dict.
    file_dict = {"Name" : "", "instantiationIdentifierDigital__c" : "", "essenceTrackDuration__c" : "", "instantiationFileSize__c" : "", "instantiationDigital__c" : "", "essenceTrackEncodingVideo__c" : "", "essenceTrackBitDepthVideo__c" : "", "essenceTrackCompressionMode__c" : "", "essenceTrackScanType__c" : "", "essenceTrackFrameRate__c" : "", "essenceTrackFrameSize__c" : "", "essenceTrackAspectRatio__c" : "", "instantiationDataRateVideo__c" : "", "instantiationDigitalColorMatrix__c" : "", "instantiationDigitalColorSpace__c" : "", "instantiationDigitalChromaSubsampling__c" : "", "instantiationDataRateAudio__c" : "", "essenceTrackBitDepthAudio__c" : "", "essenceTrackSamplingRate__c" : "", "essenceTrackEncodingAudio__c" : "", "instantiationChannelConfigDigitalLayout__c" : "", "instantiationChannelConfigurationDigital__c" : "", "messageDigest" : "", "messageDigestAlgorithm" : "", "audioMetaDict" : {}}
    file_dict["instantiationIdentifierDigital__c"] = os.path.basename(filePath).split(".")[0]
    barcodeTemp = file_dict["instantiationIdentifierDigital__c"]
    try:
        barcodeTemp = str(barcodeTemp).split("_")[0]
        file_dict["Name"] = barcodeTemp.split("BAVC")[1]
        if "WDA_" in file_dict["instantiationIdentifierDigital__c"]:
            print(bcolors.OKGREEN + "Renaming File for Disney Specs" + bcolors.ENDC)
            file_dict["instantiationIdentifierDigital__c"] = file_dict["instantiationIdentifierDigital__c"].replace("BAVC" + file_dict["Name"] + "_","")
        elif "nyuarchives" in file_dict["instantiationIdentifierDigital__c"]:
            print(bcolors.OKGREEN + "Renaming File for NYU Specs" + bcolors.ENDC)
            file_dict["instantiationIdentifierDigital__c"] = file_dict["instantiationIdentifierDigital__c"].replace("BAVC" + file_dict["Name"] + "_","")
    except:
        print(bcolors.FAIL + "Error parsing filename, No Barcode given for this file!\n\n")

    try:
        mi_General_Text = (media_info_text.split("<track type=\"General\">"))[1].split("</track>")[0]
        if masterExtension in filePath:
            mi_Video_Text = (media_info_text.split("<track type=\"Video\">"))[1].split("</track>")[0]
        try:
            mi_Audio_Text = (media_info_text.split("<track type=\"Audio\">"))[1].split("</track>")[0]
        except:
            mi_Audio_Text = (media_info_text.split("<track type=\"Audio\" typeorder=\"1\">"))[1].split("</track>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse tracks for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

        # General Stuff

    try:
        file_dict["essenceTrackDuration__c"] = (mi_General_Text.split("<Duration>"))[6].split("</Duration>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Duration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        fileFormatTemp = (mi_General_Text.split("<Format>"))[1].split("</Format>")[0]
        if fileFormatTemp == "MPEG-4":
            file_dict["instantiationDigital__c"] = "MOV"
        elif fileFormatTemp == "Matroska":
            file_dict["instantiationDigital__c"] = "MKV"
        elif fileFormatTemp == "DV":
            file_dict["instantiationDigital__c"] = "DV"
        elif fileFormatTemp == "Wave":
            file_dict["instantiationDigital__c"] = "WAV"
            file_dict = getAudioMetadata(file_dict, filePath)

            #This is where we insert the BWAV metadata. tag value pairs are added the medainfo dict (so we don't need to add more dicts) then rmeoved later on in the script
            insertBWAV(file_dict, filePath)
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not File Format for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["instantiationFileSize__c"] = (mi_General_Text.split("<File_size>"))[6].split("</File_size>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse File Size for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

        # Video Stuff
    if masterExtension in filePath:
        try:
            try:
                file_dict["essenceTrackEncodingVideo__c"] = (mi_Video_Text.split("<Codec_ID>"))[1].split("</Codec_ID>")[0]
            except:
                file_dict["essenceTrackEncodingVideo__c"] = (mi_Video_Text.split("<Codec>"))[1].split("</Codec>")[0]
            if file_dict["essenceTrackEncodingVideo__c"] == "v210":
                file_dict["essenceTrackEncodingVideo__c"] = "Uncompressed 10-bit (v210)"
            elif file_dict["essenceTrackEncodingVideo__c"] == "apch":
                file_dict["essenceTrackEncodingVideo__c"] = "Apple ProRes 422 HQ"
            elif file_dict["essenceTrackEncodingVideo__c"] == "apcn":
                file_dict["essenceTrackEncodingVideo__c"] = "Apple ProRes 422"
            elif file_dict["essenceTrackEncodingVideo__c"] == "apcs":
                file_dict["essenceTrackEncodingVideo__c"] = "Apple ProRes 422 LT"
            elif file_dict["essenceTrackEncodingVideo__c"] == "apco":
                file_dict["essenceTrackEncodingVideo__c"] = "Apple ProRes 422 Proxy"
            elif file_dict["essenceTrackEncodingVideo__c"] == "ap4h":
                file_dict["essenceTrackEncodingVideo__c"] = "Apple ProRes 4444"
            elif file_dict["essenceTrackEncodingVideo__c"] == "dv":
                file_dict["essenceTrackEncodingVideo__c"] = "DV"
            elif file_dict["essenceTrackEncodingVideo__c"] == "DV":
                file_dict["essenceTrackEncodingVideo__c"] = "DV"
            elif "FFV1" in file_dict["essenceTrackEncodingVideo__c"]:
                file_dict["essenceTrackEncodingVideo__c"] = "FFV1"

        except:
            try:
                file_dict["essenceTrackEncodingVideo__c"] = "DV"
            except:
                print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["essenceTrackBitDepthVideo__c"] = (mi_Video_Text.split("<Bit_depth>"))[2].split("</Bit_depth>")[0].split(" ")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["essenceTrackCompressionMode__c"] = (mi_Video_Text.split("<Compression_mode>"))[1].split("</Compression_mode>")[0]
        except:
            if "ProRes" in file_dict["essenceTrackEncodingVideo__c"]:
                file_dict["essenceTrackCompressionMode__c"] = "Lossy"
            else:
                print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Compression Mode for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["essenceTrackScanType__c"] = (mi_Video_Text.split("<Scan_type>"))[1].split("</Scan_type>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Scan Type for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["essenceTrackFrameRate__c"] = (mi_Video_Text.split("<Frame_rate>"))[1].split("</Frame_rate>")[0]
            if file_dict["essenceTrackFrameRate__c"] == "29.970":
                file_dict["essenceTrackFrameRate__c"] = "29.97"
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            frame_width = (mi_Video_Text.split("<Width>"))[1].split("</Width>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Width for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            frame_height = (mi_Video_Text.split("<Height>"))[1].split("</Height>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Height for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["essenceTrackFrameSize__c"] = frame_width + " x " + frame_height
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not create frame size using height and width of " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["essenceTrackAspectRatio__c"] = (mi_Video_Text.split("<Display_aspect_ratio>"))[2].split("</Display_aspect_ratio>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Display Aspect Ratio for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["instantiationDataRateVideo__c"] = (mi_Video_Text.split("<Bit_rate>"))[2].split("</Bit_rate>")[0]
            file_dict["instantiationDataRateVideo__c"] = file_dict["instantiationDataRateVideo__c"].replace("/","p")
        except:
            #this catches the overall bitrate of FFV1 files. It's a bit of a fudge, but gets the point across
            try:
                file_dict["instantiationDataRateVideo__c"] = (mi_General_Text.split("<Overall_bit_rate>"))[2].split("</Overall_bit_rate>")[0]
                file_dict["instantiationDataRateVideo__c"] = file_dict["instantiationDataRateVideo__c"].replace("/","p")
            except:
                print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            if file_dict["essenceTrackEncodingVideo__c"] == "DV":
                file_dict["instantiationDigitalColorMatrix__c"] = "n/a"
            elif "dvc" in file_dict["essenceTrackEncodingVideo__c"]:        #for some reason i had to do this instead of ==. couldn't figure out why, but go with what works I guess!
                file_dict["instantiationDigitalColorMatrix__c"] = "n/a"
            else:
                file_dict["instantiationDigitalColorMatrix__c"] = (mi_Video_Text.split("<Color_primaries>"))[1].split("</Color_primaries>")[0].split(" ")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Matrix for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            if file_dict["essenceTrackEncodingVideo__c"] == "DV" or file_dict["essenceTrackEncodingVideo__c"] == "dvc":
                file_dict["instantiationDigitalColorSpace__c"] = "n/a"
            else:
                file_dict["instantiationDigitalColorSpace__c"] = (mi_Video_Text.split("<Color_space>"))[1].split("</Color_space>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Space for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
        try:
            file_dict["instantiationDigitalChromaSubsampling__c"] = (mi_Video_Text.split("<Chroma_subsampling>"))[1].split("</Chroma_subsampling>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Chroma Subsampling for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

        # Audio Stuff
    try:
        file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Resolution>"))[1].split("</Resolution>")[0]
    except:
        try:
            file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Bit_depth>"))[1].split("</Bit_depth>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        samplingRate = (mi_Audio_Text.split("<Sampling_rate>"))[1].split("</Sampling_rate>")[0]
        if samplingRate == "44100":
            samplingRate = "44.1"
        else:
            samplingRate = int(samplingRate)/1000
        file_dict["essenceTrackSamplingRate__c"] = str(samplingRate) + " kHz"
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Sampling Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Codec>"))[1].split("</Codec>")[0]
        if file_dict["essenceTrackEncodingAudio__c"] == "PCM":
            file_dict["essenceTrackEncodingAudio__c"] = "Linear PCM"
    except:
        try:
            file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Format>"))[1].split("</Format>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        audioDataRate = (mi_Audio_Text.split("<Bit_rate>"))[1].split("</Bit_rate>")[0]
        audioDataRate = int(audioDataRate)/1000
        file_dict["instantiationDataRateAudio__c"] = str(audioDataRate) + " Kbps"
    except:
        try:
            if file_dict["essenceTrackSamplingRate__c"] == "48 kHz" and file_dict["essenceTrackBitDepthAudio__c"] == "24":
                file_dict["instantiationDataRateAudio__c"] = "2304 Kbps"
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    try:
        file_dict["instantiationChannelConfigurationDigital__c"] = (mi_Audio_Text.split("<Channel_s_>"))[2].split("</Channel_s_>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Configuration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["instantiationChannelConfigDigitalLayout__c"] = (mi_Audio_Text.split("<ChannelLayout>"))[1].split("</ChannelLayout>")[0]
    except:
        if file_dict["instantiationChannelConfigurationDigital__c"] == "2 channels":
            file_dict["instantiationChannelConfigDigitalLayout__c"] = "L R"
        else:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Layout for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    try:
        # Checksum
        if hashType == "none":
            file_dict["messageDigest"] = ""
            file_dict["messageDigestAlgorithm"] = ""
        else:
            file_dict["messageDigest"] = hashfile(filePath, hashType, blocksize=65536)
            file_dict["messageDigestAlgorithm"] = hashType
            if sidecar == 1:
                sidecarPath = filePath + "." + hashType
                f = open(sidecarPath,'w')
                f.write(file_dict["messageDigest"])
                f.close()
    except:
        print(bcolors.FAIL + "Error creating checksum for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    return file_dict

# Create a CSV file from a dict
def createCSV(media_info_list, csv_path):
    keys = media_info_list[0].keys()
    with open(csv_path, 'w') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(media_info_list)

# Generate checksum for the file
def hashfile(filePath, hashalg, blocksize=65536):
    afile = open(filePath,'rb')
    hasher = hashlib.new(hashalg) #grab the hashing algorithm decalred by user
    buf = afile.read(blocksize) # read the file into a buffer cause it's more efficient for big files
    while len(buf) > 0: # little loop to keep reading
        hasher.update(buf) # here's where the hash is actually generated
        buf = afile.read(blocksize) # keep reading
    return hasher.hexdigest()


# Runs the scripting. FFmpeg, QCLI
def processVideo(inPath, processDict):
    processVideoCMD = createString(inPath, processDict)
    runCommand(processVideoCMD)

# Creates the string based off the inputs
def createString(inPath, processDict):

    ffmpeg_string = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic -vsync 0 -i '" + inPath + "' "

    for derivCount in range(len(processDict['derivDetails'])):

        #skip the following if deriv type is MP3
        if processDict['derivDetails'][derivCount]['derivType'] != 5:
        # See if user opted to not crop MP4s

            if processDict['derivDetails'][derivCount]['frameSize'] == 2:
                frameSizeString = "720x486"
                processDict['crop'] = 2
            elif processDict['derivDetails'][derivCount]['frameSize'] == 1:
                frameSizeString = "640x480"
            elif processDict['derivDetails'][derivCount]['frameSize'] == 3:
                frameSizeString = "720x540"

            # Figure out the video filter string, then add to the basepath
            if processDict['crop'] == 1 and processDict['derivDetails'][derivCount]['doInterlace'] == 1: # if de-interlace and crop
                videoFilterString = " -vf crop=720:480:0:4,yadif "
            elif processDict['crop'] == 2 and processDict['derivDetails'][derivCount]['doInterlace'] == 1: # if de-interlace and no crop
                videoFilterString = " -vf yadif "
            elif processDict['crop'] == 1 and processDict['derivDetails'][derivCount]['doInterlace'] == 2: # if no de-interlace and crop
                videoFilterString = " -vf crop=720:480:0:4 "
            elif processDict['crop'] == 2 and processDict['derivDetails'][derivCount]['doInterlace'] == 2: # if no de-interlace and no crop
                videoFilterString = " "
            else:
                videoFilterString = " "
        else:
            videoFilterString = ""

        # Figure out the audio filter string, then add to the basepath
        if processDict['derivDetails'][derivCount]['audioMap'] == 1: # keep original
            audioFilterString = " "
        elif processDict['derivDetails'][derivCount]['audioMap'] == 2: # pan left center
            audioFilterString = " -af 'pan=stereo|c0=c0|c1=c0' "
        elif processDict['derivDetails'][derivCount]['audioMap'] == 3: # pan right center
            audioFilterString = " -af 'pan=stereo|c0=c1|c1=c1' "
        elif processDict['derivDetails'][derivCount]['audioMap'] == 4: # sum stereo to mono
            audioFilterString = " -af 'pan=stereo|c0=c0+c1|c1=c0+c1' "
        else:
            audioFilterString = " "

        # Figure out basestring
        if processDict['derivDetails'][derivCount]['mp3Kbps'] == 1:
            mp3kpbs = "320"
        elif processDict['derivDetails'][derivCount]['mp3Kbps'] == 2:
            mp3kpbs = "240"
        elif processDict['derivDetails'][derivCount]['mp3Kbps'] == 3:
            mp3kpbs = "160"
        elif processDict['derivDetails'][derivCount]['mp3Kbps'] == 4:
            mp3kpbs = "128"
        else:
            mp3kpbs = "0"

        if processDict['derivDetails'][derivCount]['derivType'] == 1: # Basestring for H264/MP4
            baseString = " -c:v libx264 -pix_fmt yuv420p -movflags faststart -crf 18 -b:a 160000 -ar 48000 -aspect 4:3 -s " + frameSizeString + " "
            videoFilterString = videoFilterString.replace("-vf ", "-vf setdar=4/3,")
            if "720x540" in baseString:
                processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(processDict['masterExtension'],"_s.mov")
            else:
                processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(processDict['masterExtension'],"_access.mp4")
        elif processDict['derivDetails'][derivCount]['derivType'] == 2: # Basestring for ProRes/MOV
            baseString = " -c:v prores -profile:v 3 -c:a pcm_s24le -ar 48000 "
            processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(processDict['masterExtension'],"_mezzanine.mov")
        elif processDict['derivDetails'][derivCount]['derivType'] == 3: # Basestring for FFv1/MKV
            baseString = " -map 0 -dn -c:v ffv1 -level 3 -coder 1 -context 1 -g 1 -slicecrc 1 -slices 24 -field_order bb -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m -c:a copy "
            videoFilterString = videoFilterString.replace("-vf ", "-vf setfield=bff,setdar=4/3,")
            processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(processDict['masterExtension'],".mkv")
        elif processDict['derivDetails'][derivCount]['derivType'] == 5: # Basestring for MP3
            baseString = " -c:a libmp3lame -b:a " + mp3kpbs + " -write_xing 0 -ac 2 "
            processDict['derivDetails'][derivCount]['outPath'] = inPath.replace(".wav","_access.mp3")

        ffmpeg_string = ffmpeg_string + baseString + videoFilterString + audioFilterString + " -y '" + processDict['derivDetails'][derivCount]['outPath'] + "' "

    if processDict['createQCT'] == 1:
        qctString = " && qcli -i '" + inPath + "'"
    else:
        qctString = ""

    cmd = ffmpeg_string + qctString
    return cmd


# Runs a command
def runCommand(cmd):
    print(bcolors.OKGREEN + "Running Command: " + cmd + "\n" + bcolors.ENDC)
    ffmpeg_out = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]
    return

# Runs the command that will move files to PresRAID via rsync
def moveToBackup(inPathList, processDict, NoSalesForce):
    if processDict['moveToPresRAID'] == 1:
        print(bcolors.OKBLUE + "Moving to PresRAID!\n" + bcolors.ENDC)
        inPathList_String = ""
        for i in range(len(inPathList)):
            inPathList_String = inPathList_String + "'" + inPathList[i] + "' "
            rsync_command = "rsync -av " + inPathList_String + " /Volumes/presraid/" + processDict['presRaidFolderPath']

        #runCommand(rsync_command)
        run_rsync(rsync_command)
        print(bcolors.OKBLUE + "Done Moving. Verifying Move Now\n"  + bcolors.ENDC)
        for i in range(len(inPathList)):                    # this cute little sections checks to see that the rysnc worked and the updates salesforce
            inputFileSize = os.path.getsize(inPathList[i])
            outputFileSize = os.path.getsize("/Volumes/presraid/" + processDict['presRaidFolderPath'] + "/" + os.path.basename(inPathList[i]))
            if inputFileSize == outputFileSize:
                barcode = getBarcode(inPathList[i])
                if barcode is False:
                    print(bcolors.FAIL + "\nERROR: Barcode is malformed. Cannot update SalesForce info for file: " + os.path.basename(inPathList[i]) + "\n" + bcolors.ENDC)
                else:
                    print(bcolors.OKGREEN +  "\nFile size of original and PresRAID version match for Barcode: " + barcode + "\n" + bcolors.ENDC)
                    updateSalesForceFileBackup(barcode, NoSalesForce)
            else:
                print(bcolors.FAIL + "\nERROR: File size of original and PresRAID version did not match. Please investigate\n" + bcolors.ENDC)
        return
    else:
        print(bcolors.OKBLUE + "Skipping Sync to PresRAID According to User-Selected Option\n" + bcolors.ENDC)
        return

# Allows us to see the progress of rsync (on a file-by-file basis)
def run_rsync(command):
    print(bcolors.OKGREEN + "Running Command: " + command + "\n\n" + bcolors.ENDC)
    p = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    p.communicate()
#    while True:
#        output = process.stdout.readline()
#        if output == '' and process.poll() is not None:
#            break
#        if output:
#            print(bcolors.OKGREEN + output.strip().decode("utf-8") + bcolors.ENDC)
#    rc = process.poll()
    return

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

# Get audio metadata from user
def getAudioMetadata(file_dict, filePath):

    audioMetaDict = {}
    filename = os.path.basename(filePath)
    audioMetaDict['title'] = input(bcolors.OKBLUE + "Please enter the title of " + filename + ", if any (No apostrophes or quotes please!): " + bcolors.ENDC)
    audioMetaDict['fullDate'] = input(bcolors.OKBLUE + "Please enter the Original Creation Date of this object, if any, in the format YYYY-MM-DD: " + bcolors.ENDC)
    audioMetaDict['creationDate'] = input(bcolors.OKBLUE + "Please enter the Digitization Date of this object YYYY-MM-DD: " + bcolors.ENDC)
    audioMetaDict['artistName'] = input(bcolors.OKBLUE + "Please enter the Arist/Producer of this object: " + bcolors.ENDC)
    audioMetaDict['yearDate'] = audioMetaDict['fullDate'][:4]
    userChoiceNum = input(bcolors.OKBLUE + "Please select the Tape Deck used:  \n[1] 101029-Otari-MX-5050\n[2] 101030-Otari-MX-55\n[3] 103527-Tascam-34\n[4] 101589-Tascam-122 MKII\n[5] 103540-Panasonic-SV-3700\n[6] 103591-Sony-MDS-E10\n[7] 103590-Sony-MDS-E10\n[8] 102573-TASCAM-DA-20\n\n " + bcolors.ENDC)
    while userChoiceNum not in ("1","2","3","4","5","6","7","8"):
        print(bcolors.FAIL + "\nIncorrect Input! Please enter a number\n" + bcolors.ENDC)
        userChoiceNum = input(bcolors.OKBLUE + "Please select the Tape Deck used: \n[1] 101029-Otari-MX-5050\n[2] 101030-Otari-MX-55\n[3] 103527-Tascam-34\n[4] 101589-Tascam-122 MKII\n[5] 103540-Panasonic-SV-3700\n[6] 103591-Sony-MDS-E10\n[7] 103590-Sony-MDS-E10\n[8] 102573-TASCAM-DA-20\n\n " + bcolors.ENDC)
    audioMetaDict['signalChain'] = int(userChoiceNum)

    file_dict['audioMetaDict'] = audioMetaDict
    return file_dict

# Inserting BWAV metadata in master audio files
def insertBWAV(file_dict, filePath):

    # Formats Descrition to "Title; Date"
    if file_dict['audioMetaDict']['fullDate'] == "" and file_dict['audioMetaDict']['title'] == "":
        bwavDescrition = ""
    elif file_dict['audioMetaDict']['fullDate'] == "":
        bwavDescrition = file_dict['audioMetaDict']['title']
    elif file_dict['audioMetaDict']['title'] == "":
        bwavDescrition = file_dict['audioMetaDict']['fullDate']
    else:
        bwavDescrition = file_dict['audioMetaDict']['title'] + "; " + file_dict['audioMetaDict']['fullDate']
    bwavOriginator = "BAVC"
    bwavOriginatorReference = file_dict["Name"]
    bwavOriginationDate = file_dict['audioMetaDict']['creationDate']
    bwavUMID = "0000000000000000000000000000000000000000000000000000000000000000"

    if file_dict['audioMetaDict']['signalChain'] == 1:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Otari_MX-5050_10452043f\\nA=PCM,F=96000,W=24,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 2:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Otari_MX-55_10482068n\\nA=PCM,F=96000,W=24,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 3:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Tascam_34_220069\\nA=PCM,F=96000,W=24,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 4:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Tascam_122MKII_1502630881\\nA=PCM,F=96000,W=24,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 5:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Panasonic_SV-3700_AA5IJ26175\\nA=S/PDIF,F=44100,W=16,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 6:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Sony_MDS-E10-302494\\nA=S/PDIF,F=44100,W=16,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 7:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=Sony_MDS-E10-305292\\nA=S/PDIF,F=44100,W=16,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    elif file_dict['audioMetaDict']['signalChain'] == 8:
        bwavCodingHistory = "A=ANALOGUE,M=stereo,T=TASCAM_DA-20-50088954\\nA=PCM,F=96000,W=24,M=stereo,T=MOTU_Ultralite-MK3_ES1F2FFFE00CAB1"
    else:
        bwavCodingHistory = "n/a"

#   Pads blank space at end of coding history if the length is odd to make sure there is an even number of characters.
    codeHistLen = len(bwavCodingHistory)
    if codeHistLen % 2 != 0:
        bwavCodingHistory = bwavCodingHistory + " "

    bwfString = "bwfmetaedit --accept-nopadding --specialchars --Description='" + bwavDescrition + "' --Originator='" + bwavOriginator + "' --OriginationDate='" + bwavOriginationDate + "' --OriginatorReference='" + bwavOriginatorReference + "' --UMID='" + bwavUMID + "' --History='" + bwavCodingHistory + "' '" + filePath + "'"
    runCommand(bwfString)

# Inserting ID3 metadata in master audio files
def insertID3(file_dict, filePath):

    id3Artist = file_dict['audioMetaDict']['artistName']
    id3Title = file_dict['audioMetaDict']['title']
    id3Year = file_dict['audioMetaDict']['yearDate']

    id3String = "id3v2 -a '" + id3Artist + "' -t '" + id3Title + "' -y '" + id3Year + "' '" + filePath + "'"
    runCommand(id3String)

# Used for seeing if a string represents an integer
def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

#prococesses sees if file was synced to backup directory and updates salesforce record if so
def updateSalesForceFileBackup(Barcode, NoSalesForce):
    if NoSalesForce == True:
        print(bcolors.OKBLUE +  "Skipping SalesForce Sync Due to Runtime Flag\n" + bcolors.ENDC)
    else:
        sf = initSF()
        insertLoadedData(sf,Barcode)

#prococesses CSV data and inserts it into salesforce
def updateSalesForceCSV(csv_path, NoSalesForce):
    if NoSalesForce == True:
        print(bcolors.OKBLUE +  "Skipping SalesForce Sync Due to Runtime Flag\n" + bcolors.ENDC)
    else:
        sf = initSF()
        dict_list = createDictList(csv_path)
        insertDictlist(dict_list,sf)

#connect to salesforce
def initSF():
    #init salesforce login#
    try:
        print(bcolors.OKBLUE +  "\nConnecting To Salesforce" + bcolors.ENDC)
        sf = Salesforce(username=config.username,password=config.password,security_token=config.security_token)
        return sf
    except:
        print(bcolors.FAIL + "\nSalesforce Connection Failed. Quitting Script" + bcolors.ENDC)
        exit()

#creates a list of dictionaries using the output CSV File
def createDictList(input_csv):
    dict_list = []
    with open(input_csv, mode='r') as infile:
        reader = csv.DictReader(infile)
        for line in reader:
            dict_list.append(line)
    return dict_list

#gets the barcode from a file
def getBarcode(filepath):
    filename = os.path.basename(filepath)
    barcode = filename[4:11] #get the barcode from the filename
    if not barcode.isdigit(): #this makes sure that the barcode is 7 numbers. if not it'll throw a failure
        return False
    else:
        return barcode

#creates the salesforce data object
def querySF(sf,barcode):
    result = sf.query("SELECT Id FROM Preservation_Object__c WHERE Name = '" + barcode + "'")
    return result

#gets info to embed in file from the Salesforce record (WORK IN PROGRESS)
def getSFAudioMD(sf,barcode):
    sfData = querySF(sf,Barcode)
    recordID = sfData['records'][0]['Id']
    sfRecord = sf.Contact.get(recordID)
    print(sfRecord)

#checks the Loaded to PresRAID box of the record if the file is succesfully loaded to the PresRAID
def insertLoadedData(sf,Barcode):
    sfData = querySF(sf,Barcode)
    recordID = sfData['records'][0]['Id']
    print(bcolors.OKBLUE +  "\nUpdating SalesForce record 'Loaded to PresRAID' field for record: " + Barcode + bcolors.ENDC)
    #try:
    sf.Preservation_Object__c.update(recordID,{'On_PresRaid__c': True})
    print(bcolors.OKGREEN +  "\nSuccess!\n" + bcolors.ENDC)
    #except:
    #    print(bcolors.FAIL +  "\nFailed!" + bcolors.ENDC)

#inserts data from list of dictionaies into salesforce
def insertDictlist(dict_list,sf):
    for d in dict_list:
        #create json out of ordered dict
        dString = json.dumps(d)
        #some string magic to fix improperly named fields
        temp = dString.replace("messageDigestAlgorithm", "messageDigestAlgorithm__c")
        dString = temp.replace("\"messageDigest\"", "\"messageDigest__c\"")
        #turn the string back into a JSON sturcture
        j = json.loads(dString)
        #get the record ID of the associated salesforce record
        if (len(d['Name']) is not 7) or (not d['Name'].isdigit()):     #quick check to make surebarcode is properly formaed. If not we'll stop trying to sync to salesfroce
            print(bcolors.FAIL +  "\nSkipping Barcode Because it is malformed: " + d['Name'] + "\n" + bcolors.ENDC)
        else:
            sfData = querySF(sf,d['Name'])
            recordID = sfData['records'][0]['Id']
            #insert the metadata!
            print(bcolors.OKBLUE +  "\nInserting Metadata for record: " + bcolors.ENDC + d['Name'])
            try:
                sf.Preservation_Object__c.update(recordID,j)
                print(bcolors.OKGREEN +  "\nSuccess!\n" + bcolors.ENDC)
            except:
                print(bcolors.FAIL +  "\nFailed!" + bcolors.ENDC)


# Creates the dict that holds all of the processing information
def createProcessDict(processDict):
    #Get number of derivatives with error catching
    userChoiceNum = input(bcolors.OKBLUE + "Please enter how many Derivatives will you be making: " + bcolors.ENDC)
    while not RepresentsInt(userChoiceNum):
        print(bcolors.FAIL + "\nIncorrect Input! Please enter a number\n" + bcolors.ENDC)
        userChoiceNum = input(bcolors.OKBLUE + "Please enter how many Derivatives will you be making: " + bcolors.ENDC)
    processDict['numDerivs'] = int(userChoiceNum)

    derivList = []

    # What to do if user selects 0 derivatives (so they just get mediainfo, qctools, presraid)
    if processDict['numDerivs'] == 0:
        processDict['derivDetails'] = "NoDerivs"

    for derivCount in range (1, (processDict.get('numDerivs') + 1)):
        derivDetails = {}
        #initialize variable
        derivDetails['mp3Kbps'] = 0
        #Get derivative types with error catching
        userChoiceType = input(bcolors.OKBLUE + "\nWhich Codec Do You Want Derivatives " + str(derivCount) + " To Be?\n[1] H.264/MP4\n[2] ProRes/MOV\n[3] FFv1/MKV\n[4] J2K/MXF\n[5] MP3\n\n" + bcolors.ENDC)
        while userChoiceType not in ("1","2","3","4", "5"):
            print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
            userChoiceType = input(bcolors.OKBLUE + "\n[1] H.264/MP4\n[2] ProRes/MOV\n[3] FFv1/MKV\n[4] J2K/MXF\n[5] MP3\n\n" + bcolors.ENDC)
        derivDetails['derivType'] = int(userChoiceType)
        #Get derivative details with error catching
        if derivDetails['derivType'] == 1 or derivDetails['derivType'] == 2 or derivDetails['derivType'] == 5:
            #Interlacing Options
            if derivDetails['derivType'] == 1 or derivDetails['derivType'] == 2:
                userChoiceInterlace = input(bcolors.OKGREEN + "\nDo you want to De-Interlace Derivative " + str(derivCount) + "?\n[1] De-interlace\n[2] Leave Interlaced\n\n" + bcolors.ENDC)
                while userChoiceInterlace not in ("1","2"):
                    print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
                    userChoiceInterlace = input(bcolors.OKGREEN + "\n[1] De-interlace\n[2] Leave Interlaced\n\n" + bcolors.ENDC)
                derivDetails['doInterlace'] = int(userChoiceInterlace)
            # MP3 Bitrate
            elif derivDetails['derivType'] == 5:
                userChoiceKbps= input(bcolors.OKGREEN + "\nHow many kpbs would you like to make your MP3 " + str(derivCount) + "?\n[1] 320\n[2] 240\n[3] 160\n[4] 128\n\n" + bcolors.ENDC)
                derivDetails['mp3Kbps'] = int(userChoiceKbps)
                while userChoiceKbps not in ("1","2","3","4"):
                    print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
                    userChoiceKbps = input(bcolors.OKGREEN + "\n[1] 320\n[2] 240\n[3] 160\n[4] 128\n\n" + bcolors.ENDC)
                    derivDetails['mp3Kbps'] = int(userChoiceKbps)
            #Audio Mapping Options
            userChoiceAudio = input(bcolors.OKGREEN + "\nHow would you like to map the audio for Derivative " + str(derivCount) + "?\n[1] Keep Original\n[2] Pan Left Center\n[3] Pan Right Center\n[4] Sum Stereo To Mono\n\n" + bcolors.ENDC)
            while userChoiceAudio not in ("1","2","3","4"):
                print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
                userChoiceAudio = input(bcolors.OKGREEN + "\n[1] Keep Original\n[2] Pan Left Center\n[3] Pan Right Center\n[4] Sum Stereo To Mono\n\n" + bcolors.ENDC)
            derivDetails['audioMap'] = int(userChoiceAudio)
        else:
            derivDetails['doInterlace'] = 2
            derivDetails['audioMap'] = 1
        if derivDetails['derivType'] == 1:
        #Frame Size Options for MP4
            userChoiceSize = input(bcolors.OKGREEN + "\nWhat frame size do you want the MP4 to be?\n[1] 640x480\n[2] 720x486\n[3] 720x540\n\n" + bcolors.ENDC)
            while userChoiceSize not in ("1","2","3"):
                print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
                userChoiceSize = input(bcolors.OKGREEN + "\n[1] 640x480\n[2] 720x486\n[3] 720x540\n\n" + bcolors.ENDC)
            derivDetails['frameSize'] = int(userChoiceSize)
        else:
            derivDetails['frameSize'] = 2
        derivList.append(derivDetails)
        processDict['derivDetails'] = derivList

    #PresRAID options
    userChoiceRAID = input(bcolors.OKBLUE + "\nDo you want to move the file to the PresRAID?\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
    while userChoiceRAID not in ("1","2"):
        print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
        userChoiceRAID = input(bcolors.OKBLUE + "\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
    processDict['moveToPresRAID'] = int(userChoiceRAID)
    if processDict['moveToPresRAID'] == 1:
        #Make sure PresRaid path exists
        processDict['presRaidFolderPath'] = str(input(bcolors.OKGREEN + "\nPlease Enter the Folder in the PresRAID you want to move these files to\n\n" + bcolors.ENDC))
        if os.path.isdir("/Volumes/presraid/InProgress/" + processDict['presRaidFolderPath']):   #add a little catch to automatically add "InProgress" if the folder in there exists already
            processDict['presRaidFolderPath'] = "InProgress/" + processDict['presRaidFolderPath']
        while not os.path.isdir("/Volumes/presraid/" + processDict['presRaidFolderPath']):
            print(bcolors.FAIL + "\nFolder path does not exist! Please try again!" + bcolors.ENDC)
            processDict['presRaidFolderPath'] = str(input(bcolors.OKGREEN + "\nPlease Enter the Folder in the PresRAID you want to move these files to\n\n" + bcolors.ENDC))
    else:
        processDict['presRaidFolderPath'] = ""

    #QCTools Options
    if derivDetails['mp3Kbps'] != 0:
        processDict['createQCT'] = 2
    else:
        userChoiceQC = input(bcolors.OKBLUE + "\nDo you want to create a QCTools Report for this file?\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
        while userChoiceQC not in ("1","2"):
            print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
            userChoiceQC = input(bcolors.OKBLUE + "\n[1] Yes \n[2] No\n\n" + bcolors.ENDC)
        processDict['createQCT'] = int(userChoiceQC)

    #Checksum Options
    userChoiceHash = input(bcolors.OKBLUE + "\nDo you want to create a Checksum for this file?\n[1] Yes \n[2] Yes + Sidecar \n[3] No \n\n" + bcolors.ENDC)
    while userChoiceHash not in ("1","2", "3"):
        print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
        userChoiceHash = input(bcolors.OKBLUE + "\n[1] Yes \n[2] Yes + Sidecar\n[3] No\n\n" + bcolors.ENDC)
    createHash = int(userChoiceHash)
    if createHash == 1 or createHash == 2:
        processDict['sidecar'] = createHash - 1 #Create sidecar will be 0 if no sidecar, 1 if yes sidecar
        userChoiceHashType = input(bcolors.OKGREEN + "\nWhich type of hash would you like to create?\n[1] MD5 \n[2] SHA1 \n[3] SHA256\n\n" + bcolors.ENDC)
        while userChoiceHashType not in ("1","2","3"):
            print(bcolors.FAIL + "\nIncorrect Input! Please Select from one of the following options!" + bcolors.ENDC)
            userChoiceHashType = (bcolors.OKGREEN + "[1] MD5 \n[2] SHA1 \n[3] SHA256\n\n" + bcolors.ENDC)
        hashNum = int(userChoiceHashType)
        if hashNum == 1:
            processDict['hashType'] = "md5"
        elif hashNum == 2:
            processDict['hashType'] = "sha1"
        elif hashNum == 3:
            processDict['hashType'] = "sha256"
        else:
            processDict['hashType'] = "none"
    else:
        processDict['hashType'] = "none"
        processDict['sidecar'] = ""
    return processDict


# Standard boilerplate to call the main() function to begin
# the program.
if __name__ == '__main__':
    main()
