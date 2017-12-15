#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Version History 
#	0.1 - 20170707
#		Creates a CSV file with all of the correct field names to match up with the SalesForce table. No bells or whistles. Input args suck
#	0.2 - 20170707
#       Added a progress bar because checksums take so long so it's nice to know 
#	0.3 - 20171010
#       Removed pymediainfo from the script because it sucks and doesn't work


# import modules used here -- sys is a very standard one
import os, sys
import datetime
#from pymediainfo import MediaInfo 	# used for harvesting mediainfo. Really great lib!
import csv							# used for creating the csv
import hashlib						# used for creating the md5 checksum
import subprocess

# Gather our code in a main() function
def main():
	media_info_list = []

	#handling the input args. This is kind of a mess in this version
	if len(sys.argv) == 1:
		print "Please enter at least 1 System Argument!"
		print "Systerm Arguemnt 1 should be path to file or directory to process (required)"
		print "Systerm Arguemnt 2 should be output path of CSV file (optional)"
		quit()
	elif len(sys.argv) == 2:
		print "No output path defined, using default path"
		out_path = ""
	
	inPath = sys.argv[1]
	inType = fileOrDir(inPath)
	# This part can tell if we're processing a file or directory. Handles it accordingly
	if inType == "F":
		print "Processing Input File: " + os.path.basename(inPath)
		media_info_list.append(createMediaInfoDict(inPath, inType))
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
			csv_path = sys.argv[2]
		print "Output CSV file path is: " + csv_path
		
		# Need this part to get the number of Mov files. 
		movCount = 0
		for root, directories, filenames in os.walk(inPath):
			for filename in filenames:
			    tempFilePath = os.path.join(root,filename)  		    
			    if tempFilePath.endswith('.mov'):
			        movCount = movCount + 1
                
		
		for root, directories, filenames in os.walk(inPath):
			fileIndex = 0
			for filename in filenames: 		    
			    #Process the file   
			    tempFilePath = os.path.join(root,filename) 
			    if tempFilePath.endswith('.mov'):
			    
			    	#Progress bar fun
			    	numFiles = movCount
			        percentDone = float(float(fileIndex)/float(numFiles)*100.0)
			        sys.stdout.write('\r')
			        sys.stdout.write("[%-20s] %d%% %s \n" % ('='*int(percentDone/5.0), percentDone, filename))
			        sys.stdout.flush()
			        fileIndex = fileIndex + 1
			        
			        media_info_list.append(createMediaInfoDict(tempFilePath, inType)) # Turns the dicts into lists
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
def createMediaInfoDict(filePath, inType):
	media_info_text = getMediaInfo(filePath)
	media_info_dict = parseMediaInfo(filePath, media_info_text)
	return media_info_dict
	
#gets the Mediainfo text
def getMediaInfo(filePath):	
	cmd = [ '/usr/local/bin/mediainfo', '-f', '--Output=OLDXML', filePath ]
	media_info = subprocess.Popen( cmd, stdout=subprocess.PIPE ).communicate()[0]
	return media_info
	
#process mediainfo object into a dict
def parseMediaInfo(filePath, media_info_text):
	# The following line initializes the dict. 
	file_dict = {"Name" : "", "instantiationIdentifierDigital__c" : "", "essenceTrackDuration__c" : "", "instantiationFileSize__c" : "", "instantiationDigital__c" : "", "essenceTrackEncodingVideo__c" : "", "essenceTrackBitDepthVideo__c" : "", "essenceTrackCompressionMode__c" : "", "essenceTrackScanType__c" : "", "essenceTrackFrameRate__c" : "", "essenceTrackFrameSize__c" : "", "essenceTrackAspectRatio__c" : "", "instantiationDataRateVideo__c" : "", "instantiationDigitalColorMatrix__c" : "", "instantiationDigitalColorSpace__c" : "", "instantiationDigitalChromaSubsampling__c" : "", "instantiationDataRateAudio__c" : "", "essenceTrackBitDepthAudio__c" : "", "essenceTrackSamplingRate__c" : "", "essenceTrackEncodingAudio__c" : "", "instantiationChannelConfigDigitalLayout__c" : "", "instantiationChannelConfigurationDigital__c" : "", "messageDigest" : "", "messageDigestAlgorithm" : ""}
	file_dict["instantiationIdentifierDigital__c"] = os.path.basename(filePath)
	barcodeTemp = file_dict["instantiationIdentifierDigital__c"]
	try:
		barcodeTemp = str(barcodeTemp).split("_")[0]
		file_dict["Name"] = barcodeTemp.split("BAVC")[1]
	except:
		print "Error parsing filename, No Barcode given for this file!"
	#mi_General_Text = str(media_info_text).split("<track type=\"General\">")[1]
	#mi_General_Text = str(mi_General_Text).split("</track>")[0]
	#mi_Video_Text = str(media_info_text).split("<track type=\"Video\">")[1]
	#mi_Video_Text = str(mi_General_Text).split("</track>")[0]
	#mi_Audio_Text = str(media_info_text).split("<track type=\"Audio\">")[1]
	#mi_Audio_Text = str(mi_General_Text).split("</track>")[0]
	
	try:
	
		mi_General_Text = (media_info_text.split("<track type=\"General\">"))[1].split("</track>")[0]
		mi_Video_Text = (media_info_text.split("<track type=\"Video\">"))[1].split("</track>")[0]
		mi_Audio_Text = (media_info_text.split("<track type=\"Audio\">"))[1].split("</track>")[0]
	
		# General Stuff
	
		file_dict["essenceTrackDuration__c"] = (mi_General_Text.split("<Duration>"))[6].split("</Duration>")[0]
		fileFormatTemp = (mi_General_Text.split("<Format>"))[1].split("</Format>")[0]
		if fileFormatTemp == "MPEG-4":
			file_dict["instantiationDigital__c"] = "MOV"
		file_dict["instantiationFileSize__c"] = (mi_General_Text.split("<File_size>"))[6].split("</File_size>")[0]
	
		# Video Stuff
	
		file_dict["essenceTrackEncodingVideo__c"] = (mi_Video_Text.split("<Codec_ID>"))[1].split("</Codec_ID>")[0]
		file_dict["essenceTrackBitDepthVideo__c"] = (mi_Video_Text.split("<Bit_depth>"))[2].split("</Bit_depth>")[0]
		file_dict["essenceTrackCompressionMode__c"] = (mi_Video_Text.split("<Compression_mode>"))[1].split("</Compression_mode>")[0]
		file_dict["essenceTrackScanType__c"] = (mi_Video_Text.split("<Scan_type>"))[1].split("</Scan_type>")[0]
		file_dict["essenceTrackFrameRate__c"] = (mi_Video_Text.split("<Frame_rate>"))[1].split("</Frame_rate>")[0]
		frame_width = (mi_Video_Text.split("<Width>"))[1].split("</Width>")[0]
		frame_height = (mi_Video_Text.split("<Height>"))[1].split("</Height>")[0]
		file_dict["essenceTrackFrameSize__c"] = frame_width + " x " + frame_height
		file_dict["essenceTrackAspectRatio__c"] = (mi_Video_Text.split("<Display_aspect_ratio>"))[2].split("</Display_aspect_ratio>")[0]
		file_dict["instantiationDataRateVideo__c"] = (mi_Video_Text.split("<Bit_rate>"))[2].split("</Bit_rate>")[0]
		file_dict["instantiationDigitalColorMatrix__c"] = (mi_Video_Text.split("<Color_primaries>"))[1].split("</Color_primaries>")[0]
		file_dict["instantiationDigitalColorSpace__c"] = (mi_Video_Text.split("<Color_space>"))[1].split("</Color_space>")[0]
		file_dict["instantiationDigitalChromaSubsampling__c"] = (mi_Video_Text.split("<Chroma_subsampling>"))[1].split("</Chroma_subsampling>")[0]
			
		# Audio Stuff
	
		file_dict["instantiationDataRateAudio__c"] = (mi_Audio_Text.split("<Bit_rate>"))[1].split("</Bit_rate>")[0]
		file_dict["essenceTrackBitDepthAudio__c"] = (mi_Audio_Text.split("<Resolution>"))[1].split("</Resolution>")[0]
		file_dict["essenceTrackSamplingRate__c"] = (mi_Audio_Text.split("<Sampling_rate>"))[1].split("</Sampling_rate>")[0]
		file_dict["essenceTrackEncodingAudio__c"] = (mi_Audio_Text.split("<Codec>"))[1].split("</Codec>")[0]
		if file_dict["essenceTrackEncodingAudio__c"] == "PCM":
			file_dict["essenceTrackEncodingAudio__c"] = "Linear PCM"
		file_dict["instantiationChannelConfigDigitalLayout__c"] = (mi_Audio_Text.split("<Channel_s_>"))[2].split("</Channel_s_>")[0]
		file_dict["instantiationChannelConfigurationDigital__c"] = (mi_Audio_Text.split("<ChannelLayout>"))[1].split("</ChannelLayout>")[0]
			
		# Checksum
		
		file_dict["messageDigest"] = hashfile(filePath, "md5", blocksize=65536)
		file_dict["messageDigestAlgorithm"] = "md5"
	
	except:
		print "Error parsing mediainfo for " + file_dict["instantiationIdentifierDigital__c"]	

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

# Standard boilerplate to call the main() function to begin
# the program.	
if __name__ == '__main__':
	main()
	