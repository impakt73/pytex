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
                packer.Pack(imageFilenames, (128, 128), (8192, 8192), "uv", outputImagePath, outputManifestPath)
            else:
                print "No images found in directory %s!" % directoryPath
        else:
            if os.path.exists(sys.argv[1]) and os.path.splitext(sys.argv[1])[1] in IMAGE_EXTENSIONS:
                imagePath = sys.argv[1]
                print "Slicing image %s into 128x128 chunks!" % imagePath

                packer = AtlasPacker()
                packer.Slice(imagePath, (128, 128))
            else:
                print "Invalid image path supplied!"
    else:
        print "No directory supplied!"
