import sys
#import cv2
from matplotlib import pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches
from matplotlib import gridspec
import numpy as np
import math
import json

#Globals
TOOL_WIDTH=240
toolH=40
colorMap = {'text':(0/255.0,0/255.0,255/255.0), 'textP':(0/255.0,150/255.0,255/255.0), 'textMinor':(100/255.0,190/255.0,205/255.0), 'textInst':(190/255.0,210/255.0,255/255.0), 'textNumber':(0/255.0,160/255.0,100/255.0), 'fieldCircle':(255/255.0,190/255.0,210/255.0), 'field':(255/255.0,0/255.0,0/255.0), 'fieldP':(255/255.0,120/255.0,0/255.0), 'fieldCheckBox':(255/255.0,220/255.0,0/255.0), 'graphic':(255/255.0,105/255.0,250/255.0)}
codeMap = {'text':0, 'textP':1, 'textMinor':2, 'textInst':3, 'textNumber':4, 'fieldCircle':5, 'field':6, 'fieldP':7, 'fieldCheckBox':8, 'graphic':9}
RcodeMap = {v: k for k, v in codeMap.iteritems()}
keyMap = {'text':'1',
          'textP':'2',
          'textMinor':'3',
          'textInst':'4',
          'textNumber':'5',
          'field':'q',
          'fieldP':'w',
          'fieldCheckBox':'e',
          'fieldCircle':'r',
          'graphic':'t',
          }
RkeyMap = {v: k for k, v in keyMap.iteritems()}
toolMap = {'text':'1:text/label', 'textP':'2:text para', 'textMinor':'3:minor label', 'textInst':'4:instructions', 'textNumber':'5:enumeration (#)', 'fieldCircle':'R:to be circled', 'field':'Q:field', 'fieldP':'W:field para', 'fieldCheckBox':'E:check-box', 'graphic':'T:graphic'}
modes = ['text', 'textP', 'textMinor', 'textInst', 'textNumber', 'field', 'fieldP', 'fieldCheckBox', 'fieldCircle', 'graphic']


class Control:
    def __init__(self,ax_im,ax_tool,texts,fields,pairs):
        self.ax_im=ax_im
        self.ax_tool=ax_tool
        self.down_cid = self.ax_im.figure.canvas.mpl_connect(
                            'button_press_event', self.clickerDown)
        self.up_cid = self.ax_im.figure.canvas.mpl_connect(
                            'button_release_event', self.clickerUp)
        self.move_cid = self.ax_im.figure.canvas.mpl_connect(
                            'motion_notify_event', self.clickerMove)
        self.key_cid = self.ax_im.figure.canvas.mpl_connect(
                            'key_press_event', self.doKey)
        self.mode='none'
        self.textBBs={}
        self.textRects={}
        self.textBBsCurId=0
        self.fieldBBs={}
        self.fieldRects={}
        self.fieldBBsCurId=0
        self.pairing=[]
        self.pairLines={}
        self.image=None
        self.displayImage=None
        self.startX=-1
        self.startY=-1
        self.endX=-1
        self.endY=-1
        self.actionStack=[]
        self.undoStack=[]
        self.selectedId=-1
        self.selected='none'
        if texts is not None and fields is not None and pairs is not None:
            for (startX,startY,endX,endY,para) in texts:
                self.textBBs[self.textBBsCurId] = (int(round(startX*scale)),int(round(startY*scale)),int(round(endX*scale)),int(round(endY*scale)),para,0)
                self.textBBsCurId+=1
            for (startX,startY,endX,endY,para,blank) in fields:
                self.fieldBBs[self.fieldBBsCurId] = (int(round(startX*scale)),int(round(startY*scale)),int(round(endX*scale)),int(round(endY*scale)),para,blank)
                self.fieldBBsCurId+=1
            self.pairing=pairs

    def clickerDown(self,event):
        #image,displayImage,mode,textBBs,fieldBBs,pairing = param
        if event.inaxes!=self.ax_im.axes or event.button!=3: return
        if self.mode!='delete':
            self.mode+='-d'
            self.startX=event.xdata
            self.startY=event.ydata

    def clickerUp(self,event):
        if event.button!=3: return
        if '-m' == self.mode[-2:]: #we dragged to make a box
            self.mode=self.mode[:-2] #make state readable
            if abs((self.startX-self.endX)*(self.startY-self.endY))>10: #the box is "big enough"
                didPair=None #for storing auto-pair for undo/action stack

                #auto-pair to selected
                if 'text' in self.mode and 'field' in self.selected:
                    self.pairing.append((self.textBBsCurId,self.selectedId))
                    didPair=[(self.textBBsCurId,self.selectedId)]
                elif 'field' in self.mode and 'text' in self.selected:
                    self.pairing.append((self.selectedId,self.fieldBBsCurId))
                    didPair=[(self.selectedId,self.fieldBBsCurId)]

                code = codeMap[self.mode]
                if self.mode[:4]=='text':
                    self.textBBs[self.textBBsCurId]=(min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0)
                    self.actionStack.append(('add-text',self.textBBsCurId,min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0,didPair))
                    self.undoStack=[]
                    self.selectedId=self.textBBsCurId
                    self.selected='text'
                    self.textRects[self.textBBsCurId] = patches.Rectangle((self.textBBs[self.textBBsCurId][0],self.textBBs[self.textBBsCurId][1]),self.textBBs[self.textBBsCurId][2]-self.textBBs[self.textBBsCurId][0],self.textBBs[self.textBBsCurId][3]-self.textBBs[self.textBBsCurId][1],linewidth=2,edgecolor=colorMap[self.mode],facecolor='none')
                    self.ax_im.add_patch(self.textRects[self.textBBsCurId])
                    self.textRects[self.textBBsCurId].figure.canvas.draw()
                    self.textBBsCurId+=1
                else: #self.mode[:5]=='field':
                    self.fieldBBs[self.fieldBBsCurId]=(min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0)
                    self.actionStack.append(('add-field',self.fieldBBsCurId,min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),code,0,didPair))
                    self.undoStack=[]
                    self.selectedId=self.fieldBBsCurId
                    self.selected='field'
                    self.fieldRects[self.fieldBBsCurId] = patches.Rectangle((self.fieldBBs[self.fieldBBsCurId][0],self.fieldBBs[self.fieldBBsCurId][1]),self.fieldBBs[self.fieldBBsCurId][2]-self.fieldBBs[self.fieldBBsCurId][0],self.fieldBBs[self.fieldBBsCurId][3]-self.fieldBBs[self.fieldBBsCurId][1],linewidth=2,edgecolor=colorMap[self.mode],facecolor='none')
                    self.ax_im.add_patch(self.fieldRects[self.fieldBBsCurId])
                    self.fieldRects[self.fieldBBsCurId].figure.canvas.draw()
                    self.fieldBBsCurId+=1
                if didPair is not None:
                    x=(self.textBBs[didPair[0]][2]-self.textBBs[didPair[0]][0])/2
                    y=(self.textBBs[didPair[0]][3]-self.textBBs[didPair[0]][1])/2
                    xe=(self.fieldBBs[didPair[1]][2]-self.fieldBBs[didPair[1]][0])/2
                    ye=(self.fieldBBs[didPair[1]][3]-self.fieldBBs[didPair[1]][1])/2
                    self.pairLines[didPair]=patches.Arrow(x,y,xe-x,ye-y,1,edgecolor='g',facecolor='none')
                    self.ax_im.add_patch(self.pairLines[didPair])
                    #self.pairLines[didPair].figure.canvas.draw()
           # draw(self)
        elif '-tl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (self.endX,self.endY,bbs[self.selectedId][2],bbs[self.selectedId][3],bbs[self.selectedId][4],bbs[self.selectedId][5])
                #draw(self)
        elif '-bl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (self.endX,bbs[self.selectedId][1],bbs[self.selectedId][2],self.endY,bbs[self.selectedId][4],bbs[self.selectedId][5])
                #draw(self)
        elif '-tr' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (bbs[self.selectedId][0],self.endY,self.endX,bbs[self.selectedId][3],bbs[self.selectedId][4],bbs[self.selectedId][5])
                #draw(self)
        elif '-br' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId,bbs[self.selectedId][0],bbs[self.selectedId][1],bbs[self.selectedId][2],bbs[self.selectedId][3]))
                bbs[self.selectedId] = (bbs[self.selectedId][0],bbs[self.selectedId][1],self.endX,self.endY,bbs[self.selectedId][4],bbs[self.selectedId][5])
                #draw(self)
        else:
            if '-d' == self.mode[-2:]:
                self.mode=self.mode[:-2]

            if self.mode=='delete': #first check for pairing lines (we can only delete them)
                for index,(text,field) in enumerate(self.pairing):
                    #if within bounds of line and within distance from it
                    x1=(self.textBBs[text][0]+self.textBBs[text][2])/2
                    y1=(self.textBBs[text][1]+self.textBBs[text][3])/2
                    x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2])/2
                    y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3])/2

                    if x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/math.sqrt(pow(y2-y1,2.0) + pow(x2-x1,2.0)) < 3.5:
                        #delete the pairing
                        self.actionStack.append(('remove-pairing',text,field))
                        self.undoStack=[]
                        del self.pairing[index]
                        #draw(self)
                        return
            #then bbs
            for id, (startX,startY,endX,endY,para,blank) in self.textBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if self.mode=='delete':
                        #delete the text BB
                        pairs=[]#pairs this BB is part of
                        for pair in self.pairing:
                            if id==pair[0]:
                                pairs.append(pair)
                        for pair in pairs:
                            self.pairing.remove(pair)
                        self.actionStack.append(('remove-text',id,startX,startY,endX,endY,para,blank,pairs))
                        self.undoStack=[]
                        del self.textBBs[id]
                        if self.selected=='text' and self.selectedId==id:
                            self.selected='none'
                    else:
                        #pair to prev selected?
                        if self.selected=='field' and (id,self.selectedId) not in self.pairing:
                            self.pairing.append((id,self.selectedId))
                            self.actionStack.append(('add-pairing',id,self.selectedId))
                            self.undoStack=[]
                        #select the text BB
                        self.selectedId=id
                        self.selected='text'
                    #draw(self)
                    return

            for id, (startX,startY,endX,endY,para,blank) in self.fieldBBs.iteritems():
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if self.mode=='delete':
                        #delete the field BB
                        pairs=[]#pairs this BB is part of
                        for pair in self.pairing:
                            if id==pair[1]:
                                pairs.append(pair)
                        for pair in pairs:
                            self.pairing.remove(pair)
                        self.actionStack.append(('remove-field',id,startX,startY,endX,endY,para,blank,pairs))
                        self.undoStack=[]
                        del self.fieldBBs[id]
                        if self.selected=='field' and self.selectedId==id:
                            self.selected='none'
                    else:
                        #pair to prev selected?
                        if self.selected=='text' and (self.selectedId,id) not in self.pairing:
                            self.pairing.append((self.selectedId,id))
                            self.actionStack.append(('add-pairing',self.selectedId,id))
                            self.undoStack=[]
                        #select the field BB
                        self.selectedId=id
                        self.selected='field'
                    #draw(self)
                    return

            if self.selected!='none':
                #print 'deselected'
                self.selected='none'
                #draw(self)

    def clickerMove(self,event):           
        #moving only matters if the button is down and we've moved "enough"
        bbs = None
        if self.selected == 'field':
            bbs = self.fieldBBs
        elif self.selected == 'text':
            bbs = self.textBBs
        if '-d' == self.mode[-2:] and math.sqrt(pow(event.xdata-self.startX,2)+pow(event.ydata-self.startY,2))>2:
            if bbs is not None and self.startX>bbs[self.selectedId][0] and self.startX<bbs[self.selectedId][2] and self.startY>bbs[self.selectedId][1] and self.startY<bbs[self.selectedId][3]:
                #we are going to adjust the selected BB, but how?
                w=bbs[self.selectedId][2]-bbs[self.selectedId][0] +1
                h=bbs[self.selectedId][3]-bbs[self.selectedId][1] +1
                leftBoundary = bbs[self.selectedId][0] + 0.5*w
                rightBoundary = bbs[self.selectedId][0] + 0.5*w
                topBoundary = bbs[self.selectedId][1] + 0.5*h
                bottomBoundary = bbs[self.selectedId][1] + 0.5*h
                
                if self.startX<leftBoundary and self.startY<topBoundary:#top-left corner
                    self.mode = self.mode[:-1]+'tl'
                elif self.startX<leftBoundary and self.startY>bottomBoundary:#bot-left corner
                    self.mode = self.mode[:-1]+'bl'
                elif self.startX>rightBoundary and self.startY<topBoundary:#top-right corner
                    self.mode = self.mode[:-1]+'tr'
                elif self.startX>rightBoundary and self.startY>bottomBoundary:#bot-right corner
                    self.mode = self.mode[:-1]+'br'
                #elif self.startX<leftBoundary:#left
                #    self.mode = self.mode[:-1]+'l'
                #elif self.startX>rightBoundary:#right
                #    self.mode = self.mode[:-1]+'r'
                #elif self.startY<topBoundary:#top
                #    self.mode = self.mode[:-1]+'t'
                #elif self.startY<bottomBoundary:#bot
                #    self.mode = self.mode[:-1]+'b'
            elif 'none' not in self.mode and 'delete' not in self.mode:
                self.mode = self.mode[:-1]+'m'
            else:
                self.mode = self.mode[:-2]
        if '-m' == self.mode[-2:]:
            self.endX=event.xdata
            self.endY=event.ydata
            #draw(self)
        elif (('-tl' == self.mode[-3:] and  x<bbs[self.selectedId][2] and y<bbs[self.selectedId][3]) or
              ('-bl' == self.mode[-3:] and  x<bbs[self.selectedId][2] and y>bbs[self.selectedId][1]) or
              ('-tr' == self.mode[-3:] and  x>bbs[self.selectedId][0] and y<bbs[self.selectedId][3]) or
              ('-br' == self.mode[-3:] and  x>bbs[self.selectedId][0] and y>bbs[self.selectedId][1]) or
              ('-l' == self.mode[-3:] and  x<bbs[self.selectedId][2]) or
              ('-r' == self.mode[-3:] and  x>bbs[self.selectedId][0]) or
              ('-t' == self.mode[-3:] and  y<bbs[self.selectedId][3]) or
              ('-b' == self.mode[-3:] and  y>bbs[self.selectedId][1])):
            self.endX=event.xdata
            self.endY=event.ydata
            #draw(self)

    def doKey(self,event):
        if self.mode=='change':
            key = event.key
            for mode in keyMap:
                if key==keyMap[mode] and self.selected[:4]==mode[:4]:
                    if self.selected=='text':
                        self.actionStack.append(('change-text',self.selectedId,self.textBBs[self.selectedId][4]))
                        self.textBBs[self.selectedId]=(self.textBBs[self.selectedId][0],self.textBBs[self.selectedId][1],self.textBBs[self.selectedId][2],self.textBBs[self.selectedId][3],codeMap[mode],self.textBBs[self.selectedId][5])
                    elif self.selected=='field':
                        self.actionStack.append(('change-field',self.selectedId,self.fieldBBs[self.selectedId][4]))
                        self.fieldBBs[self.selectedId]=(self.fieldBBs[self.selectedId][0],self.fieldBBs[self.selectedId][1],self.fieldBBs[self.selectedId][2],self.fieldBBs[self.selectedId][3],codeMap[mode],self.textBBs[self.selectedId][5])
                    #draw(p)

            self.mode=self.tmpMode
            #drawToolbar(p)
        else:
            key = event.key
            if key in RkeyMap:
                newMode = RkeyMap[key]
                if self.mode != newMode:
                    self.mode = newMode
                    print newMode
                    #drawToolbar(p)
            elif key=='escape': #quit
                plt.close('all')
            elif key=='f': #delete:
                if self.mode != 'delete':
                    self.mode='delete'
                    #drawToolbar(p)
            elif key=='a': # undo
                undo()
            elif key=='s': #S redo
                redo()
            elif key=='d': #D change
                change()
            elif key=='z': #Z blank
                flipBlank()



    def undo(self):
        if len(self.actionStack)>0:
            action = self.actionStack.pop()
            action = undoAction(p,action)

            self.undoStack.append(action)
            #draw(p)

    def redo(self):
        if len(self.undoStack)>0:
            action = self.undoStack.pop()
            action = undoAction(p,action)

            self.actionStack.append(action)
            #draw(p)

    def undoAction(self,action):
        if action[0] == 'add-pairing':
            self.pairing.remove((action[1],action[2]))
            return ('remove-pairing',action[1],action[2])
        elif action[0] == 'remove-pairing':
            self.pairing.append((action[1],action[2]))
            return ('add-pairing',action[1],action[2])
        elif action[0] == 'add-text':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            del self.textBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if self.selected=='text' and self.selectedId==id:
                self.selected='none'
            return ('remove-text',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'remove-text':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            self.textBBs[id]=(startX,startY,endX,endY,para,blank)
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            return ('add-text',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'add-field':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            del self.fieldBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if self.selected=='field' and self.selectedId==id:
                self.selected='none'
            return ('remove-field',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'remove-field':
            label,id,startX,startY,endX,endY,para,blank,pairs = action
            self.fieldBBs[id]=(startX,startY,endX,endY,para,blank)
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            return ('add-field',id,startX,startY,endX,endY,para,blank,pairs)
        elif action[0] == 'drag-field':
            label,id,startX,startY,endX,endY = action
            toRet = (label,id,self.fieldBBs[id][0],self.fieldBBs[id][1],self.fieldBBs[id][2],self.fieldBBs[id][3])
            self.fieldBBs[id] = (startX,startY,endX,endY,self.fieldBBs[id][4],self.fieldBBs[id][5])
            return toRet
        elif action[0] == 'drag-text':
            label,id,startX,startY,endX,endY = action
            toRet = (label,id,self.textBBs[id][0],self.textBBs[id][1],self.textBBs[id][2],self.textBBs[id][3])
            self.textBBs[id] = (startX,startY,endX,endY,self.textBBs[id][4],self.fieldBBs[id][5])
            return toRet
        elif action[0] == 'change-text':
            label,id,code = action
            toRet = (label,id,self.textBBs[id][4])
            self.textBBs[id] = (self.textBBs[id][0],self.textBBs[id][1],self.textBBs[id][2],self.textBBs[id][3],code,self.fieldBBs[id][5])
            return toRet
        elif action[0] == 'change-field':
            label,id,code = action
            toRet = (label,id,self.fieldBBs[id][4])
            self.fieldBBs[id] = (self.fieldBBs[id][0],self.fieldBBs[id][1],self.fieldBBs[id][2],self.fieldBBs[id][3],code,self.fieldBBs[id][5])
            return toRet
        elif action[0] == 'flip-blank':#only occurs with fields
            label,id= action
            toRet = (label,id)
            newBlank = int(self.fieldBBs[id][4]!=1)
            self.fieldBBs[id] = (self.fieldBBs[id][0],self.fieldBBs[id][1],self.fieldBBs[id][2],self.fieldBBs[id][3],newBlank,self.fieldBBs[id][5])
            return toRet
        else:
            print 'Unimplemented action: '+action[0]

    def change(self):
            self.tmpMode = self.mode
            self.mode='change'
            #drawToolbar(p)

    def flipBlank(self):
        if self.selected=='field':
            self.actionStack.append(('flip-blank',self.selectedId))
            newBlank = int(self.fieldBBs[self.selectedId][5]!=1)
            self.fieldBBs[self.selectedId]=(self.fieldBBs[self.selectedId][0],self.fieldBBs[self.selectedId][1],self.fieldBBs[self.selectedId][2],self.fieldBBs[self.selectedId][3],self.fieldBBs[self.selectedId][4],newBlank)
            #draw(p)

"""
    def #draw(p):
        #self.displayImage[0:self.image.shape[0], 0:self.image.shape[1]] = self.image
        for id, (startX,startY,endX,endY,code,blank) in self.textBBs.iteritems():
            cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)

        for id, (startX,startY,endX,endY,code,blank) in self.fieldBBs.iteritems():
            cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
            if blank==1:
                w = endX-startX
                h = endY-startY
                cv2.rectangle(self.displayImage,(startX+2,startY+2),(endX-2,endY-2),(240,240,240),1)
                cv2.rectangle(self.displayImage,(int(startX+0.25*w),int(startY+0.25*h)),(int(endX-0.25*w),int(endY-0.25*h)),(240,240,240),1)
                cv2.rectangle(self.displayImage,(int(startX+0.15*w),int(startY+0.15*h)),(int(endX-0.15*w),int(endY-0.15*h)),(240,240,240),1)
                cv2.rectangle(self.displayImage,(int(startX+0.35*w),int(startY+0.35*h)),(int(endX-0.35*w),int(endY-0.35*h)),(240,240,240),1)

        for text,field in self.pairing:
            x1=(self.textBBs[text][0]+self.textBBs[text][2])/2
            y1=(self.textBBs[text][1]+self.textBBs[text][3])/2
            x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2])/2
            y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3])/2
            cv2.line(self.displayImage,(x1,y1),(x2,y2),(0,255,0),1)

        if self.selected == 'text':
            startX,startY,endX,endY,para,blank = self.textBBs[self.selectedId]
            if self.mode[-3:]=='-tl':
                cv2.rectangle(self.displayImage,(self.endX,self.endY),(max(startX,endX),max(startY,endY)),(255,240,100),1)
            elif self.mode[-3:]=='-tr':
                cv2.rectangle(self.displayImage,(startX,self.endY),(self.endX,endY),(255,240,100),1)
            elif self.mode[-3:]=='-bl':
                cv2.rectangle(self.displayImage,(self.endX,startY),(endX,self.endY),(255,240,100),1)
            elif self.mode[-3:]=='-br':
                cv2.rectangle(self.displayImage,(startX,startY),(self.endX,self.endY),(255,240,100),1)
            cv2.rectangle(self.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)
        elif self.selected == 'field':
            startX,startY,endX,endY,para,blank = self.fieldBBs[self.selectedId]
            if self.mode[-3:]=='-tl':
                cv2.rectangle(self.displayImage,(self.endX,self.endY),(max(startX,endX),max(startY,endY)),(120,255,255),1)
            elif self.mode[-3:]=='-tr':
                cv2.rectangle(self.displayImage,(startX,self.endY),(self.endX,endY),(120,255,255),1)
            elif self.mode[-3:]=='-bl':
                cv2.rectangle(self.displayImage,(self.endX,startY),(endX,self.endY),(120,255,255),1)
            elif self.mode[-3:]=='-br':
                cv2.rectangle(self.displayImage,(startX,startY),(self.endX,self.endY),(120,255,255),1)
            cv2.rectangle(self.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)

        if self.mode[-2:]=='-m':
            cv2.rectangle(self.displayImage,(self.startX,self.startY),(self.endX,self.endY),colorMap[self.mode[:-2]],1)

        cv2.imshow("labeler",self.displayImage)

    def #drawToolbar(p):
        self.displayImage[0:,-TOOL_WIDTH:]=(140,140,140)

        y=0

        for mode in modes:
            self.displayImage[y:y+toolH,-TOOL_WIDTH:]=colorMap[mode]
            if self.mode==mode:
                cv2.rectangle(self.displayImage,(self.displayImage.shape[1]-TOOL_WIDTH+1,y),(self.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
            cv2.putText(self.displayImage,toolMap[mode],(self.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
            y+=toolH+1

        #undo
        self.displayImage[y:y+toolH,-TOOL_WIDTH:]=(160,160,160)
        cv2.putText(self.displayImage,'A:undo',(self.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        y+=toolH+1

        #redo
        self.displayImage[y:y+toolH,-TOOL_WIDTH:]=(190,190,190)
        cv2.putText(self.displayImage,'S:redo',(self.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        y+=toolH+1

        #change
        self.displayImage[y:y+toolH,-TOOL_WIDTH:]=(230,230,230)
        if self.mode=='change':
            cv2.rectangle(self.displayImage,(self.displayImage.shape[1]-TOOL_WIDTH+1,y),(self.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
        cv2.putText(self.displayImage,'D:switch type',(self.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        y+=toolH+1

        #delete
        self.displayImage[y:y+toolH,-TOOL_WIDTH:]=(250,250,250)
        if self.mode=='delete':
            cv2.rectangle(self.displayImage,(self.displayImage.shape[1]-TOOL_WIDTH+1,y),(self.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
        cv2.putText(self.displayImage,'F:delete',(self.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        y+=toolH+1

        #blank
        self.displayImage[y:y+toolH,-TOOL_WIDTH:]=(30,30,30)
        if self.mode=='blank':
            cv2.rectangle(self.displayImage,(self.displayImage.shape[1]-TOOL_WIDTH+1,y),(self.displayImage.shape[1]-1,y+toolH),(255,0,255),2)
        cv2.putText(self.displayImage,'Z:mark blank',(self.displayImage.shape[1]-TOOL_WIDTH+3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(240,240,240))
        y+=toolH+1

        cv2.imshow("labeler",self.displayImage)
        """

def labelImage(imagePath,displayH,displayW,texts,fields,pairs):
    #p = Params()
    toolImage = np.zeros(((toolH+1)*(len(modes)+5),TOOL_WIDTH,3),dtype=np.uint8)
    toolImage[:,:,:] = 140
    image = mpimg.imread(sys.argv[1])
    #if p.image is None:
    #    print 'cannot open image '+imagePath
    #    exit(1)
    #scale = min(float(displayH)/p.image.shape[0],float(displayW-TOOL_WIDTH)/p.image.shape[1])
    #p.image=cv2.resize(p.image,(0,0),None,scale,scale)
    


    #cv2.namedWindow("labeler")
    #cv2.setMouseCallback("labeler", clicker,param=p)
    #draw(p)
    #drawToolbar(p)
    #cv2.imshow('labeler',p.displayImage)

    #fig,axs = plt.subplots(1,2)
    fig = plt.figure()
    gs = gridspec.GridSpec(1, 2, width_ratios=[8, 1])
    ax_im = plt.subplot(gs[0])
    ax_im.imshow(image)
    ax_tool = plt.subplot(gs[1])
    ax_tool.imshow(toolImage)
    ax_im.figure.canvas.mpl_disconnect(fig.canvas.manager.key_press_handler_id)
    control = Control(ax_im,ax_tool,texts,fields,pairs)
    plt.show()


    idToIdxText={}
    textBBs=[]
    for id, (startX,startY,endX,endY,para,blank) in control.textBBs.iteritems():
        idToIdxText[id]=len(textBBs)
        textBBs.append((int(round(startX/scale)),int(round(startY/scale)),int(round(endX/scale)),int(round(endY/scale)),para))
    idToIdxField={}
    fieldBBs=[]
    for id, (startX,startY,endX,endY,para,blank) in control.fieldBBs.iteritems():
        idToIdxField[id]=len(fieldBBs)
        fieldBBs.append((int(round(startX/scale)),int(round(startY/scale)),int(round(endX/scale)),int(round(endY/scale)),para,blank))
    pairing=[]
    for text,field in control.pairing:
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
