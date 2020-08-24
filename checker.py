import json
import math

def checkProblem(path):
    with open(path) as f:
        read = json.load(f)
    texts=read['textBBs']
    fields=read['fieldBBs']
    pairs=read['pairs']
    samePairs=read['samePairs']
    groups=read['groups']
    reasons=[]
    if 'horzLinks' in read:
        horzLinks=read['horzLinks']
    else:
        #return True, 'no horz links'
        reasons.append('no horz links')
    if 'page_corners' in read and 'actualPage_corners' in read:
        page_corners=read['page_corners']
        page_cornersActual=read['actualPage_corners']
    if 'labelTime' in read:
        labelTime = read['labelTime']
    else:
        labelTime = None
    if 'checkedBy' in read:
        checkedBy = read['checkedBy']


    #tall BBs
    countRot=0
    sumUpright=0
    for bb in texts+fields:
        typ = bb['type']
        if typ!='fieldRegion' and typ!='fieldCol' and typ!='fieldRow' and typ!='graphic':
            points = bb['poly_points']
            tlX, tlY = points[0]
            trX, trY = points[1]
            brX, brY = points[2]
            blX, blY = points[3]


            lX = (tlX+blX)/2.0
            lY = (tlY+blY)/2.0
            rX = (trX+brX)/2.0
            rY = (trY+brY)/2.0
            d=math.sqrt((lX-rX)**2 + (lY-rY)**2)

            hl = ((tlX-lX)*-(rY-lY) + (tlY-lY)*(rX-lX))/d #projection of half-left edge onto transpose horz run
            hr = ((brX-rX)*-(lY-rY) + (brY-rY)*(lX-rX))/d #projection of half-right edge onto transpose horz run
            h = (hl+hr)/2.0

            cX = (lX+rX)/2.0
            cY = (lY+rY)/2.0
            rot = math.atan2((rY-lY),rX-lX)
            height = abs(h)    #this is half height
            width = d/2.0 

            #print((path+' :: '+str(height)))
            #if read['imageFilename']=='004191670_00347.jpg':
            #    print(bb)
            #    print('rot: {}, w: {}, h: {}, h/w: {}'.format(rot,width,height,height/width))

            if height/width>3 and width>26 and height>40:
                #print('inline Tall box1 {}'.format(points))
                #return True, 'Tall box {}'.format(points)
                reasons.append('Tall box {}'.format(points))
            elif height/width>5 and width>1 and height>1:
                #print('inline Tall box2 {}'.format(points))
                #return True, 'Tall box {}'.format(points)
                reasons.append('Tall box {}'.format(points))
            elif height>150 and height/width>0.9:
                #return True, 'Very tall box {}'.format(points)
                reasons.append('Very tall box {}'.format(points))

            elif height*width<50:
                #print('Small box {}'.format(points))

                #return True, 'Small box {}'.format(points)
                reasons.append('Small box {}'.format(points))
            
            if rot<math.pi/4 and rot>-math.pi/4:
                sumUpright+=1
            countRot+=1

    if sumUpright/float(countRot)<0.45:
        #print('Rotation')
        #return True, 'Rotation'
        reasons.append('Rotation')

    #for link in horzLinks:
    #    existsPair=False
    #    for id1 in link:
    #        for id2 in link:
    #            #if (id1,id2) in pairs or (id2,id1) in pairs or (id1,id2) in samePairs or (id2,id1) in samePairs:
    #            for p in pairs+samePairs:
    #                if p[0]==id1 and p[1]==id2 or p[0]==id2 and p[1]==id1:
    #                    existsPair=True
    #                    break
    #            if existsPair:
    #                break
    #        if existsPair:
    #            break
    #    if not existsPair:
    #        #print('horz link without a pair')
    #        #return True, 'horz link without a pair: {} :: {} ::s {}'.format(link,pairs,samePairs)
    #        reasons.append('horz link without a pair: {} :: {} ::s {}'.format(link,pairs,samePairs))

    #print(len(reasons))
    return len(reasons)>0, reasons
