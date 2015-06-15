import os
import unittest
import pytex

class TestPyTex(unittest.TestCase):

    def setUp(self):
        # Gather a list of filenames to use.
        self._imageFilenames = []
        for filename in os.listdir("res"):
            self._imageFilenames.append(os.path.join( "res", filename ))

        # Create a packer object.
        self._packer = pytex.AtlasPacker()

        # Set up some standard options.
        self._imageSize = (2048, 2048)
        self._padding = 2
        self._cropColor = (0, 0, 0, 0)
        self._outputImageName = "Test.png"
        self._outputManifestName = "Test.xml"

    def tearDown(self):
        # Nullify all variables.
        self._imageFilenames = None
        self._packer = None

    def test_GetImageInfo(self):
        for imageInfo in self._packer._GetImageInfo(self._imageFilenames):
            self.assertTrue(imageInfo.path in self._imageFilenames, "Missing ImageInfo for filename %s!" % imageInfo.path)

    def test_CropBoundingBoxes(self):
        imageInfoList = self._packer._GetImageInfo(self._imageFilenames)
        self.assertTrue(self._packer._CropBoundingBoxes(imageInfoList, self._cropColor), "Failed to calculate crop bounding boxes!")

    def test_PackImages(self):
        imageInfoList = self._packer._GetImageInfo(self._imageFilenames)
        self._packer._CropBoundingBoxes(imageInfoList, self._cropColor)
        packingResult = self._packer._PackImages(imageInfoList, self._padding, self._imageSize)[0]
        self.assertTrue(packingResult, "Failed to pack images into atlas!")

    def test_CompositePackedImages(self):
        imageInfoList = self._packer._GetImageInfo(self._imageFilenames)
        self._packer._CropBoundingBoxes(imageInfoList, self._cropColor)
        packedImageDict = self._packer._PackImages(imageInfoList, self._padding, self._imageSize)[1]
        compositeResult = self._packer._CompositePackedImages(self._outputImageName, self._imageSize, self._padding, packedImageDict)
        self.assertTrue(compositeResult, "Failed to composite images into atlas image!")

    def test_WriteManifestForImages(self):
        imageInfoList = self._packer._GetImageInfo(self._imageFilenames)
        self._packer._CropBoundingBoxes(imageInfoList, self._cropColor)
        packedImageDict = self._packer._PackImages(imageInfoList, self._padding, self._imageSize)[1]
        self._packer._WriteManifestForImages(self._outputManifestName, self._imageSize, "uv", packedImageDict)
        self._packer._WriteManifestForImages(self._outputManifestName, self._imageSize, "pixel", packedImageDict) 

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPyTex)
    unittest.TextTestRunner(verbosity=2).run(suite)
