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
    if 'horzLinks' in read:
        horzLinks=read['horzLinks']
    else:
        return True, 'no horz links'
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

            print((path+' :: '+str(height)))

            if height>width and width>26 and height>40:
                #print('Tall box {}'.format(points))
                return True, 'Tall box {}'.format(points)
            if height>150:
                return True, 'Very tall box {}'.format(points)

            if height*width<50:
                #print('Small box {}'.format(points))

                return True, 'Small box {}'.format(points)
            
            if rot<math.pi/4 and rot>-math.pi/4:
                sumUpright+=1
            countRot+=1

    if sumUpright/float(countRot)<0.45:
        #print('Rotation')
        return True, 'Rotation'

    for link in horzLinks:
        existsPair=False
        for id1 in link:
            for id2 in link:
                #if (id1,id2) in pairs or (id2,id1) in pairs or (id1,id2) in samePairs or (id2,id1) in samePairs:
                for p in pairs+samePairs:
                    if p[0]==id1 and p[1]==id2 or p[0]==id2 and p[1]==id1:
                        existsPair=True
                        break
                if existsPair:
                    break
            if existsPair:
                break
        if not existsPair:
            #print('horz link without a pair')
            return True, 'horz link without a pair: {} :: {} ::s {}'.format(link,pairs,samePairs)

    return False, 'none'
