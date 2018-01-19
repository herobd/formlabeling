import sys
import cv2
import numpy as np
import math

TOOL_WIDTH=240
toolH=40

def clicker(event, x, y, flags, p):
    #image,displayImage,mode,textBBs,fieldBBs,pairing = param

    if event == cv2.EVENT_LBUTTONDOWN:
        if p.mode!='none' and p.mode!='delete':
            p.mode+='-d'
            p.startX=x
            p.startY=y
    elif event == cv2.EVENT_LBUTTONUP:
        if '-m' == p.mode[-2:]:
            p.mode=p.mode[:-2]
            if abs((p.startX-p.endX)*(p.startY-p.endY))>10:
                didPair=None
                if 'text' in p.mode and 'field' in p.selected:
                    p.pairing.append((len(p.textBBs),p.selectedIdx))
                    didPair=(len(p.textBBs),p.selectedIdx)
                elif 'field' in p.mode and 'text' in p.selected:
                    p.pairing.append((p.selectedIdx,len(p.fieldBBs)))
                    didPair=(p.selectedIdx,len(p.fieldBBs))

                if p.mode=='text':
                    p.textBBs.append((p.startX,p.startY,p.endX,p.endY,0))
                    p.actionStack.append(('append-text',p.startX,p.startY,p.endX,p.endY,0,didPair))
                    p.selectedIdx=len(p.textBBs)-1
                    p.selected='text'
                elif p.mode=='textP':
                    p.textBBs.append((p.startX,p.startY,p.endX,p.endY,1))
                    p.actionStack.append(('append-textP',p.startX,p.startY,p.endX,p.endY,1,didPair))
                    p.selectedIdx=len(p.textBBs)-1
                    p.selected='text'
                elif p.mode=='field':
                    p.fieldBBs.append((p.startX,p.startY,p.endX,p.endY,0))
                    p.actionStack.append(('append-field',p.startX,p.startY,p.endX,p.endY,0,didPair))
                    p.selectedIdx=len(p.fieldBBs)-1
                    p.selected='field'
                elif p.mode=='fieldP':
                    p.fieldBBs.append((p.startX,p.startY,p.endX,p.endY,1))
                    p.actionStack.append(('append-fieldP',p.startX,p.startY,p.endX,p.endY,1,didPair))
                    p.selectedIdx=len(p.fieldBBs)-1
                    p.selected='field'
            draw(p)
        else:
            if '-d' == p.mode[-2:]:
                p.mode=p.mode[:-2]

            if p.mode=='delete':
                for index,(text,field) in enumerate(p.pairing):
                    #if within bounds of line and within distance from it
                    x1=(p.textBBs[text][0]+p.textBBs[text][2])/2
                    y1=(p.textBBs[text][1]+p.textBBs[text][3])/2
                    x2=(p.fieldBBs[field][0]+p.fieldBBs[field][2])/2
                    y2=(p.fieldBBs[field][1]+p.fieldBBs[field][3])/2

                    if x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/math.sqrt(pow(y2-y1,2.0) + pow(x2-x1,2.0)) < 3.5:
                        p.actionStack.append(('remove-pairing',text,field))
                        del p.pairing[index]
                        draw(p)
                        return

            for index, (startX,startY,endX,endY,para) in enumerate(p.textBBs):
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if p.mode=='delete':
                        #TODO populate pairs and delete them too
                        p.actionStack.append(('remove-text',startX,startY,endX,endY,para,pairs))
                        del p.textBBs[index]
                        if p.selected=='text' and p.selectedIdx==index:
                            p.selected='none'
                    else:
                        if p.selected=='field' and (index,p.selectedIdx) not in p.pairing:
                            p.pairing.append((index,p.selectedIdx))
                            p.actionStack.append(('append-pairing',index,p.selectedIdx))
                        p.selectedIdx=index
                        p.selected='text'
                    draw(p)
                    return

            for index, (startX,startY,endX,endY,para) in enumerate(p.fieldBBs):
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if p.mode=='delete':
                        #TODO populate pairs and delete them too
                        p.actionStack.append(('remove-field',startX,startY,endX,endY,para,pairs))
                        del p.textBBs[index]
                        if p.selected=='field' and p.selectedIdx==index:
                            p.selected='none'
                    else:
                        if p.selected=='text' and (p.selectedIdx,index) not in p.pairing:
                            p.pairing.append((p.selectedIdx,index))
                            p.actionStack.append(('append-pairing',p.selectedIdx,index))
                        p.selectedIdx=index
                        p.selected='field'
                    draw(p)
                    return

            
    elif event == cv2.EVENT_MOUSEMOVE:
        if '-d' == p.mode[-2:] and math.sqrt(pow(x-p.startX,2)+pow(y-p.startY,2))>2:
            p.mode = p.mode[:-1]+'m'
        if '-m' == p.mode[-2:]:
            p.endX=x
            p.endY=y
            draw(p)

class Params:
    mode='none'
    textBBs=[]
    fieldBBs=[]
    pairing=[]
    image=None
    displayImage=None
    startX=-1
    startY=-1
    endX=-1
    endY=-1
    actionStack=[]
    undoStack=[]
    selectedIdx=-1
    selected='none'

def draw(p):
    p.displayImage[0:p.image.shape[0], 0:p.image.shape[1]] = p.image
    for startX,startY,endX,endY,para in p.textBBs:
        if para:
            g=150
        else:
            g=0
        cv2.rectangle(p.displayImage,(startX,startY),(endX,endY),(255,g,0),1)

    for startX,startY,endX,endY,para in p.fieldBBs:
        if para:
            g=120
        else:
            g=0
        cv2.rectangle(p.displayImage,(startX,startY),(endX,endY),(0,g,255),1)

    for text,field in p.pairing:
        x1=(p.textBBs[text][0]+p.textBBs[text][2])/2
        y1=(p.textBBs[text][1]+p.textBBs[text][3])/2
        x2=(p.fieldBBs[field][0]+p.fieldBBs[field][2])/2
        y2=(p.fieldBBs[field][1]+p.fieldBBs[field][3])/2
        cv2.line(p.displayImage,(x1,y1),(x2,y2),(0,255,0),1)

    if p.selected == 'text':
        startX,startY,endX,endY,para = p.textBBs[p.selectedIdx]
        cv2.rectangle(p.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)
    elif p.selected == 'field':
        startX,startY,endX,endY,para = p.fieldBBs[p.selectedIdx]
        cv2.rectangle(p.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)

    if p.mode[-2:]=='-m':
        if 'textP' in p.mode:
            color=(255,150,0)
        elif 'text' in p.mode:
            color=(255,0,0)
        elif 'fieldP' in p.mode:
            color=(0,120,255)
        elif 'field' in p.mode:
            color=(0,0,255)
        cv2.rectangle(p.displayImage,(p.startX,p.startY),(p.endX,p.endY),color,1)

    cv2.imshow("labeler",p.displayImage)

def drawToolbar(p):
    p.displayImage[0:,-TOOL_WIDTH:]=(140,140,140)

    y=0

    #text
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(255,0,0)
    if p.mode=='text':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'1:text',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #textP
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(255,150,0)
    if p.mode=='textP':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'2:text para',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #field
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(0,0,255)
    if p.mode=='field':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'3:field',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #field
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(0,120,255)
    if p.mode=='fieldP':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'4:field para',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #delete
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(240,240,240)
    if p.mode=='delete':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'5:delete',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    cv2.imshow("labeler",p.displayImage)

def labelImage(imagePath,displayH,displayW):
    p = Params()
    p.displayImage = np.zeros((displayH,displayW,3),dtype=np.uint8)
    p.image = cv2.imread(imagePath)
    if p.image is None:
        print 'cannot open image '+imagePath
        exit(1)
    scale = min(float(displayH)/p.image.shape[0],float(displayW-TOOL_WIDTH)/p.image.shape[1])
    p.image=cv2.resize(p.image,(0,0),None,scale,scale)
    


    cv2.namedWindow("labeler")
    cv2.setMouseCallback("labeler", clicker,param=p)
    draw(p)
    drawToolbar(p)
    #cv2.imshow('labeler',p.displayImage)

    while True:
        key = cv2.waitKey(33) & 0xFF
        if key==27: #esc
            break
        elif key==49: #1
            if p.mode != 'text':
                p.mode='text'
                drawToolbar(p)
        elif key==50: #2
            if p.mode != 'textP':
                p.mode='textP'
                drawToolbar(p)
        elif key==51: #3
            if p.mode != 'field':
                p.mode='field'
                drawToolbar(p)
        elif key==52: #4
            if p.mode != 'fieldP':
                p.mode='fieldP'
                drawToolbar(p)
        elif key==53: #5
            if p.mode != 'delete':
                p.mode='delete'
                drawToolbar(p)

    #TODO scale?
    print 'TODO scale'
    return textBBs, fieldBBs, pairing

print labelImage(sys.argv[1],int(sys.argv[2]),int(sys.argv[2]))
