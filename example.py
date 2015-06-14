import os
import sys
from pytex import AtlasPacker

IMAGE_EXTENSIONS = {".jpg", ".png"}

if __name__ == "__main__":
    if len(sys.argv) == 2:
        if os.path.isdir(sys.argv[1]):
            directoryPath = sys.argv[1]
            
            imageFilenames = [os.path.join(directoryPath, x) for x in os.listdir(directoryPath) if os.path.splitext(x)[1].lower() in IMAGE_EXTENSIONS]
            
            if len(imageFilenames) > 0:
                print "Found %d images in %s!" % (len(imageFilenames), directoryPath)
                directoryName = os.path.basename(directoryPath)
                parentPath = os.path.dirname(directoryPath)
                outputImagePath = os.path.join(parentPath, directoryName + ".png")
                outputManifestPath = os.path.join(parentPath, directoryName + ".xml")
                packer = AtlasPacker()
                packer.Pack(imageFilenames, (128, 128), (8192, 8192), outputImagePath, outputManifestPath)
            else:
                print "No images found in directory %s!" % directoryPath
        else:
            print "Invalid directory '%s' supplied!" % sys.argv[1]
    else:
        print "No directory supplied!"