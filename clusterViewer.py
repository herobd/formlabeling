import sys
import cv2
import numpy as np

"""
from Tkinter import *

root = Tk()

def mouseDown_callback(event):
    frame.focus_set()
    print "clicked at", event.x, event.y

def mouseMove_callback(event):
    print "moved at", event.x, event.y

def mouseUp_callback(event):
    print "released at", event.x, event.y

def key_callback(event):
    global can,image
    print "pressed", repr(event.char)
    if (repr(event.char) == 'a'):
        can.delete(image)

can = Canvas(root, width=100, height=100)
can.bind("<Button-1>", mouseDown_callback)
can.bind("<B1-Motion>", mouseMove_callback)
can.bind("<ButtonRelease-1>", mouseUp_callback)
can.bind("<Key>", key_callback)
can.pack()

image = can.create_image((0,0),achor=TOPLEFT,image=im)

root.mainloop()

"""

MAX_SHOW=9

def fit(h,w,images,scale):
    r=0
    cols=0
    c=0
    y=0
    x=0
    yMax=0
    imIdx=0
    print 'fit images:'+str(len(images))+' scale:'+str(scale)
    p=''
    while imIdx < len(images):
        ih=images[imIdx].shape[0]*scale
        iw=images[imIdx].shape[1]*scale
        if ih>yMax:
            yMax=ih
        if cols<1:
            if x+iw<w:
                c+=1
                x+=iw+1
                imIdx+=1
                if imIdx<10:
                    p+='  '+str(imIdx)
                else:
                    p+=' '+str(imIdx)
            elif c==0:
                return -1,-1,-1
            else:
                cols=c
                c=0
                r=1
                y+=yMax+1
                yMax=0
                print p
                p=''
        else:
            if c<cols:
                c+=1 #this doesn't check width. Just draw over
                imIdx+=1
                if imIdx<10:
                    p+='  '+str(imIdx)
                else:
                    p+=' '+str(imIdx)
            else:
                c=0
                r+=1
                y+=yMax+1
                yMax=0
                print p
                p=''
    if cols==0:
        cols=c
    y+=yMax
    rows=r+1
    fitM=h-y
    print p
    print 'x: '+str(x)+' y: '+str(y)
    print 'fitM: '+str(fitM)

    return fitM, rows, cols

def display(imageDir,clusterFull,displayH, displayW):
    images=[]
    if len(clusterFull)>MAX_SHOW:
        cluster=clusterFull[:MAX_SHOW]
    else:
        cluster=clusterFull
    for imPath in cluster:
        image=cv2.imread(imageDir+imPath)
        if image is None:
            print 'could not read image '+imPath
            exit(1)
        print 'read '+imPath
        images.append(image)
    scale = 1.0
    scaleStep =0.5

    while scaleStep>0.1:
        print 'smaller '+str(scaleStep)
        while 0>fit(displayH,displayW,images,scale)[0]:
            scale*=1.0-scaleStep
        scaleStep /= 2.0
        print 'bigger '+str(scaleStep)
        while 0<fit(displayH,displayW,images,scale)[0]:
            scale*=1.0+scaleStep
        scaleStep /= 2.0
    print 'smallerF '+str(scaleStep)
    while True:
        fitM,rows,cols=fit(displayH,displayW,images,scale)
        if fitM>=0:
            break
        scale*=1.0-scaleStep

    print rows
    print cols
    imIdx=0
    x=0
    y=0
    composite=np.zeros((displayH,displayW,3),dtype=np.uint8)
    for r in range(rows):
        maxY=0
        for c in range(cols):
            shrunk = cv2.resize(images[imIdx],(0,0),None,scale,scale)
            print 'shrunk h:'+str(shrunk.shape[0])+' w:'+str(shrunk.shape[1])
            widthToDraw=shrunk.shape[1]
            if x+widthToDraw>=displayW:
                widthToDraw-=(x+widthToDraw)-displayW
            print 'wtd:'+str(widthToDraw)
            print 'r:'+str(r)+' c:'+str(c)
            composite[y:y+shrunk.shape[0], x:x+widthToDraw]=shrunk[:,0:widthToDraw]
            x+=shrunk.shape[1]+1
            #y+=shrunk.shape[0]
            if shrunk.shape[0]>maxY:
                maxY=shrunk.shape[0]
            imIdx+=1
            if imIdx>=len(images):
                break;
        y+=maxY+1
        x=0
    return composite

def clusterViewer(imageDir, clustersFile,h,w):
    displayH=int(h)
    displayW=int(w)
    if imageDir[-1]!='/':
        imageDir+='/'
    clusters=[]
    with open(clustersFile) as f:
        for line in f.readlines():
            imageFiles = line.split(',')
            cluster=[imageFile.strip() for imageFile in imageFiles]
            clusters.append(cluster)
    ret=[]
    for cluster in clusters:
        dim = display(imageDir,cluster,displayH,displayW)
        while True:
            cv2.imshow('cluster',dim)
            key = cv2.waitKey() & 0xFF
            if key == 13: #enter, good
                ret.append(cluster)
                break
            elif key == 8: #backspace, bad
                break
            elif key == 127: #del, split
                doSomething()
                break
    return ret



if len(sys.argv)!=5:
    print 'Usage: python '+sys.argv[0]+' imageDir clusters.csv height width'
    exit()
clusters = clusterViewer(sys.argv[1], sys.argv[2],sys.argv[3], sys.argv[4])
print clusters
