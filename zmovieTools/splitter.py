"""
Adapted from Green Goblins scripts. Very similar to demo
only alignments are 0x920
"""

import os, struct, re, sys, glob
sys.path.append(os.path.abspath('./myScripts'))
sys.path.append(os.path.abspath('.'))
import DemoTools.demoTextExtractor as DTE

version = "jpn"
filename = f"build-src/{version}-d1/MGS/ZMOVIE.STR"
outputDir = f"zMovieWorkingDir/{version}/bins"

zMovieScript = {}

zmFile = open(filename, 'rb')
zmData = zmFile.read()


offsets = []
os.makedirs(outputDir, exist_ok=True)

def getOffsets(toc: bytes) -> list:
    demoNum = 4 # If we figure out where this is we can implement it.
    offsets = []
    counter = 16
    for i in range(demoNum):
        offset = struct.unpack("<I", toc[counter : counter + 4])[0]
        offsets.append(offset * 0x920)
        counter += 8
    return offsets

if __name__ == "__main__":
    
    # movieOffsets = getOffsets(zmData[0:0x920])
    # movieOffsets.append(len(zmData))
    # print(movieOffsets)

    # for i in range(len(movieOffsets) - 1):
    #     # Write the output movie file
    #     with open(f'{outputDir}/{i:02}-movie.bin', 'wb') as f:
    #         start = movieOffsets[i]
    #         end = movieOffsets[i + 1]
    #         # Output movie data
    #         f.write(zmData[start : end])

    bin_files = glob.glob(os.path.join(outputDir, '*.bin'))
    bin_files.sort(key=lambda f: int(f.split('/')[-1].split('-')[0]))

    for bin_file in bin_files:
        with open(bin_file, 'rb') as movieTest:
            filename = os.path.basename(bin_file)
            DTE.filename = filename
            movieData = movieTest.read()

            # Get text areas
            matches = re.finditer(b'\x02\x00\x00\x00......\x10\x00', movieData, re.DOTALL)
            offsets = [match.start() for match in matches]

            # Trim false positives.
            finalMatches = []
            for offset in offsets:
                if movieData[offset + 28: offset + 32] == bytes(4):
                    finalMatches.append(offset)
            
            offsets = finalMatches

            texts = []
            timings = [] # list of timings (start time, duration)
            timingCount = 1
            # For now we assume they are correct.
            for offset in offsets:
                # offset = offsets[0]
                length = struct.unpack("I", movieData[offset + 12 : offset + 16])[0]
                subset = movieData[offset + 16: offset + length]
                textHexes, graphicsBytes, coords = DTE.getTextHexes(subset)
                texts.extend(DTE.getDialogue(textHexes, graphicsBytes))
                timings.extend(coords)

            basename = filename.split('.')[0]
            zMovieScript[basename] = [DTE.textToDict(texts), DTE.textToDict(timings)]
            DTE.writeTextToFile(f'{outputDir}/{basename}.txt', texts)
        