#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Current Version: 0.7
#Version History
#   0.1 - 20170707
#       Creates a CSV file with all of the correct field names to match up with the SalesForce table. No bells or whistles. Input args suck
#   0.2 - 20170707
#       Added a progress bar because checksums take so long so it's nice to know
#   0.3 - 20171010
#       Removed pymediainfo from the script because it sucks and doesn't work
#   0.4 - 20171215
#       Changed the input args method, and allowed for a flag (-pr) that allows the script to parse prores files (otherwise it ignores them)
#   0.5 - 20180411
#       Fixed whitespace issues
#       Added 4 channel support
#       Added Disney Filename support
#   0.6 - 20180816
#       fixed parsing to match output of transcode script
#   0.7 - 20181108
#       Updated parsing to better match output of transcode description
#       Added -mkv flag for allowing MKV input
#   0.8 - 20191219
#       ignores files with "mezzanine" or "access" in the file name
#       can properly parse single files


# import modules used here -- sys is a very standard one
import os, sys
import datetime
#from pymediainfo import MediaInfo  # used for harvesting mediainfo. Really great lib!
import csv                          # used for creating the csv
import hashlib                      # used for creating the md5 checksum
import subprocess
import argparse

# Gather our code in a main() function
def main():
    media_info_list = []

    ####init the stuff from the cli########
    parser = argparse.ArgumentParser(description="Harvests Mediainfo of input file or files in input directory")
    parser.add_argument('-i','--input',dest='i', help="the path to the input directory or files")
    parser.add_argument('-o','--output',dest='o', help="the output file path (optional)")
    parser.add_argument('-pr','--ProRes',dest='pr',action ='store_true',default=False, help="Allows parsing of ProRes files when turned on")
    parser.add_argument('-mkv','--Matroska',dest='mkv',action ='store_true',default=False, help="Looks only for Matroska files")
    args = parser.parse_args()

    #handling the input args. This is kind of a mess in this version
    if args.i is None:
        print bcolors.FAIL + "Please enter an input path!" + bcolors.ENDC
        quit()
    elif args.o is None:
        print bcolors.OKBLUE +  "No output path defined, using default path" + bcolors.ENDC
        out_path = ""

    #initialize master file extension in processDict
    if args.mkv is True:
        masterExtension = ".mkv"
    else:
        masterExtension = ".mov"

    inPath = args.i
    inType = fileOrDir(inPath)
    # This part can tell if we're processing a file or directory. Handles it accordingly
    if inType == "F":
        print "Processing Input File: " + os.path.basename(inPath)
        media_info_list.append(createMediaInfoDict(inPath, inType, args.pr))
        if out_path == "":
            csv_path = inPath + ".mediainfo.csv"
        else:
            csv_path = out_path
        print "Output CSV file path is: " + csv_path
        createCSV(media_info_list, csv_path)	# this processes a list with a single dict in it (this is the case that only one file was given as the input)
    elif inType == "D":
        print "Processing Input Directory: " + os.path.dirname(inPath)
        if out_path == "":
            csv_path = inPath + "/mediainfo.csv"
        else:
            csv_path = args.o
        print "Output CSV file path is: " + csv_path

        # Need this part to get the number of Mov files.
        movCount = 0
        for root, directories, filenames in os.walk(inPath):
            for filename in filenames:
                tempFilePath = os.path.join(root,filename)
                if tempFilePath.endswith(masterExtension):
                    movCount = movCount + 1


        for root, directories, filenames in os.walk(inPath):
            fileIndex = 0
            for filename in filenames:
                #Process the file
                tempFilePath = os.path.join(root,filename)
                if tempFilePath.endswith(masterExtension) and not filename.startswith('.') and not filename.endswith('_mezzanine' + masterExtension) and not filename.endswith('_access' + masterExtension):

                    #Progress bar fun
                    numFiles = movCount
                    percentDone = float(float(fileIndex)/float(numFiles)*100.0)
                    sys.stdout.write('\r')
                    sys.stdout.write("[%-20s] %d%% %s \n" % ('='*int(percentDone/5.0), percentDone, filename))
                    sys.stdout.flush()
                    fileIndex = fileIndex + 1
                    mediainfo_dict = createMediaInfoDict(tempFilePath, inType, args.pr)
                    #will be "prores" if the file that was processed was prores. we can skip these.
                    if mediainfo_dict != "prores" or args.pr == True:
                        media_info_list.append(mediainfo_dict) # Turns the dicts into lists
                        createCSV(media_info_list,csv_path)	# this instances process the big list of dicts
        print "[====================] 100%% Done!\n"
        quit()


# Determine whether input is a file or a Directory, returns F or D respectively, quits otherwise
def fileOrDir(inPath):
    if os.path.isdir(inPath):
        return "D"
    elif os.path.isfile(inPath):
        return "F"
    else:
        print "I couldn't determine or find the input type!"
        quit()

#Process a single file
def createMediaInfoDict(filePath, inType, proresFlag):
    media_info_text = getMediaInfo(filePath)
    media_info_dict = parseMediaInfo(filePath, media_info_text, proresFlag)
    return media_info_dict

#gets the Mediainfo text
def getMediaInfo(filePath):
    cmd = [ '/usr/local/bin/mediainfo', '-f', '--Output=OLDXML', filePath ]
    media_info = subprocess.Popen( cmd, stdout=subprocess.PIPE ).communicate()[0]
    return media_info

#process mediainfo object into a dict
def parseMediaInfo(filePath, media_info_text, proresFlag):
    # The following line initializes the dict.
    file_dict = {"Name" : "", "instantiationIdentifierDigital__c" : "", "essenceTrackDuration__c" : "", "instantiationFileSize__c" : "", "instantiationDigital__c" : "", "essenceTrackEncodingVideo__c" : "", "essenceTrackBitDepthVideo__c" : "", "essenceTrackCompressionMode__c" : "", "essenceTrackScanType__c" : "", "essenceTrackFrameRate__c" : "", "essenceTrackFrameSize__c" : "", "essenceTrackAspectRatio__c" : "", "instantiationDataRateVideo__c" : "", "instantiationDigitalColorMatrix__c" : "", "instantiationDigitalColorSpace__c" : "", "instantiationDigitalChromaSubsampling__c" : "", "instantiationDataRateAudio__c" : "", "essenceTrackBitDepthAudio__c" : "", "essenceTrackSamplingRate__c" : "", "essenceTrackEncodingAudio__c" : "", "instantiationChannelConfigDigitalLayout__c" : "", "instantiationChannelConfigurationDigital__c" : "", "messageDigest" : "", "messageDigestAlgorithm" : ""}
    fileNameTemp = os.path.basename(filePath)
    fileNameExtension = fileNameTemp.split(".")[-1]
    file_dict["instantiationIdentifierDigital__c"] = fileNameTemp.split("." + fileNameExtension)[0]
    barcodeTemp = file_dict["instantiationIdentifierDigital__c"]
    #Catch for Disney Filesnames
    if "WDA_" in file_dict["instantiationIdentifierDigital__c"]:
        print bcolors.OKGREEN + "Renaming File for Disney Specs" + bcolors.ENDC
        file_dict["instantiationIdentifierDigital__c"] = "_".join(barcodeTemp.split("_")[1:])
    try:
        barcodeTemp = str(barcodeTemp).split("_")[0]
        file_dict["Name"] = barcodeTemp.split("BAVC")[1]
    except:
        print bcolors.FAIL + "Error parsing filename, No Barcode given for this file!\n\n" + bcolors.ENDC

    try:
        mi_General_Text = (media_info_text.split("<track type=\"General\">"))[1].split("</track>")[0]
        mi_Video_Text = (media_info_text.split("<track type=\"Video\">"))[1].split("</track>")[0]
        try:
            mi_Audio_Text = (media_info_text.split("<track type=\"Audio\">"))[1].split("</track>")[0]
        except:
            mi_Audio_Text = (media_info_text.split("<track type=\"Audio\" typeorder=\"1\">"))[1].split("</track>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse tracks for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC

    # General Stuff

    try:
        file_dict["essenceTrackDuration__c"] = (mi_General_Text.split("<Duration>"))[6].split("</Duration>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Duration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        fileFormatTemp = (mi_General_Text.split("<Format>"))[1].split("</Format>")[0]
        if fileFormatTemp == "MPEG-4":
            file_dict["instantiationDigital__c"] = "MOV"
        elif fileFormatTemp == "Matroska":
            file_dict["instantiationDigital__c"] = "MKV"
        elif fileFormatTemp == "Wave":
            file_dict["instantiationDigital__c"] = "WAV"
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not File Format for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationFileSize__c"] = (mi_General_Text.split("<File_size>"))[6].split("</File_size>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse File Size for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC

        # Video Stuff

    try:
        file_dict["essenceTrackEncodingVideo__c"] = (mi_Video_Text.split("<Codec_ID>"))[1].split("</Codec_ID>")[0]
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
        elif "FFV1" in file_dict["essenceTrackEncodingVideo__c"]:
            file_dict["essenceTrackEncodingVideo__c"] = "FFV1"
        elif "ProRes" in file_dict["essenceTrackEncodingVideo__c"] and proresFlag == False:
            print bcolors.FAIL + "Skipping ProRes File! (run with flag -pr to parse ProRes)" + bcolors.ENDC
            return "prores"
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        if "ProRes" in file_dict["essenceTrackEncodingVideo__c"]:
            file_dict["essenceTrackBitDepthVideo__c"] = "10 bits"
        else:
            file_dict["essenceTrackBitDepthVideo__c"] = (mi_Video_Text.split("<Bit_depth>"))[2].split("</Bit_depth>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["essenceTrackCompressionMode__c"] = (mi_Video_Text.split("<Compression_mode>"))[1].split("</Compression_mode>")[0]
    except:
        if "ProRes" in file_dict["essenceTrackEncodingVideo__c"]:
            file_dict["essenceTrackCompressionMode__c"] = "Lossy"
        else:
            print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Compression Mode for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["essenceTrackScanType__c"] = (mi_Video_Text.split("<Scan_type>"))[1].split("</Scan_type>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Scan Type for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["essenceTrackFrameRate__c"] = (mi_Video_Text.split("<Frame_rate>"))[1].split("</Frame_rate>")[0]
        if file_dict["essenceTrackFrameRate__c"] == "29.970":
            file_dict["essenceTrackFrameRate__c"] = "29.97"
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        frame_width = (mi_Video_Text.split("<Width>"))[1].split("</Width>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Width for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        frame_height = (mi_Video_Text.split("<Height>"))[1].split("</Height>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Frame Height for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    file_dict["essenceTrackFrameSize__c"] = frame_width + " x " + frame_height
    try:
        file_dict["essenceTrackAspectRatio__c"] = (mi_Video_Text.split("<Display_aspect_ratio>"))[2].split("</Display_aspect_ratio>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Display Aspect Rastio for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationDataRateVideo__c"] = (mi_Video_Text.split("<Bit_rate>"))[2].split("</Bit_rate>")[0]
        file_dict["instantiationDataRateVideo__c"] = file_dict["instantiationDataRateVideo__c"].replace("/","p")
    except:
        #this catches the overall bitrate of FFV1 files. It's a bit of a fudge, but gets the point across
        try:
            file_dict["instantiationDataRateVideo__c"] = (mi_General_Text.split("<Overall_bit_rate>"))[2].split("</Overall_bit_rate>")[0]
            file_dict["instantiationDataRateVideo__c"] = file_dict["instantiationDataRateVideo__c"].replace("/","p")
        except:
            print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Video Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationDigitalColorMatrix__c"] = (mi_Video_Text.split("<Color_primaries>"))[1].split("</Color_primaries>")[0]
    except:
        if "ProRes" in file_dict["essenceTrackEncodingVideo__c"]:
            try:
                file_dict["instantiationDigitalColorMatrix__c"] = (mi_Video_Text.split("<Matrix_coefficients>"))[1].split("</Matrix_coefficients>")[0]
            except:
                print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Matrix for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
        else:
            print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Matrix for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationDigitalColorSpace__c"] = (mi_Video_Text.split("<Color_space>"))[1].split("</Color_space>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Digital Color Space for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationDigitalChromaSubsampling__c"] = (mi_Video_Text.split("<Chroma_subsampling>"))[1].split("</Chroma_subsampling>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Chroma Subsampling for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC

        # Audio Stuff
    try:
        file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Resolution>"))[1].split("</Resolution>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        samplingRate = (mi_Audio_Text.split("<Sampling_rate>"))[1].split("</Sampling_rate>")[0]
        if samplingRate == "44100":
            samplingRate = "44.1"
        else:
            samplingRate = int(samplingRate)/1000
        file_dict["essenceTrackSamplingRate__c"] = str(samplingRate) + " kHz"
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Sampling Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Codec>"))[1].split("</Codec>")[0]
        if file_dict["essenceTrackEncodingAudio__c"] == "PCM":
            file_dict["essenceTrackEncodingAudio__c"] = "Linear PCM"
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Track Encoding for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        audioDataRate = (mi_Audio_Text.split("<Bit_rate>"))[1].split("</Bit_rate>")[0]
        audioDataRate = int(audioDataRate)/1000
        file_dict["instantiationDataRateAudio__c"] = str(audioDataRate) + " Kbps"
    except:
        try:
            if file_dict["essenceTrackSamplingRate__c"] == "48 kHz" and file_dict["essenceTrackBitDepthAudio__c"] == "24":
                file_dict["instantiationDataRateAudio__c"] = "2304 Kbps"
        except:
            print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Data Rate for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationChannelConfigurationDigital__c"] = (mi_Audio_Text.split("<Channel_s_>"))[2].split("</Channel_s_>")[0]
    except:
        print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Configuration for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC
    try:
        file_dict["instantiationChannelConfigDigitalLayout__c"] = (mi_Audio_Text.split("<ChannelLayout>"))[1].split("</ChannelLayout>")[0]
    except:
        if file_dict["instantiationChannelConfigurationDigital__c"] == "2 channels":
            file_dict["instantiationChannelConfigDigitalLayout__c"] = "L R"
        else:
            print bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Channel Layout for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC

        # Checksum
    try:
        file_dict["messageDigest"] = hashfile(filePath, "md5", blocksize=65536)
        file_dict["messageDigestAlgorithm"] = "md5"
    except:
        print bcolors.FAIL + "CHECKSUMS ERROR: Could not harvest checksum for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC

    return file_dict

# Create a CSV file from a dict
def createCSV(media_info_list, csv_path):
    keys = media_info_list[0].keys()
    with open(csv_path, 'wb') as output_file:
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
