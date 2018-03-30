import sys
import cv2
import numpy as np
import math
import json

TOOL_WIDTH=240
toolH=40
colorMap = {'text':(255,0,0), 'textP':(255,150,0), 'textMinor':(205,190,100), 'textInst':(255,210,190), 'textNumber':(100,160,0), 'fieldCircle':(210,190,255), 'field':(0,0,255), 'fieldP':(0,120,255), 'fieldCheckBox':(0,220,255), 'graphic':(250,105,255)}
codeMap = {'text':0, 'textP':1, 'textMinor':2, 'textInst':3, 'textNumber':4, 'fieldCircle':5, 'field':6, 'fieldP':7, 'fieldCheckBox':8, 'graphic':9}
RcodeMap = {v: k for k, v in codeMap.iteritems()}
keyMap = {'text':49,#1
          'textP':50,#2
          'textMinor':51,#3
          'textInst':52,#4
          'textNumber':53,#5
          'field':113,#Q
          'fieldP':119,#W
          'fieldCheckBox':101,#E
          'fieldCircle':114,#R
          'graphic':116 #T
          }
RkeyMap = {v: k for k, v in keyMap.iteritems()}
toolMap = {'text':'1:text/label', 'textP':'2:text para', 'textMinor':'3:minor label', 'textInst':'4:instructions', 'textNumber':'5:enumeration (#)', 'fieldCircle':'R:to be circled', 'field':'Q:field', 'fieldP':'W:field para', 'fieldCheckBox':'E:check-box', 'graphic':'T:graphic'}
modes = ['text', 'textP', 'textMinor', 'textInst', 'textNumber', 'field', 'fieldP', 'fieldCheckBox', 'fieldCircle', 'graphic']

def clicker(event, x, y, flags, p):
    #image,displayImage,mode,textBBs,fieldBBs,pairing = param

    if event == cv2.EVENT_LBUTTONDOWN:
        if p.mode!='delete':
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

                code = codeMap[p.mode]
                if p.mode[:4]=='text':
                    p.textBBs[p.textBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),code,0)
                    p.actionStack.append(('add-text',p.textBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),code,0,didPair))
                    p.undoStack=[]
                    p.selectedId=p.textBBsCurId
                    p.selected='text'
                    p.textBBsCurId+=1
                else: #p.mode[:5]=='field':
                    p.fieldBBs[p.fieldBBsCurId]=(min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),code,0)
                    p.actionStack.append(('add-field',p.fieldBBsCurId,min(p.startX,p.endX),min(p.startY,p.endY),max(p.startX,p.endX),max(p.startY,p.endY),code,0,didPair))
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
                bbs[p.selectedId] = (p.endX,p.endY,bbs[p.selectedId][2],bbs[p.selectedId][3],bbs[p.selectedId][4],bbs[p.selectedId][5])
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
                bbs[p.selectedId] = (p.endX,bbs[p.selectedId][1],bbs[p.selectedId][2],p.endY,bbs[p.selectedId][4],bbs[p.selectedId][5])
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
                bbs[p.selectedId] = (bbs[p.selectedId][0],p.endY,p.endX,bbs[p.selectedId][3],bbs[p.selectedId][4],bbs[p.selectedId][5])
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
                bbs[p.selectedId] = (bbs[p.selectedId][0],bbs[p.selectedId][1],p.endX,p.endY,bbs[p.selectedId][4],bbs[p.selectedId][5])
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
            for id, (startX,startY,endX,endY,para,blank) in p.textBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if p.mode=='delete':
                        #delete the text BB
                        pairs=[]#pairs this BB is part of
                        for pair in p.pairing:
                            if id==pair[0]:
                                pairs.append(pair)
                        for pair in pairs:
                            p.pairing.remove(pair)
                        p.actionStack.append(('remove-text',id,startX,startY,endX,endY,para,blank,pairs))
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

            for id, (startX,startY,endX,endY,para,blank) in p.fieldBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if p.mode=='delete':
                        #delete the field BB
                        pairs=[]#pairs this BB is part of
                        for pair in p.pairing:
                            if id==pair[1]:
                                pairs.append(pair)
                        for pair in pairs:
                            p.pairing.remove(pair)
                        p.actionStack.append(('remove-field',id,startX,startY,endX,endY,para,blank,pairs))
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
                leftBoundary = bbs[p.selectedId][0] + 0.5*w
                rightBoundary = bbs[p.selectedId][0] + 0.5*w
                topBoundary = bbs[p.selectedId][1] + 0.5*h
                bottomBoundary = bbs[p.selectedId][1] + 0.5*h
                
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
            elif 'none' not in p.mode and 'delete' not in p.mode:
                p.mode = p.mode[:-1]+'m'
            else:
                p.mode = p.mode[:-2]
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
        label,id,startX,startY,endX,endY,para,blank,pairs = action
        del p.textBBs[id]
        if pairs is not None:
            for pair in pairs:
                p.pairing.remove(pair)
        if p.selected=='text' and p.selectedId==id:
            p.selected='none'
        return ('remove-text',id,startX,startY,endX,endY,para,blank,pairs)
    elif action[0] == 'remove-text':
        label,id,startX,startY,endX,endY,para,blank,pairs = action
        p.textBBs[id]=(startX,startY,endX,endY,para,blank)
        if pairs is not None:
            for pair in pairs:
                p.pairing.append(pair)
        return ('add-text',id,startX,startY,endX,endY,para,blank,pairs)
    elif action[0] == 'add-field':
        label,id,startX,startY,endX,endY,para,blank,pairs = action
        del p.fieldBBs[id]
        if pairs is not None:
            for pair in pairs:
                p.pairing.remove(pair)
        if p.selected=='field' and p.selectedId==id:
            p.selected='none'
        return ('remove-field',id,startX,startY,endX,endY,para,blank,pairs)
    elif action[0] == 'remove-field':
        label,id,startX,startY,endX,endY,para,blank,pairs = action
        p.fieldBBs[id]=(startX,startY,endX,endY,para,blank)
        if pairs is not None:
            for pair in pairs:
                p.pairing.append(pair)
        return ('add-field',id,startX,startY,endX,endY,para,blank,pairs)
    elif action[0] == 'drag-field':
        label,id,startX,startY,endX,endY = action
        toRet = (label,id,p.fieldBBs[id][0],p.fieldBBs[id][1],p.fieldBBs[id][2],p.fieldBBs[id][3])
        p.fieldBBs[id] = (startX,startY,endX,endY,p.fieldBBs[id][4],p.fieldBBs[id][5])
        return toRet
    elif action[0] == 'drag-text':
        label,id,startX,startY,endX,endY = action
        toRet = (label,id,p.textBBs[id][0],p.textBBs[id][1],p.textBBs[id][2],p.textBBs[id][3])
        p.textBBs[id] = (startX,startY,endX,endY,p.textBBs[id][4],p.fieldBBs[id][5])
        return toRet
    elif action[0] == 'change-text':
        label,id,code = action
        toRet = (label,id,p.textBBs[id][4])
        p.textBBs[id] = (p.textBBs[id][0],p.textBBs[id][1],p.textBBs[id][2],p.textBBs[id][3],code,p.fieldBBs[id][5])
        return toRet
    elif action[0] == 'change-field':
        label,id,code = action
        toRet = (label,id,p.fieldBBs[id][4])
        p.fieldBBs[id] = (p.fieldBBs[id][0],p.fieldBBs[id][1],p.fieldBBs[id][2],p.fieldBBs[id][3],code,p.fieldBBs[id][5])
        return toRet
    elif action[0] == 'flip-blank':#only occurs with fields
        label,id= action
        toRet = (label,id)
        newBlank = int(p.fieldBBs[id][4]!=1)
        p.fieldBBs[id] = (p.fieldBBs[id][0],p.fieldBBs[id][1],p.fieldBBs[id][2],p.fieldBBs[id][3],newBlank,p.fieldBBs[id][5])
        return toRet
    else:
        print 'Unimplemented action: '+action[0]

def change(p):
        tmpMode = p.mode
        p.mode='change'
        drawToolbar(p)
        key = cv2.waitKey() & 0xFF
        for mode in keyMap:
            if key==keyMap[mode] and p.selected[:4]==mode[:4]:
                if p.selected=='text':
                    p.actionStack.append(('change-text',p.selectedId,p.textBBs[p.selectedId][4]))
                    p.textBBs[p.selectedId]=(p.textBBs[p.selectedId][0],p.textBBs[p.selectedId][1],p.textBBs[p.selectedId][2],p.textBBs[p.selectedId][3],codeMap[mode],p.textBBs[p.selectedId][5])
                elif p.selected=='field':
                    p.actionStack.append(('change-field',p.selectedId,p.fieldBBs[p.selectedId][4]))
                    p.fieldBBs[p.selectedId]=(p.fieldBBs[p.selectedId][0],p.fieldBBs[p.selectedId][1],p.fieldBBs[p.selectedId][2],p.fieldBBs[p.selectedId][3],codeMap[mode],p.textBBs[p.selectedId][5])
                draw(p)

        p.mode=tmpMode
        drawToolbar(p)

def flipBlank(p):
    if p.selected=='field':
        p.actionStack.append(('flip-blank',p.selectedId))
        newBlank = int(p.fieldBBs[p.selectedId][5]!=1)
        p.fieldBBs[p.selectedId]=(p.fieldBBs[p.selectedId][0],p.fieldBBs[p.selectedId][1],p.fieldBBs[p.selectedId][2],p.fieldBBs[p.selectedId][3],p.fieldBBs[p.selectedId][4],newBlank)
        draw(p)

def draw(p):
    p.displayImage[0:p.image.shape[0], 0:p.image.shape[1]] = p.image
    for id, (startX,startY,endX,endY,code,blank) in p.textBBs.iteritems():
        cv2.rectangle(p.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)

    for id, (startX,startY,endX,endY,code,blank) in p.fieldBBs.iteritems():
        cv2.rectangle(p.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
        if blank==1:
            w = endX-startX
            h = endY-startY
            cv2.rectangle(p.displayImage,(startX+2,startY+2),(endX-2,endY-2),(240,240,240),1)
            cv2.rectangle(p.displayImage,(int(startX+0.25*w),int(startY+0.25*h)),(int(endX-0.25*w),int(endY-0.25*h)),(240,240,240),1)
            cv2.rectangle(p.displayImage,(int(startX+0.15*w),int(startY+0.15*h)),(int(endX-0.15*w),int(endY-0.15*h)),(240,240,240),1)
            cv2.rectangle(p.displayImage,(int(startX+0.35*w),int(startY+0.35*h)),(int(endX-0.35*w),int(endY-0.35*h)),(240,240,240),1)

    for text,field in p.pairing:
        x1=(p.textBBs[text][0]+p.textBBs[text][2])/2
        y1=(p.textBBs[text][1]+p.textBBs[text][3])/2
        x2=(p.fieldBBs[field][0]+p.fieldBBs[field][2])/2
        y2=(p.fieldBBs[field][1]+p.fieldBBs[field][3])/2
        cv2.line(p.displayImage,(x1,y1),(x2,y2),(0,255,0),1)

    if p.selected == 'text':
        startX,startY,endX,endY,para,blank = p.textBBs[p.selectedId]
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
        startX,startY,endX,endY,para,blank = p.fieldBBs[p.selectedId]
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
        cv2.rectangle(p.displayImage,(p.startX,p.startY),(p.endX,p.endY),colorMap[p.mode[:-2]],1)

    cv2.imshow("labeler",p.displayImage)

def drawToolbar(p):
    p.displayImage[0:,-TOOL_WIDTH:]=(140,140,140)

    y=0

    for mode in modes:
        p.displayImage[y:y+toolH,-TOOL_WIDTH:]=colorMap[mode]
        if p.mode==mode:
            cv2.rectangle(p.displayImage,(p.displayImage.shape[1]-TOOL_WIDTH+1,y),(p.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
        cv2.putText(p.displayImage,toolMap[mode],(p.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        y+=toolH+1

    #undo
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(160,160,160)
    cv2.putText(p.displayImage,'A:undo',(p.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #redo
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(190,190,190)
    cv2.putText(p.displayImage,'S:redo',(p.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #change
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(230,230,230)
    if p.mode=='change':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[1]-TOOL_WIDTH+1,y),(p.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'D:switch type',(p.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #delete
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(250,250,250)
    if p.mode=='delete':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[1]-TOOL_WIDTH+1,y),(p.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'F:delete',(p.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
    y+=toolH+1

    #blank
    p.displayImage[y:y+toolH,-TOOL_WIDTH:]=(30,30,30)
    if p.mode=='blank':
        cv2.rectangle(p.displayImage,(p.displayImage.shape[1]-TOOL_WIDTH+1,y),(p.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
    cv2.putText(p.displayImage,'Z:mark blank',(p.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(240,240,240))
    y+=toolH+1

    cv2.imshow("labeler",p.displayImage)

def labelImage(imagePath,displayH,displayW,texts,fields,pairs):
    p = Params()
    p.displayImage = np.zeros((displayH,displayW,3),dtype=np.uint8)
    p.image = cv2.imread(imagePath)
    if p.image is None:
        print 'cannot open image '+imagePath
        exit(1)
    scale = min(float(displayH)/p.image.shape[0],float(displayW-TOOL_WIDTH)/p.image.shape[1])
    p.image=cv2.resize(p.image,(0,0),None,scale,scale)
    if texts is not None and fields is not None and pairs is not None:
        for (startX,startY,endX,endY,para) in texts:
            p.textBBs[p.textBBsCurId] = (int(round(startX*scale)),int(round(startY*scale)),int(round(endX*scale)),int(round(endY*scale)),para,0)
            p.textBBsCurId+=1
        for (startX,startY,endX,endY,para,blank) in fields:
            p.fieldBBs[p.fieldBBsCurId] = (int(round(startX*scale)),int(round(startY*scale)),int(round(endX*scale)),int(round(endY*scale)),para,blank)
            p.fieldBBsCurId+=1
        p.pairing=pairs


    cv2.namedWindow("labeler")
    cv2.setMouseCallback("labeler", clicker,param=p)
    draw(p)
    drawToolbar(p)
    #cv2.imshow('labeler',p.displayImage)
    while True:
        key = cv2.waitKey(33) & 0xFF
        if key in RkeyMap:
            newMode = RkeyMap[key]
            if p.mode != newMode:
                p.mode = newMode
                drawToolbar(p)
        elif key==27: #esc
            break
        elif key==102: #F
            if p.mode != 'delete':
                p.mode='delete'
                drawToolbar(p)
        elif key==97: #A undo
            undo(p)
        elif key==115: #S redo
            redo(p)
        elif key==100: #D change
            change(p)
        elif key==122: #Z blank
            flipBlank(p)


    idToIdxText={}
    textBBs=[]
    for id, (startX,startY,endX,endY,para,blank) in p.textBBs.iteritems():
        idToIdxText[id]=len(textBBs)
        textBBs.append((int(round(startX/scale)),int(round(startY/scale)),int(round(endX/scale)),int(round(endY/scale)),para))
    idToIdxField={}
    fieldBBs=[]
    for id, (startX,startY,endX,endY,para,blank) in p.fieldBBs.iteritems():
        idToIdxField[id]=len(fieldBBs)
        fieldBBs.append((int(round(startX/scale)),int(round(startY/scale)),int(round(endX/scale)),int(round(endY/scale)),para,blank))
    pairing=[]
    for text,field in p.pairing:
        pairing.append((idToIdxText[text],idToIdxField[field]))

    return textBBs, fieldBBs, pairing

texts=None
fields=None
pairs=None
if len(sys.argv)>4:
    with open(sys.argv[4]) as f:
        read = json.loads(f.read())
        texts=read['texts']
        fields=read['fields']
        pairs=read['pairs']

texts,fields,pairs = labelImage(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),texts,fields,pairs)
outFile='test.json'
with open(outFile,'w') as out:
    out.write(json.dumps({"texts":texts, "fields":fields, "pairs":pairs}))
