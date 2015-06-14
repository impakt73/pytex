"""
pytex
Copyright (C) 2015  Gregory Mitrano

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

from PIL import Image, ImageOps
from cygon import CygonRectanglePacker
from xml.etree.cElementTree import Element, ElementTree, SubElement, tostring
import xml.dom.minidom
import os

class ImageInfo(object):
    """A small data structure for holding information about images"""

    def __init__(self):
        self.name = ""
        self.path = ""
        self.containsAlpha = False
        self.boundingBox = [0, 0, 0, 0]

class PackedImageInfo(object):
    """A small data structure for holding information about packed images"""
    
    def __init__(self, packPosition, packedBoundingBox):
        self.packPosition = packPosition
        self.packedBoundingBox = packedBoundingBox

class AtlasPacker(object):
    """A class for packing texture atlases"""
    
    def __init__(self):
        pass
    
    def _Lerp(self, x, max):
        return float( x ) / float( max )
    
    def _FindBBox(self, image, color=(0,0,0,0)):
        alphaTestMode = ( color[3] is 0 )
        img = image.load()
        bbox = [0,0,image.size[0],image.size[1]]
        
        # Find top
        for y in xrange( image.size[1] ):
            emptyRow = True
            for x in xrange( image.size[0] ):
                pixel = img[x, y]
                
                if alphaTestMode:
                    if pixel[3] != 0:
                        emptyRow = False
                        break
                else:
                    if pixel != color:
                        emptyRow = False
                        break
            
            if not emptyRow:
                bbox[1] = y
                break
            
        # Find bottom
        for y in reversed( xrange( image.size[1] ) ):
            emptyRow = True
            for x in reversed( xrange( image.size[0] ) ):
                pixel = img[x, y]
                
                if alphaTestMode:
                    if pixel[3] != 0:
                        emptyRow = False
                        break
                else:
                    if pixel != color:
                        emptyRow = False
                        break
            
            if not emptyRow:
                bbox[3] = y+1
                break
            
        # Find left
        for x in xrange( image.size[0] ):
            emptyRow = True
            for y in xrange( image.size[1] ):
                pixel = img[x, y]
                
                if alphaTestMode:
                    if pixel[3] != 0:
                        emptyRow = False
                        break
                else:
                    if pixel != color:
                        emptyRow = False
                        break
            
            if not emptyRow:
                bbox[0] = x
                break
            
        # Find right
        for x in reversed( xrange( image.size[0] ) ):
            emptyRow = True
            for y in reversed( xrange( image.size[1] ) ):
                pixel = img[x, y]
                
                if alphaTestMode:
                    if pixel[3] != 0:
                        emptyRow = False
                        break
                else:
                    if pixel != color:
                        emptyRow = False
                        break
            
            if not emptyRow:
                bbox[2] = x+1
                break
        
        return tuple( bbox )
                    
    def _GetImageInfo(self, imagePaths):
        # A list of the resulting ImageInfo objects
        imageInfoList = []

        # Collect information about the images
        for filepath in imagePaths:
            try:
                # Set up some basic info about the image.
                imageInfo = ImageInfo()
                imageInfo.name = os.path.basename(filepath)
                imageInfo.path = filepath

                # Open the image.
                image = Image.open(filepath)

                # Check if the image has alpha.
                imageInfo.containsAlpha = (image.mode == "RGBA")

                # Extract the dimensions of the image.
                imageInfo.boundingBox =  [0, 0, image.size[0], image.size[1]]

                # Collect the result
                imageInfoList.append(imageInfo)

            except IOError:
                pass

        # Sort the image info list so we get constant results.
        imageInfoList = sorted(imageInfoList, key=lambda imageInfo: imageInfo.name)

        # Return the results.
        return imageInfoList

    def _CropBoundingBoxes(self, imageInfoList, cropColor):
        # Keep track of the result.
        result = True

        # Crop bounding box for each image in the list.
        for imageInfo in imageInfoList:
            try:
                # Load the image
                image = Image.open(imageInfo.path)

                # Make sure it's in RGBA format.
                if image.mode != "RGBA":
                    image = image.convert("RGBA")

                # Crop the bounding box using the image data.
                imageInfo.boundingBox = self._FindBBox(image, cropColor)
            
            except IOError:
                result = False

        return result

    def _PackImages(self, imageInfoList, padding, size):
        # Create a dictionary of imagePaths to tuples of ImageInfo and PackedImageInfo
        packedImageDict = dict()

        # A bool that indicates success or failure.
        packingResult = True

        # Create a rectangle packer for the current size.
        packer = CygonRectanglePacker(*size)

        # Calculate the texel width and height for the current size.
        texelWidth = 1.0 / float( size[0] )
        texelHeight = 1.0 / float( size[1] )

        # Attempt to pack each image.
        for imageInfo in imageInfoList:
            assert imageInfo.path not in packedImageDict

            # Get the image dimensions
            imageWidth = imageInfo.boundingBox[2]
            imageHeight = imageInfo.boundingBox[3]

            # Calculate the effective image dimensions.
            effectiveImageWidth = imageWidth + (padding * 2.0)
            effectiveImageHeight = imageHeight + (padding * 2.0)

            # Send the image over to the packing algorithm
            packingResult = packer.Pack(effectiveImageWidth, effectiveImageHeight)
            if packingResult is not None:
                # The pack was successful, calculate the values for the packed bounding box.
                packedX = self._Lerp(packingResult.x + padding, size[0])
                packedY = self._Lerp(packingResult.y + padding, size[1])
                packedWidth = float(imageWidth * texelWidth)
                packedHeight = float(imageHeight * texelHeight)
                packedImageDict[imageInfo.path] = (imageInfo, PackedImageInfo((int(packingResult.x), int(packingResult.y)), [packedX, packedY, packedWidth, packedHeight]))
            else:
                # The pack failed. Destroy all results and return.
                packedImageDict.clear()
                packingResult = False
                break

        # Return the results.
        return (packingResult, packedImageDict)

    def _CompositePackedImages(self, outputPath, size, padding, packedImageDict):
        # Keep track of the result.
        result = True

        # Create the output image.
        outImage = Image.new("RGBA", size)

        # Composite all packed images into the output image.
        for packedImagePath, packedImageData in packedImageDict.iteritems():
            try:
                # Open the image
                image = Image.open(packedImageData[0].path)

                # Make sure it's an RGBA image.
                if image.mode != "RGBA":
                    image = image.convert("RGBA")

                # Crop the image to its bounding box.
                image = image.crop(packedImageData[0].boundingBox)

                # Pad the image.
                image = ImageOps.expand(image, padding, 0)

                # Paste the image into the output image.
                outImage.paste(image, packedImageData[1].packPosition)

            except IOError:
                result = False

        # Save the output image
        outImage.save(outputPath)

        return result

    def _WriteManifestForImages(self, outputPath, size, packedImageDict):
        # Create the root node.
        rootNode = Element("atlas")
        rootNode.set("width", str(size[0]))
        rootNode.set("height", str(size[1]))

        # Sort the image paths by their basename so we get constant ordering.
        sortedImagePathList = sorted(packedImageDict.keys(), key=lambda path: os.path.basename(path))
        
        # Append all image nodes.
        for imagePath in sortedImagePathList:
            packedImageData = packedImageDict[imagePath][1]
            imageNode = SubElement(rootNode, "image")
            imageNode.set("name", os.path.basename(imagePath))
            imageNode.set("x", str(packedImageData.packedBoundingBox[0]))
            imageNode.set("y", str(packedImageData.packedBoundingBox[1]))
            imageNode.set("width", str(packedImageData.packedBoundingBox[2]))
            imageNode.set("height", str(packedImageData.packedBoundingBox[3]))

        # Prettify the xml
        xmlData = tostring( rootNode )
        dom = xml.dom.minidom.parseString( xmlData )
        xmlText = dom.toprettyxml()

        # Write the xml to the output file.
        with open( outputPath, "wb" ) as file:
            file.write( xmlText )

    def Pack(self, imageFilenames, minImageSize, maxImageSize, outputImagePath, outputManifestPath, padding=2, cropColor=(0,0,0,0)):
        print "Packing %d images..." % len(imageFilenames)

        # Calculate information for each image.
        imageInfoList = self._GetImageInfo(imageFilenames)

        # Crop the images
        if cropColor is not None:
            print "Cropping images..."
            if self._CropBoundingBoxes(imageInfoList, cropColor):
                print "Cropping successful!"
            else:
                print "Cropping failed!"

        # Pack the images.
        print "Packing images..."
        imageSize = minImageSize
        packResult = False
        while (imageSize[0] <= maxImageSize[0] and imageSize[1] <= maxImageSize[1]):
            print "Packing into %dx%d image..." % imageSize
            packResult, packedImageDict = self._PackImages(imageInfoList, padding, imageSize)
            if packResult:
                print "Packing into %dx%d image successful!" % imageSize
                break
            else:
                print "Packing into %dx%d image failed!" % imageSize
                imageSize = (imageSize[0] * 2, imageSize[1] * 2)
        
        # Only continue if the packing was successful.
        if packResult:
            # Composite the images into the output image.
            print "Compositing Images to %s..." % os.path.basename(outputImagePath)
            if self._CompositePackedImages(outputImagePath, imageSize, padding, packedImageDict):
                print "Compositing successful!"
            else:
                print "Compositing failed!"

            # Write the manifest file.
            print "Writing manifest to %s..." % os.path.basename(outputManifestPath)
            self._WriteManifestForImages(outputManifestPath, imageSize, packedImageDict)
            print "Writing successful!"
        else:
            print "Failed to pack images into image of desired dimensions."

        print "Packing complete!"
