import os
from pytex import AtlasPacker

if __name__ == "__main__":
    imageFilenames = []
    for filename in os.listdir("res"):
        imageFilenames.append( os.path.join( "res", filename ) )
        
    packer = AtlasPacker()
    packer.Pack(imageFilenames, (2048, 2048), "example.png", "example.xml")
