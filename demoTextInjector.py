"""
Adapted from Green Goblins scripts. 
This is really heavily based on his awesome work. 

Script for working with Metal Gear Solid data

Copyright (C) 2023 Green_goblin (https://mgsvm.blogspot.com/)

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

"""

import os, sys
sys.path.append(os.path.abspath('./myScripts'))
import re
import glob
import struct
import progressbar
import translation.radioDict as RD
import json

import DemoTools.demoTextExtractor as DTE
from common.structs import subtitle

# --- CHANGE ---
# version = "mc"
# disc = 1
# Get command-line arguments (version and disc)
if len(sys.argv) < 3:
    print(f" Usage: python {sys.argv[0]} <version> <disc>")
    print(f"Example: python {sys.argv[0]} usa 1")
    sys.exit(1)

version = sys.argv[1]
try:
    disc = int(sys.argv[2])
except ValueError:
    print(f"Error: Disc number must be an integer. Got: {sys.argv[2]}")
    sys.exit(1)

print(f"Running for Version: {version}, Disc: {disc}...")
# --- END CHANGE ---

# Toggles
debug = True

# Directory configs
inputDir = f'workingFiles/{version}-d{disc}/demo/bins'
outputDir = f'workingFiles/{version}-d{disc}/demo/newBins'
injectJson = f'workingFiles/{version}-d{disc}/demo/demoText-{version}.json'
os.makedirs(outputDir, exist_ok=True)

# Collect files to use
bin_files = glob.glob(os.path.join(inputDir, '*.dmo'))
bin_files.sort(key=lambda f: int(f.split('-')[-1].split('.')[0]))

# --- CHANGE 2: Fixed 'json.load(open(open(...)))' error ---
# Collect source json to inject
try:
    # Incorrect line: injectTexts = json.load(open(open(injectJson, 'r', encoding='utf-8')))
    # Corrected version (safer with 'with' block):
    # INFO: This code can read both single-line (minified) and vertical (indented) JSON files.
    # Therefore, no change was needed here after the change in Extractor.
    with open(injectJson, 'r', encoding='utf-8') as f:
        injectTexts = json.load(f)
except FileNotFoundError:
    print(f"ERROR: JSON file not found!")
    print(f"Searched path: {os.path.abspath(injectJson)}")
    print(f"Please ensure the 'version' and 'disc' variables are set correctly.")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"ERROR: JSON file is corrupt or has an invalid format: {injectJson}")
    print("Please check the contents of the JSON file.")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)


# --- (This definition is used if not under common.structs)
"""
class subtitle:
    text: str
    startFrame: int
    duration: int

    def __init__(self, dialogue, b, c) -> None:
        self.text = dialogue
        self.startFrame = int(b)
        self.duration = int(c)

        return
    
    def __str__(self) -> str:
        a = f'Subtitle contents: Start: {self.startFrame} Duration: {self.duration} Text: {self.text}'
        return a
    
    def __bytes__(self) -> bytes:
        
        # Simple. Encodes the dialogue as bytes. 
        # Adds the buffer we need to be divisible by 4...
        # Return the new bytes.
        
        subtitleBytes: bytes = struct.pack("III", self.startFrame, self.duration, 0)
        
        # !!! USER NOTE !!!
        # This is the critical part that converts your text into bytes the game can understand.
        # Since you are doing a translation with special characters (e.g., ğ, ü, ş, ı, ö, ç),
        # the 'encodeJapaneseHex' function in your 'translation/radioDict.py' file
        # MUST be configured to support these specific characters.
        # If this function is not set up, the characters will be corrupted.
        subtitleBytes += RD.encodeJapaneseHex(self.text)[0]
        
        bufferNeeded = 4 - (len(subtitleBytes) % 4)
        subtitleBytes += bytes(bufferNeeded)
        
        return subtitleBytes
"""

def assembleTitles(demoData: dict) -> list [subtitle]:
    """
    Reads the new JSON format from the Extractor.
    Format: {"start_frame_str": {"duration": "...", "text": "..."}}
    """
    subsList = []
    temp_list = [] # First, we'll add to a temporary list and then sort it

    # Iterate over demoData.items() to get both the key (start_frame) and the data
    for start_frame_str, data in demoData.items():
        try:
            start_frame_int = int(start_frame_str)
            duration_int = int(data["duration"])
            text = data["text"]
            
            # According to the subtitle class __init__ structure (text, start, duration)
            a = subtitle(text, start_frame_int, duration_int)
            temp_list.append(a)
            
        except ValueError as e:
            print(f"ERROR: An error occurred while processing JSON data. Key: {start_frame_str}, Error: {e}")
            continue
        except KeyError as e:
            print(f"ERROR: Missing key in JSON. Key: {start_frame_str}, Looked for: {e}")
            continue

    # Sort the subtitles by their start time (startFrame).
    # This is VERY IMPORTANT for ensuring the subtitles are added in the correct order.
    subsList = sorted(temp_list, key=lambda s: s.startFrame)
    
    return subsList


"""
# TODO:
- change key to int (DONE)
- make sure range hits all texts (DONE)
"""
skipFilesListD1 = [
    'demo-05',
    'demo-06',
    'demo-31',
    'demo-33',
    'demo-35',
    'demo-63',
    'demo-67',
    'demo-71',
    'demo-72',
]

def genSubBlock(subs: list [subtitle] ) -> bytes:
    """
    Injects the new text to the original data, returns the bytes. 
    Also returns the index we were at when we finished. 

    """ 
    newBlock = b''
    
    # If there are no subtitles in this block, return empty bytes
    if not subs:
        return newBlock

    # Loop through the subtitles (up to the second to last one)
    for i in range(len(subs) - 1):
        sub_bytes = bytes(subs[i])
        length = struct.pack("I", len(sub_bytes) + 4) # +4 bytes (for the length itself)
        newBlock += length + sub_bytes
    
    # Add the last subtitle (its length byte should be 0x00000000)
    newBlock += bytes(4) + bytes(subs[-1])
    
    return newBlock

def getDemoDiagHeader(data: bytes) -> bytes:
    """
    Returns the header portion only for a given dialogue section.
    """
    headerLength = struct.unpack("H", data[14:16])[0] + 4
    return data[:headerLength]

# if debug:
#     print(f'Only injecting Demo 25!')
#     bin_files = ['demoWorkingDir/usa/bins/demo-25.dmo']

if __name__ == "__main__":
    """
    Main logic is here.
    """
    # Let's start the progress bar here
    bar = progressbar.ProgressBar(maxval=len(bin_files)).start()
    barCount = 0

    for file in bin_files:
        # print(os.path.basename(f"{file}: "), end="") # Not needed with the progress bar
        filename = os.path.basename(file)
        basename = filename.split(".")[0]

        # if debug:
        #     print(f'Processing {basename}')

        if basename in skipFilesListD1:
            if debug:
                # print(f'{basename} in skip list. Continuing...         ')
                barCount += 1
                bar.update(barCount)
            continue

        if basename not in injectTexts:
            # print(f'{basename} was not in the json. Skipping...\r', end="")
            barCount += 1
            bar.update(barCount)
            continue
        
        # Initialize the demo data and the dictionary we're using to replace it.
        origDemoData = open(file, 'rb').read()
        origBlocks = len(origDemoData) // 0x800 # Use this later to check we hit the same length!
        
        demoData: dict = injectTexts[basename] # NEW (Dictionary containing all data)
        
        subtitles = assembleTitles(demoData) # NEW

        offsets = DTE.getTextAreaOffsets(origDemoData)
        
        # If no offsets are found, it means there is no text area in this file.
        if not offsets:
            barCount += 1
            bar.update(barCount)
            continue # Move to the next file

        newDemoData = origDemoData[0 : offsets[0]] # UNTIL the header
        
        current_sub_index = 0 # To keep track of which subtitle we are processing

        for Num in range(len(offsets)):
            oldHeader = getDemoDiagHeader(origDemoData[offsets[Num]:])
            oldLength = struct.unpack("H", oldHeader[1:3])[0]
            frameStart = struct.unpack("I", oldHeader[4:8])[0]
            frameLimit = struct.unpack("I", oldHeader[8:12])[0]
            
            # Get only subtitles in this section.
            subsForSection = []
            
            while current_sub_index < len(subtitles):
                sub = subtitles[current_sub_index]
                if frameStart <= sub.startFrame < frameLimit:
                    subsForSection.append(sub)
                    current_sub_index += 1 # Move to the next subtitle
                else:
                    # This subtitle doesn't belong to this section, break the loop and move to the next section
                    break 
            
            newSubBlock = genSubBlock(subsForSection)
            
            # --- HEADER UPDATE LOGIC ---
            # Base it on the original header
            newHeaderBytes = bytearray(oldHeader)
            
            # Calculate the new total length (Header + Subtitle Block)
            newTotalLength = len(oldHeader) + len(newSubBlock)
            
            # Write the new length into the header (offset 1, 2 bytes, little-endian)
            struct.pack_into("<H", newHeaderBytes, 1, newTotalLength)
            
            # Calculate the new "internal" length (Total - 4)
            # (This is usually at offset 0x10)
            newInnerLength = newTotalLength - 4
            struct.pack_into("<I", newHeaderBytes, 16, newInnerLength)

            # If there are no subtitles (section is empty), set the length to the header's own length
            if not subsForSection:
                struct.pack_into("<H", newHeaderBytes, 1, len(oldHeader))
                struct.pack_into("<I", newHeaderBytes, 16, len(oldHeader) - 4)

            newHeader = bytes(newHeaderBytes)
            # --- END HEADER UPDATE ---

            newDemoData += newHeader + newSubBlock
            
            # Add the rest of the data from this to the next offset OR until end of original demo. 
            if Num < len(offsets) - 1: # if it is NOT the last... 
                newDemoData += origDemoData[offsets[Num] + oldLength: offsets[Num + 1]]
            else:
                newDemoData += origDemoData[offsets[Num] + oldLength: ]
            # if debug:
            #     print(newSubBlock.hex(sep=" ", bytes_per_sep=4))
        
        # Adjust length to match original file.
        if len(newDemoData) == len(origDemoData):
            # print("Alignment correct!") # Stay silent with the bar
            pass
        elif len(newDemoData) < len(origDemoData): # new demo shorter
            newDemoData += bytes(len(origDemoData) - len(newDemoData)) 
            if len(newDemoData) % 0x800 == 0:
                # print("Alignment correct!") # Stay silent with the bar
                pass
        else:
            # If the new data is longer than the original, this is a problem
            print(f'\nCRITICAL ERROR! {basename} is LONGER ({len(newDemoData)}) than original ({len(origDemoData)})!')
            # Let's try to truncate like in the original script, but this is dangerous.
            checkBytes = newDemoData[len(origDemoData):] # The part exceeding the original size
            # If the excess part consists only of null bytes, we can safely truncate it
            if all(b == 0 for b in checkBytes):
                print("Truncating trailing null bytes...")
                newDemoData = newDemoData[:len(origDemoData)]
                # print("Alignment correct!")
            else:
                print(f'CRITICAL ERROR! {basename} cannot be truncated to original length!')
                print(f'New: {len(newDemoData)} vs Old: {len(origDemoData)}')
                # exit() # Commenting out the exit for debugging, you can re-enable it if you want
        
        newBlocks = len(newDemoData) // 0x800
        if newBlocks != origBlocks:
            print(f"\n{basename}: {len(newDemoData)} / {len(origDemoData)}") 
            print(f'BLOCK MISMATCH!\nNew data is {newBlocks} blocks, old was {origBlocks} blocks.\nTHERE COULD BE PROBLEMS IN RECOMPILE!!')

        # Finished work! Write the new file. 
        newFile = open(f'{outputDir}/{basename}.dmo', 'wb')
        newFile.write(newDemoData)
        newFile.close()
        
        barCount += 1
        bar.update(barCount)

    bar.finish()
    print(f'New Demo Files have been injected!')
    sys.exit(0) # Used sys.exit(0) to indicate success