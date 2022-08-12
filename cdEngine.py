#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

#Current Version: 0.1.0
#Version History
#   0.1.0 - 20220812
#       getting this script up and running


#REQUIREMENTS
#       ffmpeg
#       bwfmetaedit
#       sox
#       mediainfo
#       cuetools (installs cuebreakpoints)
###REQUIRED LIBRARIES####
#       simple_salesforce

# import modules used here -- sys is a very standard one
import os, sys
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
    parser.add_argument('-s','--Split_Tracks',dest='s',action ='store_true',default=False, help="Splits the file into tracks according to CUE file")
    parser.add_argument('-m','--Make-Full-MP3',dest='m',action ='store_true',default=False, help="Makes an unsplit MP3. This flag only works if the -s flag is also run")
    args = parser.parse_args()

    #handling the input args. This is kind of a mess in this version
    if args.i is None:
        print(bcolors.FAIL + "Please enter an input path!" + bcolors.ENDC)
        quit()
    if args.o is None:
        print(bcolors.OKBLUE +  "\nNo output path defined, using default path\n" + bcolors.ENDC)
        out_path = ""
    else:
        out_path = args.o
        print(bcolors.OKBLUE +  "User output path defined as " + out_path + bcolors.ENDC)


    # This part can tell if we're processing a file or directory. Handles it accordingly
    inPath = args.i
    inType = fileOrDir(inPath)

    #initialize output csv path
    if inType == "F":
        if out_path == "":
            csv_path = os.path.dirname(inPath) + "/" + os.path.basename(inPath).split(".")[0] + "_mediainfo.csv"
        else:
            csv_path = out_path
        print(bcolors.OKBLUE + "Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC)
    elif inType == "D":
        if out_path == "":
            csv_path = inPath + "mediainfo.csv"
        else:
            csv_path = out_path
        print(bcolors.OKBLUE + "Output CSV file path is: " + csv_path + "\n\n" + bcolors.ENDC)


    # Initialize CSV output info
    if args.c is None:
        csv_name = "mediainfo.csv"
    elif ".csv" in args.c:
        csv_name = args.c
    else:
        csv_name = args.c + ".csv"

    fileList = getFileList(inType,args)

    if fileList == []:
        print(bcolors.FAIL + "\nNo properly formatted files found. Please make sure yor input is correct and try again." + bcolors.ENDC)

    media_info_list = []    #initialzie mediainfo list

    for f in fileList:
        print(bcolors.OKBLUE +  "Processing File: " + os.path.basename(f) + "\n" + bcolors.ENDC)

        #intialize file dictionary
        file_dict = {"Name" : "", "instantiationIdentifierDigital__c" : "", "essenceTrackDuration__c" : "", "instantiationFileSize__c" : "", "instantiationDigital__c" : "", "essenceTrackEncodingVideo__c" : "", "essenceTrackBitDepthVideo__c" : "", "essenceTrackCompressionMode__c" : "", "essenceTrackScanType__c" : "", "essenceTrackFrameRate__c" : "", "essenceTrackFrameSize__c" : "", "essenceTrackAspectRatio__c" : "", "instantiationDataRateVideo__c" : "", "instantiationDigitalColorMatrix__c" : "", "instantiationDigitalColorSpace__c" : "", "instantiationDigitalChromaSubsampling__c" : "", "instantiationDataRateAudio__c" : "", "essenceTrackBitDepthAudio__c" : "", "essenceTrackSamplingRate__c" : "", "essenceTrackEncodingAudio__c" : "", "instantiationChannelConfigDigitalLayout__c" : "", "instantiationChannelConfigurationDigital__c" : "", "messageDigest" : "", "messageDigestAlgorithm" : "", "audioMetaDict" : {}}

        #harvest .wav file metadata
        file_dict = createMediaInfoDict(f, file_dict)

        #get metadata from sf
        file_dict = getAudioMetadata(file_dict, f, file_dict["Name"])

        #create bwf file with metadata
        insertBWAV(file_dict, f)

        #create spectrogram
        createSpectro(f)

        #create derivatives with metadata (split if requested)
        createMP3(file_dict, f, args)

        #clean up file_dict and add it to the list of metadata to be uploaded to SF
        del file_dict['audioMetaDict']        #need to delete the extra embedded metadata or the CSV can't be created properly
        media_info_list.append(file_dict)

    #insert mediainfo into salesforce
    createCSV(media_info_list,csv_path)	# this instances process the big list of dicts
    updateSalesForceCSV(csv_path) # syncs CSV file to salesforce

    print(bcolors.OKBLUE +  "Script Complete!\n" + bcolors.ENDC)
    quit()

#process mediainfo object into a dict
def parseMediaInfo(filePath, media_info_text, hashType, file_dict):
    # The following line initializes the dict.
    file_dict["instantiationIdentifierDigital__c"] = os.path.basename(filePath).split(".")[0]
    barcodeTemp = file_dict["instantiationIdentifierDigital__c"]
    try:
        barcodeTemp = str(barcodeTemp).split("_")[0]
        file_dict["Name"] = barcodeTemp.split("BAVC")[1]
        if "yrlsc" in filePath:
            print(bcolors.OKGREEN + "Renaming File for UCLA Spec (removing BAVC barcode)\n" + bcolors.ENDC)
            file_dict["instantiationIdentifierDigital__c"] = file_dict["instantiationIdentifierDigital__c"].replace("BAVC" + file_dict["Name"] + "_","")
        elif "nyuarchives" in file_dict["instantiationIdentifierDigital__c"]:
            print(bcolors.OKGREEN + "Renaming File for NYU Spec (removing BAVC barcode)\n" + bcolors.ENDC)
            file_dict["instantiationIdentifierDigital__c"] = file_dict["instantiationIdentifierDigital__c"].replace("BAVC" + file_dict["Name"] + "_","")
        elif "_prsv" in file_dict["instantiationIdentifierDigital__c"]:
            print(bcolors.OKGREEN + "Renaming File for CA-R Spec (removing BAVC barcode)\n" + bcolors.ENDC)
            file_dict["instantiationIdentifierDigital__c"] = file_dict["instantiationIdentifierDigital__c"].replace("BAVC" + file_dict["Name"] + "_","")
    except:
        print(bcolors.FAIL + "Error parsing filename, No Barcode given for this file!\n\n")

    try:
        mi_General_Text = (media_info_text.split("<track type=\"General\">"))[1].split("</track>")[0]
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
        file_dict["instantiationFileSize__c"] = (mi_General_Text.split("<File_size>"))[6].split("</File_size>")[0]
    except:
        print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse File Size for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

        # Audio Stuff
    try:
        file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Resolution>"))[1].split("</Resolution>")[0]
    except:
        try:
            file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Bit_depth>"))[1].split("</Bit_depth>")[0]
        except:
            print(bcolors.FAIL + "MEDIAINFO ERROR: Could not parse Audio Bit Depth for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)
    try:
        file_dict["essenceTrackSamplingRate__c"] = (mi_Audio_Text.split("<Sampling_rate>"))[1].split("</Sampling_rate>")[0]
        #if samplingRate == "44100":
        #    samplingRate = "44.1"
        #else:
        #    samplingRate = int(samplingRate)/1000
        #file_dict["essenceTrackSamplingRate__c"] = str(samplingRate) + " kHz"
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

    #try:
    # Checksum
    if hashType == "none":
        file_dict["messageDigest"] = ""
        file_dict["messageDigestAlgorithm"] = ""
    else:
        file_dict["messageDigest"] = hashfile(filePath, hashType, blocksize=65536)
        file_dict["messageDigestAlgorithm"] = hashType

    #except:
    #    print(bcolors.FAIL + "Error creating checksum for " + file_dict["instantiationIdentifierDigital__c"] + "\n\n" + bcolors.ENDC)

    return file_dict

#Process a single file
def createMediaInfoDict(filePath, file_dict):
    media_info_text = getMediaInfo(filePath)
    media_info_dict = parseMediaInfo(filePath, media_info_text, "md5", file_dict)
    return media_info_dict

#gets the Mediainfo text
def getMediaInfo(filePath):
    print(bcolors.OKBLUE +  "Harvesting Mediainfo for file: " + os.path.basename(filePath) + "\n" + bcolors.ENDC)
    cmd = [ '/usr/local/bin/mediainfo', '-f', '--Output=OLDXML', filePath ]
    media_info = subprocess.Popen( cmd, stdout=subprocess.PIPE,encoding='utf8').communicate()[0]
    return media_info

def createSpectro(filePath):
    print(bcolors.OKBLUE +  "Creating spectrogram for file: " + os.path.basename(filePath) + "\n" + bcolors.ENDC)

    soxString = "sox '" + filePath + "' -n spectrogram -o '" + filePath + ".png'"
    runCommand(soxString)

def createMP3(file_dict, wav_path, args):
    print(bcolors.OKBLUE +  "Creating derivatives for file: " + os.path.basename(wav_path) + "\n" + bcolors.ENDC)

    if args.s:
        print(bcolors.OKBLUE +  "Splitting the file according to the CUE track \n" + bcolors.ENDC)
        cue_tracks_list = parseCue(wav_path)
        mp3_path = wav_path.replace(".wav", ".mp3")
        w = 0
        while w<len(cue_tracks_list)-1:
            w_string = str(w+1)
            if len(w_string) == 1:
                w_string = "0" + w_string
            split_mp3_path = mp3_path.replace(".mp3", "_t" + w_string + ".mp3")
            if cue_tracks_list[w+1] == "01:39:99.987":
                to_string = " "
            else:
                to_string = " -to " + cue_tracks_list[w+1]
            ffmpeg_string = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic -ss " + cue_tracks_list[w] + to_string + " -i '" + wav_path + "' -c:a libmp3lame -b:a 320k -write_xing 0 -ac 2 -y '" + split_mp3_path + "'"
            runCommand(ffmpeg_string)
            w=w+1
            #insert metadat into mp3 we just created
            insertID3(file_dict["audioMetaDict"], split_mp3_path)
        if args.m:
            #if run with m flag we'll also make an unsplit mp3
            mp3_path = wav_path.replace(".wav", ".mp3")
            ffmpeg_string = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic -i '" + wav_path + "' -c:a libmp3lame -b:a 320k -write_xing 0 -ac 2 -y '" + mp3_path + "'"
            runCommand(ffmpeg_string)

            #insert metadat into mp3 we just created
            insertID3(file_dict["audioMetaDict"], mp3_path)

    else:
        mp3_path = wav_path.replace(".wav", ".mp3")
        ffmpeg_string = "/usr/local/bin/ffmpeg -hide_banner -loglevel panic -i '" + wav_path + "' -c:a libmp3lame -b:a 320k -write_xing 0 -ac 2 -y '" + mp3_path + "'"
        runCommand(ffmpeg_string)

        #insert metadat into mp3 we just created
        insertID3(file_dict["audioMetaDict"], mp3_path)

def parseCue(wav_path):
    cue_path = wav_path.replace(".wav", ".cue")
    cue_command = "/usr/local/bin/cuebreakpoints '" +  cue_path + "'"
    cue_breakpoints = runCommand(cue_command).decode()
    timestamp_list = ["00:00.00"]

    #turn output of cuebreakpoints into a nice list
    buff = []
    for c in cue_breakpoints:
        if c == '\n':
            timestamp_list.append(''.join(buff))
            buff = []
        else:
            buff.append(c)
    else:
        if buff:
            timestamp_list.append(''.join(buff))

    timestamp_list.append("99:99.74")


    #add leading zeroes to timestaps missing them before FFMPEG will need them
    formatted_timestamp_list = []
    for t in timestamp_list:
        t_split = t.split(":")
        ts_list = []
        for ts in t_split:
            if len(ts) == 1:        #adds leading zeroes
                ts = "0" + ts
            if "." in (ts):         #turns frames into milliseconds
                split_ts = ts.split(".")
                ms = round(int(split_ts[1]) / 0.075)
                ms_string = str(ms)
                ts = split_ts[0] + "."  + ms_string
            ts_list.append(ts)
        new_timestamp = ":".join(ts_list)
        if int(new_timestamp.split(":")[0]) > 59:
            new_min = str(int(t.split(":")[0]) - 60)
            if len(new_min) == 1:
                new_min = "0" + new_min
            new_hour = "01"
            new_timestamp = ":".join([new_hour,new_min,new_timestamp.split(":")[1]])
        else:
            new_timestamp = ":".join(["00",new_timestamp])
        formatted_timestamp_list.append(new_timestamp)

    return formatted_timestamp_list


def insertID3(audioMetaDict, filePath):
    print(bcolors.OKBLUE +  "Inserting metadata into file: " + os.path.basename(filePath) + "\n" + bcolors.ENDC)

    id3Artist = audioMetaDict['artistName']
    id3Album = audioMetaDict['albumName']
    id3Title = audioMetaDict['title']
    id3Year = audioMetaDict['yearDate']

    id3String = "id3v2 -a '" + id3Artist + "' -A '" + id3Album + "' -t '" + id3Title + "' -y '" + id3Year + "' '" + filePath + "'"
    runCommand(id3String)

def insertBWAV(file_dict, filePath):
    print(bcolors.OKBLUE +  "Inserting BWAV Metadata in file: " + os.path.basename(filePath) + "\n" + bcolors.ENDC)

    # Formats Descrition to "Title; Date"
    if file_dict['audioMetaDict']['createdDate'] == "0001-01-01" and file_dict['audioMetaDict']['title'] == "":
        bwavDescrition = ""
    elif file_dict['audioMetaDict']['createdDate'] == "0001-01-01":
        bwavDescrition = file_dict['audioMetaDict']['title']
    elif file_dict['audioMetaDict']['title'] == "":
        bwavDescrition = file_dict['audioMetaDict']['createdDate']
    elif file_dict['audioMetaDict']['createdDate'].split("-")[0] in file_dict['audioMetaDict']['title']:     #if the title already contains the date then don't add the date to the description
        bwavDescrition = file_dict['audioMetaDict']['title']
    else:
        bwavDescrition = file_dict['audioMetaDict']['title'] + "; " + file_dict['audioMetaDict']['createdDate']

    bwavOriginator = "BAVC"

    bwavOriginatorReference = file_dict["Name"]

    bwavOriginationDate = file_dict['audioMetaDict']['digiDate']

    if file_dict['audioMetaDict']['createdDate'] == "0001-01-01":
        ICRD = ""
    else:
        ICRD = file_dict['audioMetaDict']['createdDate']

    bwavUMID = "0000000000000000000000000000000000000000000000000000000000000000"

    INAM = file_dict['audioMetaDict']['title']
    ISRC = file_dict['audioMetaDict']['institution']
    ICMT = file_dict['audioMetaDict']['comment']
    ICOP = file_dict['audioMetaDict']['copyright']

    #look get log file text to put into coding history
    log_path = filePath.replace(".wav",".log")
    try:
        with open(log_path, 'r') as f:
            bwavCodingHistory = f.read()
    except:
        print(bcolors.FAIL + "Error parsing log file! The coding histoy will be wrong for this file" + bcolors.ENDC)


#   Pads blank space at end of coding history if the length is odd to make sure there is an even number of characters.
    codeHistLen = len(bwavCodingHistory)
    if codeHistLen % 2 != 0:
        bwavCodingHistory = bwavCodingHistory + " "

    bwfString = "bwfmetaedit --accept-nopadding --specialchars --Description='" + bwavDescrition + "' --Originator='" + bwavOriginator + "' --OriginationDate='TIMESTAMP' --IDIT='" + bwavOriginationDate + "' --ICRD='" + ICRD + "' --INAM='" + INAM + "' --ISRC='" + ISRC + "' --ICMT='" + ICMT +"' --ICOP='" + ICOP + "' --ISFT='XLD' --ITCH='BAVC' --OriginationTime='TIMESTAMP' --Timereference='00:00:00.000' --OriginatorReference='" + bwavOriginatorReference + "' --UMID='" + bwavUMID + "' --History='" + bwavCodingHistory + "' '" + filePath + "'"

    runCommand(bwfString)


def getFileList(inType,args):
    # If we are processing a single file
    fileList = []   #creating an empty list to load with files to be processed
    if inType == "F":
        if fileValid(args.i):
            fileList.append(args.i)
        else:
            print(bcolors.FAIL + "\nInvalid input file. Input must be .wav file with a .cue and .log sidecar file" + bcolors.ENDC)
    # If we are processing an entire directory file
    elif inType == "D":
        for root, dirs, files in os.walk(args.i):
            for name in files:
                fpath = os.path.join(root, name)
                if fpath.endswith(".wav"):
                    if fileValid(fpath):
                        fileList.append(fpath)
                    else:
                        print(bcolors.FAIL + "\nInvalid input file. Input must be .wav file with a .cue and .log sidecar file" + bcolors.ENDC)

    return fileList


def fileValid(inFile):
    file_name = os.path.basename(inFile)
    if file_name.endswith('.wav'):
        cue_path = inFile.replace(".wav", ".cue")
        log_path = inFile.replace(".wav", ".log")
        if os.path.exists(cue_path):
            if os.path.exists(log_path):
                return True
            else:
                return False
        else:
            return False
    else:
        return False

def fileOrDir(inPath):
    if os.path.isdir(inPath):
        return "D"
    elif os.path.isfile(inPath):
        return "F"
    else:
        print("I couldn't determine or find the input type!")
        quit()

#prococesses CSV data and inserts it into salesforce
def updateSalesForceCSV(csv_path):
    sf = initSF()
    dict_list = createDictList(csv_path)
    insertDictlist(dict_list,sf)

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
        if (len(d['Name']) != 7) or (not d['Name'].isdigit()):     #quick check to make surebarcode is properly formaed. If not we'll stop trying to sync to salesforce
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

#connect to salesforce
def initSF():
    #init salesforce login#
    try:
        print(bcolors.OKBLUE +  "Connecting To Salesforce\n" + bcolors.ENDC)
        sf = Salesforce(username=config.username,password=config.password,security_token=config.security_token)
        return sf
    except:
        print(bcolors.FAIL + "Salesforce Connection Failed. Quitting Script" + bcolors.ENDC)
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
def getSFAudioMD(Barcode, audioMetaDict):
    sf = initSF()
    sfData = querySF(sf,Barcode)
    recordID = sfData['records'][0]['Id']
    sfRecord = sf.Preservation_Object__c.get(recordID)
    audioMetaDict = {'title': None, 'createdDate': None,'artistName': None,'albumName': None,'digiDate': '','signalChain' : None,'institution' : None,'comment' : None,'copyright' : None}
    audioMetaDict['title'] = sfRecord.get('Audio_Metadata_Title__c')
    if audioMetaDict['title'] is None:
        audioMetaDict['title'] = ""
    else:
        audioMetaDict['title'] = audioMetaDict['title'].replace("'", "\'")
    audioMetaDict['albumName'] = sfRecord.get('Audio_Metadata_Album__c')
    if audioMetaDict['albumName'] is None:  #need to do this to make sure we get kill the script when these fields are empty
        audioMetaDict['albumName'] = ""
    else:
        audioMetaDict['albumName'] = audioMetaDict['albumName'].replace("'", "\'")
    audioMetaDict['artistName'] = sfRecord.get('Audio_Metadata_Artist__c')
    if audioMetaDict['artistName'] is None:
        audioMetaDict['artistName'] = ""
    else:
        audioMetaDict['artistName'] = audioMetaDict['artistName'].replace("'", "\'")
    audioMetaDict['institution'] = sfRecord.get('Embedded_Metadata_Institution__c')
    if audioMetaDict['institution'] is None:
        audioMetaDict['institution'] = ""
    else:
        audioMetaDict['institution'] = audioMetaDict['institution'].replace("'", "\'")
    audioMetaDict['comment'] = sfRecord.get('Embedded_Metadata_Comment__c')
    if audioMetaDict['comment'] is None:
        audioMetaDict['comment'] = ""
    else:
        audioMetaDict['comment'] = audioMetaDict['comment'].replace("'", "\'")
    audioMetaDict['copyright'] = sfRecord.get('Embedded_Metadata_Copyright__c')
    if audioMetaDict['copyright'] is None:
        audioMetaDict['copyright'] = ""
    else:
        audioMetaDict['copyright'] = audioMetaDict['copyright'].replace("'", "\'")
    audioMetaDict['signalChain'] = sfRecord.get('videoReproducingDevice__c')
    audioMetaDict['digiDate'] = sfRecord.get('instantiationDate__c')
    audioMetaDict['createdDate'] = convertDate(sfRecord.get('Audio_Metadata_Date__c'))


    return audioMetaDict

#Converts dd/mm/yy to YYYY-MM-DD
def convertDate(inDate):
    if (inDate == None) or (inDate == ""):
        formattedDate = "0001-01-01"
    else:#              As far as I can tell salesforce already returns ISO-8601 so we just need the check for an empty field above
    #    formattedDate = datetime.datetime.strptime(inDate, "%d/%m/%Y")    return formattedDate
        formattedDate = inDate
    return formattedDate

def getAudioMetadata(file_dict, filePath, barcode):

    #Get metadata to embed from salesforce
    audioMetaDict = {}
    try:
        audioMetaDict = getSFAudioMD(barcode, audioMetaDict)
    except:
        print(bcolors.WARNING + "\nSalesforce Connection Failed. Will get metadata manually" + bcolors.ENDC)
        audioMetaDict = {'title': None, 'createdDate': None,'artistName': None,'albumName': None,'digiDate': '','signalChain' : None}
    filename = os.path.basename(filePath)
    if audioMetaDict['title'] == None:
        audioMetaDict['title'] = input(bcolors.OKBLUE + "Please enter the title of " + filename + ", if any (No apostrophes or quotes please!): " + bcolors.ENDC)
    if audioMetaDict['createdDate'] == None:
        audioMetaDict['createdDate'] = input(bcolors.OKBLUE + "Please enter the Original Creation Date of this object, if any, in the format YYYY-MM-DD: " + bcolors.ENDC)
    if audioMetaDict['digiDate'] == None:
        audioMetaDict['digiDate'] = input(bcolors.OKBLUE + "Please enter the Digitization Date of this object YYYY-MM-DD: " + bcolors.ENDC)
    if audioMetaDict['artistName'] == None:
        audioMetaDict['artistName'] = input(bcolors.OKBLUE + "Please enter the Arist/Producer of this object: " + bcolors.ENDC)
    if audioMetaDict['albumName'] == None:
        audioMetaDict['albumName'] = input(bcolors.OKBLUE + "Please enter the Collection/Album name of this object: " + bcolors.ENDC)
    audioMetaDict['yearDate'] = audioMetaDict['createdDate'][:4]

    file_dict['audioMetaDict'] = audioMetaDict
    return file_dict

# Runs a command
def runCommand(cmd):
    print(bcolors.OKGREEN + "Running Command: " + cmd + "\n" + bcolors.ENDC)
    cmd_out = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).communicate()[0]
    return cmd_out

# Generate checksum for the file
def hashfile(filePath, hashalg, blocksize=65536):
    print(bcolors.OKBLUE +  "Harvesting checksum for file: " + os.path.basename(filePath) + "\n" + bcolors.ENDC)
    afile = open(filePath,'rb')
    hasher = hashlib.new(hashalg) #grab the hashing algorithm decalred by user
    buf = afile.read(blocksize) # read the file into a buffer cause it's more efficient for big files
    while len(buf) > 0: # little loop to keep reading
        hasher.update(buf) # here's where the hash is actually generated
        buf = afile.read(blocksize) # keep reading
    return hasher.hexdigest()

# Create a CSV file from a dict
def createCSV(media_info_list, csv_path):
    keys = media_info_list[0].keys()
    with open(csv_path, 'w') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(media_info_list)

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
