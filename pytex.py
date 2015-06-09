from PIL import Image, ImageOps
from cygon import CygonRectanglePacker
from xml.etree.cElementTree import Element, ElementTree, SubElement, tostring
import xml.dom.minidom
import os

class AtlasPacker:
    """A class for packing texture atlases"""
    
    def __init__(self):
        pass
    
    def __Lerp(self, x, max):
        return float( x ) / float( max )
    
    def __FindBBox(self, image, color=(0,0,0,0)):
        alphaTestMode = ( color[3] is 0 )
        img = image.load()
        bbox = [0,0,image.size[0],image.size[1]]
        
        #Find top
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
            
        #Find bottom
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
            
        #Find left
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
            
        #Find right
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
            image = image.crop( self.__FindBBox( image, cropColor ) )
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
                fileNode.set( "x", str( self.__Lerp( result.x + padding, size[0] ) ) )
                fileNode.set( "y", str( self.__Lerp( result.y + padding, size[1] ) ) )
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
    

if __name__ == "__main__":
    imageFilenames = []
    for filename in os.listdir("res"):
        imageFilenames.append( os.path.join( "res", filename ) )
        
    packer = AtlasPacker()
    packer.Pack( "Packed.png", ( 2048, 2048 ), ( 0,0,0,0 ), 4, imageFilenames )
