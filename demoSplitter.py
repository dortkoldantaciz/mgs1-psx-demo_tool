import os, struct, sys
# import progressbar, time

# --- CHANGE ---
# version = "mc"
# disc = 1
# Get command-line arguments (version and disc)
if len(sys.argv) < 3:
    print(f" Usage: python {sys.argv[0]} <version> <disc>")
    print(f" Example: python {sys.argv[0]} usa 1")
    sys.exit(1)

version = sys.argv[1]
try:
    disc = int(sys.argv[2])
except ValueError:
    print(f"Error: Disc number must be an integer. Got: {sys.argv[2]}")
    sys.exit(1)

print(f"Running for Version: {version}, Disc: {disc}...")
# --- END CHANGE ---

filename = f"build-src/{version}-d{disc}/MGS/DEMO.DAT"
outputDir = f"workingFiles/{version}-d{disc}/demo/bins"

demoFile = open(filename, 'rb')
demoData = demoFile.read()

offsets = []
os.makedirs(outputDir, exist_ok=True)
opening = b'\x10\x08\x00\x00'
# opening = b'\x10\x08\x00\x00\x05\x00\x00\x00'

def findDemoOffsets():
    offset = 0
    while offset < len(demoData) - 8:
        # print(f'We\'re at {offset}\n')
        checkbytes = demoData[offset:offset + 4]
        if checkbytes == opening:
            print(f'Offset found at offset {offset}!')
            offsets.append(offset)
            offset += 2048 # All demo files are aligned to 0x800, SIGNIFICANTLY faster to do this than +8! Credit to Green Goblin
        else:
            offset += 2048

    print(f'Ending! {len(offsets)} offsets found:')
    for offset in offsets:
        print(offset.to_bytes(4, 'big').hex())

def splitDemoFiles():
    i = 0
    offsetFile = open(f'{outputDir}/demoOffsets.txt', 'w')
    for i in range(len(offsets)):  
        start = offsets[i] 
        if i < len(offsets) - 1:
            end = offsets[i + 1]
        else:
            end = len(demoData) 
        f = open(f'{outputDir}/demo-{i + 1:02}.dmo', 'wb')
        offsetFile.write(f'{i + 1:02}: {start:08x} - {end:08x}, length: {end - start}\n')
        f.write(demoData[start:end])
        f.close()
        print(f'Demo {i + 1} written!')
    
    print(f'{len(offsets)} demo files written!')


if __name__ == '__main__':
    findDemoOffsets()
    splitDemoFiles()