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
        if '-m' == p.mode[-2:]: #we dragged to make a box
            p.mode=p.mode[:-2] #make state readable
            if abs((p.startX-p.endX)*(p.startY-p.endY))>10: #the box is "big enough"
                didPair=None #for storing auto-pair for undo/action stack

                #auto-pair to selected
                if 'text' in p.mode and 'field' in p.selected:
                    p.pairing.append((p.textBBsCurId,p.selectedId))
                    didPair=[(p.textBBsCurId,p.selectedId)]
                elif 'field' in p.mode and 'text' in p.selected:
                    p.pairing.append((p.selectedId,p.fieldBBsCurId))
                    didPair=[(p.selectedId,p.fieldBBsCurId)]

                if p.mode=='text':
                    p.textBBs[p.textBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),0)
                    p.actionStack.append(('add-text',p.textBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),0,didPair))
                    p.undoStack=[]
                    p.selectedId=p.textBBsCurId
                    p.selected='text'
                    p.textBBsCurId+=1
                elif p.mode=='textP':
                    p.textBBs[p.textBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),1)
                    p.actionStack.append(('add-text',p.textBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),1,didPair))
                    p.undoStack=[]
                    p.selectedId=p.textBBsCurId
                    p.selected='text'
                    p.textBBsCurId+=1
                elif p.mode=='field':
                    p.fieldBBs[p.fieldBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),0)
                    p.actionStack.append(('add-field',p.fieldBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),0,didPair))
                    p.undoStack=[]
                    p.selectedId=p.fieldBBsCurId
                    p.selected='field'
                    p.fieldBBsCurId+=1
                elif p.mode=='fieldP':
                    p.fieldBBs[p.fieldBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),1)
                    p.actionStack.append(('add-field',p.fieldBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),1,didPair))
                    p.undoStack=[]
                    p.selectedId=p.fieldBBsCurId
                    p.selected='field'
                    p.fieldBBsCurId+=1
                elif p.mode=='fieldCheckBox':
                    p.fieldBBs[p.fieldBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),2)
                    p.actionStack.append(('add-field',p.fieldBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),2,didPair))
                    p.undoStack=[]
                    p.selectedId=p.fieldBBsCurId
                    p.selected='field'
                    p.fieldBBsCurId+=1
            draw(p)
        elif '-tl' == p.mode[-3:]:#we dragged the top-left corner to resize the selected box
            p.mode=p.mode[:-3]
            bbs = None
            if p.selected=='field':
                bbs = p.fieldBBs
            elif p.selected=='text':
                bbs = p.textBBs
            if bbs is not None:
                p.actionStack.append(('drag-'+p.selected,p.selectedId,bbs[p.selectedId][0],bbs[p.selectedId][1],bbs[p.selectedId][2],bbs[p.selectedId][3]))
                bbs[p.selectedId] = (p.endX,p.endY,bbs[p.selectedId][2],bbs[p.selectedId][3],bbs[p.selectedId][4])
                draw(p)
        elif '-bl' == p.mode[-3:]:#we dragged the top-left corner to resize the selected box
            p.mode=p.mode[:-3]
            bbs = None
            if p.selected=='field':
                bbs = p.fieldBBs
            elif p.selected=='text':
                bbs = p.textBBs
            if bbs is not None:
                p.actionStack.append(('drag-'+p.selected,p.selectedId,bbs[p.selectedId][0],bbs[p.selectedId][1],bbs[p.selectedId][2],bbs[p.selectedId][3]))
                bbs[p.selectedId] = (p.endX,bbs[p.selectedId][1],bbs[p.selectedId][2],p.endY,bbs[p.selectedId][4])
                draw(p)
        elif '-tr' == p.mode[-3:]:#we dragged the top-left corner to resize the selected box
            p.mode=p.mode[:-3]
            bbs = None
            if p.selected=='field':
                bbs = p.fieldBBs
            elif p.selected=='text':
                bbs = p.textBBs
            if bbs is not None:
                p.actionStack.append(('drag-'+p.selected,p.selectedId,bbs[p.selectedId][0],bbs[p.selectedId][1],bbs[p.selectedId][2],bbs[p.selectedId][3]))
                bbs[p.selectedId] = (bbs[p.selectedId][0],p.endY,p.endX,bbs[p.selectedId][3],bbs[p.selectedId][4])
                draw(p)
        elif '-br' == p.mode[-3:]:#we dragged the top-left corner to resize the selected box
            p.mode=p.mode[:-3]
            bbs = None
            if p.selected=='field':
                bbs = p.fieldBBs
            elif p.selected=='text':
                bbs = p.textBBs
            if bbs is not None:
                p.actionStack.append(('drag-'+p.selected,p.selectedId,bbs[p.selectedId][0],bbs[p.selectedId][1],bbs[p.selectedId][2],bbs[p.selectedId][3]))
                bbs[p.selectedId] = (bbs[p.selectedId][0],bbs[p.selectedId][1],p.endX,p.endY,bbs[p.selectedId][4])
                draw(p)
        else:
            if '-d' == p.mode[-2:]:
                p.mode=p.mode[:-2]

            if p.mode=='delete': #first check for pairing lines (we can only delete them)
                for index,(text,field) in enumerate(p.pairing):
                    #if within bounds of line and within distance from it
                    x1=(p.textBBs[text][0]+p.textBBs[text][2])/2
                    y1=(p.textBBs[text][1]+p.textBBs[text][3])/2
                    x2=(p.fieldBBs[field][0]+p.fieldBBs[field][2])/2
                    y2=(p.fieldBBs[field][1]+p.fieldBBs[field][3])/2

                    if x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/math.sqrt(pow(y2-y1,2.0) + pow(x2-x1,2.0)) < 3.5:
                        #delete the pairing
                        p.actionStack.append(('remove-pairing',text,field))
                        p.undoStack=[]
                        del p.pairing[index]
                        draw(p)
                        return
            #then bbs
            for id, (startX,startY,endX,endY,para) in p.textBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if p.mode=='delete':
                        #delete the text BB
                        pairs=[]#pairs this BB is part of
                        for pair in p.pairing:
                            if id==pair[0]:
                                pairs.append(pair)
                        for pair in pairs:
                            p.pairing.remove(pair)
                        p.actionStack.append(('remove-text',id,startX,startY,endX,endY,para,pairs))
                        p.undoStack=[]
                        del p.textBBs[id]
                        if p.selected=='text' and p.selectedId==id:
                            p.selected='none'
                    else:
                        #pair to prev selected?
                        if p.selected=='field' and (id,p.selectedId) not in p.pairing:
                            p.pairing.append((id,p.selectedId))
                            p.actionStack.append(('add-pairing',id,p.selectedId))
                            p.undoStack=[]
                        #select the text BB
                        p.selectedId=id
                        p.selected='text'
                    draw(p)
                    return

            for id, (startX,startY,endX,endY,para) in p.fieldBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if p.mode=='delete':
                        #delete the field BB
                        pairs=[]#pairs this BB is part of
                        for pair in p.pairing:
                            if id==pair[1]:
                                pairs.append(pair)
                        for pair in pairs:
                            p.pairing.remove(pair)
                        p.actionStack.append(('remove-field',id,startX,startY,endX,endY,para,pairs))
                        p.undoStack=[]
                        del p.fieldBBs[id]
                        if p.selected=='field' and p.selectedId==id:
                            p.selected='none'
                    else:
                        #pair to prev selected?
                        if p.selected=='text' and (p.selectedId,id) not in p.pairing:
                            p.pairing.append((p.selectedId,id))
                            p.actionStack.append(('add-pairing',p.selectedId,id))
                            p.undoStack=[]
                        #select the field BB
                        p.selectedId=id
                        p.selected='field'
                    draw(p)
                    return

            if p.selected!='none':
                #print 'deselected'
                p.selected='none'
                draw(p)

            
    elif event == cv2.EVENT_MOUSEMOVE:
        #moving only matters if the button is down and we've moved "enough"
        bbs = None
        if p.selected == 'field':
            bbs = p.fieldBBs
        elif p.selected == 'text':
            bbs = p.textBBs
        if '-d' == p.mode[-2:] and math.sqrt(pow(x-p.startX,2)+pow(y-p.startY,2))>2:
            if bbs is not None and p.startX>bbs[p.selectedId][0] and p.startX<bbs[p.selectedId][2] and p.startY>bbs[p.selectedId][1] and p.startY<bbs[p.selectedId][3]:
                #we are going to adjust the selected BB, but how?
                w=bbs[p.selectedId][2]-bbs[p.selectedId][0] +1
                h=bbs[p.selectedId][3]-bbs[p.selectedId][1] +1
                leftBoundary = bbs[p.selectedId][0] + 0.333*w
                rightBoundary = bbs[p.selectedId][0] + 0.666*w
                topBoundary = bbs[p.selectedId][1] + 0.333*h
                bottomBoundary = bbs[p.selectedId][1] + 0.666*h
                
                if p.startX<leftBoundary and p.startY<topBoundary:#top-left corner
                    p.mode = p.mode[:-1]+'tl'
                elif p.startX<leftBoundary and p.startY>bottomBoundary:#bot-left corner
                    p.mode = p.mode[:-1]+'bl'
                elif p.startX>rightBoundary and p.startY<topBoundary:#top-right corner
                    p.mode = p.mode[:-1]+'tr'
                elif p.startX>rightBoundary and p.startY>bottomBoundary:#bot-right corner
                    p.mode = p.mode[:-1]+'br'
                #elif p.startX<leftBoundary:#left
                #    p.mode = p.mode[:-1]+'l'
                #elif p.startX>rightBoundary:#right
                #    p.mode = p.mode[:-1]+'r'
                #elif p.startY<topBoundary:#top
                #    p.mode = p.mode[:-1]+'t'
                #elif p.startY<bottomBoundary:#bot
                #    p.mode = p.mode[:-1]+'b'
            else:
                p.mode = p.mode[:-1]+'m'
        if '-m' == p.mode[-2:]:
            p.endX=x
            p.endY=y
            draw(p)
        elif (('-tl' == p.mode[-3:] and  x<bbs[p.selectedId][2] and y<bbs[p.selectedId][3]) or
              ('-bl' == p.mode[-3:] and  x<bbs[p.selectedId][2] and y>bbs[p.selectedId][1]) or
              ('-tr' == p.mode[-3:] and  x>bbs[p.selectedId][0] and y<bbs[p.selectedId][3]) or
              ('-br' == p.mode[-3:] and  x>bbs[p.selectedId][0] and y>bbs[p.selectedId][1]) or
              ('-l' == p.mode[-3:] and  x<bbs[p.selectedId][2]) or
              ('-r' == p.mode[-3:] and  x>bbs[p.selectedId][0]) or
              ('-t' == p.mode[-3:] and  y<bbs[p.selectedId][3]) or
              ('-b' == p.mode[-3:] and  y>bbs[p.selectedId][1])):
            p.endX=x
            p.endY=y
            draw(p)

class Params:
    mode='none'
    textBBs={}
    textBBsCurId=0
    fieldBBs={}
    fieldBBsCurId=0
    pairing=[]
    image=None
    displayImage=None
    startX=-1
    startY=-1
    endX=-1
    endY=-1
    actionStack=[]
    undoStack=[]
    selectedId=-1
    selected='none'

def undo(p):
    if len(p.actionStack)>0:
        action = p.actionStack.pop()
        action = undoAction(p,action)

        p.undoStack.append(action)
        draw(p)

def redo(p):
    if len(p.undoStack)>0:
        action = p.undoStack.pop()
        action = undoAction(p,action)

        p.actionStack.append(action)
        draw(p)

def undoAction(p,action):
    if action[0] == 'add-pairing':
        p.pairing.remove((action[1],action[2]))
        return ('remove-pairing',action[1],action[2])
    elif action[0] == 'remove-pairing':
        p.pairing.append((action[1],action[2]))
        return ('add-pairing',action[1],action[2])
    elif action[0] == 'add-text':
        label,id,startX,startY,endX,endY,para,pairs = action
        del p.textBBs[id]
        if pairs is not None:
            for pair in pairs:
                p.pairing.remove(pair)
        if p.selected=='text' and p.selectedId==id:
            p.selected='none'
        return ('remove-text',id,startX,startY,endX,endY,para,pairs)
    elif action[0] == 'remove-text':
        label,id,startX,startY,endX,endY,para,pairs = action
        p.textBBs[id]=(startX,startY,endX,endY,para)
        if pairs is not None:
            for pair in pairs:
                p.pairing.append(pair)
        return ('add-text',id,startX,startY,endX,endY,para,pairs)
    elif action[0] == 'add-field':
        label,id,startX,startY,endX,endY,para,pairs = action
        del p.fieldBBs[id]
        if pairs is not None:
            for pair in pairs:
                p.pairing.remove(pair)
        if p.selected=='field' and p.selectedId==id:
            p.selected='none'
        return ('remove-field',id,startX,startY,endX,endY,para,pairs)
    elif action[0] == 'remove-field':
        label,id,startX,startY,endX,endY,para,pairs = action
        p.fieldBBs[id]=(startX,startY,endX,endY,para)
        if pairs is not None:
            for pair in pairs:
                p.pairing.append(pair)
        return ('add-field',id,startX,startY,endX,endY,para,pairs)
    elif action[0] == 'drag-field':
        label,id,startX,startY,endX,endY = action
        toRet = (label,id,p.fieldBBs[id][0],p.fieldBBs[id][1],p.fieldBBs[id][2],p.fieldBBs[id][3])
        p.fieldBBs[id] = (startX,startY,endX,endY,p.fieldBBs[id][4])
        return toRet
    elif action[0] == 'drag-text':
        label,id,startX,startY,endX,endY = action
        toRet = (label,id,p.textBBs[id][0],p.textBBs[id][1],p.textBBs[id][2],p.textBBs[id][3])
        p.textBBs[id] = (startX,startY,endX,endY,p.textBBs[id][4])
        return toRet
    else:
        print 'Unimplemented action: '+action[0]

def draw(p):
    p.displayImage[0:p.image.shape[0], 0:p.image.shape[1]] = p.image
    for id, (startX,startY,endX,endY,para) in p.textBBs.iteritems():
        if para==1:
            g=150
        elif para==2:
            g=240
        else:
            g=0
        cv2.rectangle(p.displayImage,(startX,startY),(endX,endY),(255,g,0),1)

    for id, (startX,startY,endX,endY,para) in p.fieldBBs.iteritems():
        if para==1:
            g=120
        elif para==2:
            g=240
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
        startX,startY,endX,endY,para = p.textBBs[p.selectedId]
        if p.mode[-3:]=='-tl':
            cv2.rectangle(p.displayImage,(p.endX,p.endY),(max(startX,endX),max(startY,endY)),(255,240,100),1)
        elif p.mode[-3:]=='-tr':
            cv2.rectangle(p.displayImage,(startX,p.endY),(p.endX,endY),(255,240,100),1)
        elif p.mode[-3:]=='-bl':
            cv2.rectangle(p.displayImage,(p.endX,startY),(endX,p.endY),(255,240,100),1)
        elif p.mode[-3:]=='-br':
            cv2.rectangle(p.displayImage,(startX,startY),(p.endX,p.endY),(255,240,100),1)
        cv2.rectangle(p.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)
    elif p.selected == 'field':
        startX,startY,endX,endY,para = p.fieldBBs[p.selectedId]
        if p.mode[-3:]=='-tl':
            cv2.rectangle(p.displayImage,(p.endX,p.endY),(max(startX,endX),max(startY,endY)),(120,255,255),1)
        elif p.mode[-3:]=='-tr':
            cv2.rectangle(p.displayImage,(startX,p.endY),(p.endX,endY),(120,255,255),1)
        elif p.mode[-3:]=='-bl':
            cv2.rectangle(p.displayImage,(p.endX,startY),(endX,p.endY),(120,255,255),1)
        elif p.mode[-3:]=='-br':
            cv2.rectangle(p.displayImage,(startX,startY),(p.endX,p.endY),(120,255,255),1)
        cv2.rectangle(p.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)

    if p.mode[-2:]=='-m':
        if 'textP' in p.mode:
            color=(255,150,0)
        elif 'text' in p.mode:
            color=(255,0,0)
        elif 'fieldP' in p.mode:
            color=(0,120,255)
        elif 'fieldCheckBox' in p.mode:
            color=(0,200,255)
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

    #fieldP
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(0,120,255)
    if p.mode=='fieldP':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'4:field para',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #fieldCheckBox
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(0,220,255)
    if p.mode=='fieldCheckBox':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'5:check-box',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #delete
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(240,240,240)
    if p.mode=='delete':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[0]-TOOL_WIDTH+1,y),(p.displayImage.shape[0]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'6:delete',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #undo
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(160,160,160)
    cv2.putText(p.displayImage,'7:undo',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #redo
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(190,190,190)
    cv2.putText(p.displayImage,'8:redo',(p.displayImage.shape[0]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
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
            if p.mode != 'fieldCheckBox':
                p.mode='fieldCheckBox'
                drawToolbar(p)
        elif key==54: #6
            if p.mode != 'delete':
                p.mode='delete'
                drawToolbar(p)
        elif key==55 or key==65: #7 or ~ undo
            undo(p)
        elif key==56: #8 undo
            redo(p)


    idToIdxText={}
    textBBs=[]
    for id, (startX,startY,endX,endY,para) in p.textBBs.iteritems():
        idToIdxText[id]=len(textBBs)
        textBBs.append((int(round(startX/scale)),int(round(startY/scale)),int(round(endX/scale)),int(round(endY/scale)),para))
    idToIdxField={}
    fieldBBs=[]
    for id, (startX,startY,endX,endY,para) in p.fieldBBs.iteritems():
        idToIdxField[id]=len(fieldBBs)
        fieldBBs.append((int(round(startX/scale)),int(round(startY/scale)),int(round(endX/scale)),int(round(endY/scale)),para))
    pairing=[]
    for text,field in p.pairing:
        pairing.append((idToIdxText[text],idToIdxField[field]))

    return textBBs, fieldBBs, pairing

print labelImage(sys.argv[1],int(sys.argv[2]),int(sys.argv[2]))
