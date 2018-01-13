import sys
import cv2

def labelImage(imagePath,displayH,displayW):
    image = cv2.imread(imagePath)
    if image is None:
        print 'cannot open image '+imagePath
        exit(1)
    scale = min(displayH/image.shape[0],(displayW-TOOL_WIDTH)/image.shape[1])
    cv2.resize(image,(0,0),image,scale,scale)
    

    return textBBs, fieldBBs, pairing
