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
                print "Failed to get image info for image %s!" % os.path.basename(filepath)

        # Return the results.
        return imageInfoList

    def _CropBoundingBoxes(self, imageInfoList, cropColor):
        # Crop bounding box for each image in the list.
        for imageInfo in imageInfoList:
            try:
                # Load the image
                image = Image.open(imageInfo.path)

                # Make sure it's in RGBA format.
                if image.mode != "RGBA":
                    image = image.convert("RGBA")

                # Crop the bounding box using the image data.
                image.boundingBox = self._FindBBox(image, cropColor)
            
            except IOError:
                print "Failed to calculate crop bounding box for image %s!" % imageInfo.name

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
                packedX = self._Lerp(x + padding, size[0])
                packedY = self._Lerp(y + padding, size[1])
                packedWidth = float(imageWidth * texelWidth)
                packedHeight = float(imageHeight * texelHeight)
                packedImageDict[imageInfo.path] = (imageInfo, PackedImageInfo((x, y), [packedX, packedY, packedWidth, packedHeight]))
            else:
                # The pack failed. Destroy all results and return.
                print "Failed to pack images into image of size %s!" % str(size)
                packedImageDict.clear()
                packingResult = False
                break

        # Return the results.
        return (packingResult, packedImageDict)

    def _CompositePackedImages(self, outputFilename, size, padding, packedImageDict):
        # Create the output image.
        outImage = Image.new("RGBA", *size)

        # Composite all packed images into the output image.
        for packedImagePath, packedImageData in packedImageDict.iteritems():
            try:
                # Open the image
                image = Image.open(packedImagaData[0].path)

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
                print "Failed to composite packed image %s into output image %s!" % (packedImagePath, outputFilename)

        # Save the output image
        outImage.save(outputFilename)
    
    def Pack(self, outputFilename, size, cropColor, padding, imagePaths):
        print "Packing Images..."
        
        packer = CygonRectanglePacker( *size )
        outImage = Image.new( "RGBA", size )
        texelWidth = 1.0 / float( size[0] )
        texelHeight = 1.0 / float( size[1] )
        imgCount = 0
        maxPos = ( 0, 0 )
        rootNode = Element("atlas")
        rootNode.set( "width", str( size[0] ) )
        rootNode.set( "height", str( size[1] ) )
        for filepath in imagePaths:
            image = Image.open( filepath )
            image = image.convert( "RGBA" )
            image = image.crop( self._FindBBox( image, cropColor ) )
            image = ImageOps.expand( image, padding, 0 )
            result = packer.Pack( *image.size )
            if result is not None:
                filename = os.path.basename(filepath)
                outImage.paste( image, ( result.x, result.y ) )
                print "Packed %s at %f, %f | %f, %f | as %s" % ( filepath, result.x, result.y, image.size[0], image.size[1], filename )
                maxPos = ( max( maxPos[0], result.x + image.size[0] ), maxPos[1] )
                maxPos = ( maxPos[0], max( maxPos[1], result.y + image.size[1] ) )
                fileNode = SubElement( rootNode, "file" )
                fileNode.set( "name", filename )
                fileNode.set( "x", str( self._Lerp( result.x + padding, size[0] ) ) )
                fileNode.set( "y", str( self._Lerp( result.y + padding, size[1] ) ) )
                fileNode.set( "width", str( float( image.size[0] - (padding * 2.0) ) * texelWidth ) )
                fileNode.set( "height", str( float( image.size[1] - (padding * 2.0) ) * texelHeight ) )
                imgCount += 1
            else:
                print "Image %s Cannot Fit Into Output Image!" % filepath
                return False
        
        outImage.save( outputFilename )
        print "Packed %i Images!" % imgCount
        
        widthEfficiency =  float(maxPos[0]) / float(size[0])
        heightEfficiency =  float(maxPos[1]) / float(size[1])
        totalEfficiency = ( ( widthEfficiency + heightEfficiency ) / 2.0 ) * 100.0
        print "Packing Efficiency: %i%%" % totalEfficiency
        
        print "Writing Config..."
        root, ext = os.path.splitext( outputFilename )
        xmlPath = root + ".xml"
        
        xmlData =  tostring( rootNode )
        dom = xml.dom.minidom.parseString( xmlData )
        xmlText = dom.toprettyxml()
        with open( xmlPath, "wb" ) as file:
            file.write( xmlText )
            
        print "Done!"
        
        return True
