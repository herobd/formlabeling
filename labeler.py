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
mouse_button=3
TOOL_WIDTH=240
toolH=40
colorMap = {'text':(0/255.0,0/255.0,255/255.0), 'textP':(0/255.0,150/255.0,255/255.0), 'textMinor':(100/255.0,190/255.0,205/255.0), 'textInst':(190/255.0,210/255.0,255/255.0), 'textNumber':(0/255.0,160/255.0,100/255.0), 'fieldCircle':(255/255.0,190/255.0,210/255.0), 'field':(255/255.0,0/255.0,0/255.0), 'fieldP':(255/255.0,120/255.0,0/255.0), 'fieldCheckBox':(255/255.0,220/255.0,0/255.0), 'graphic':(255/255.0,105/255.0,250/255.0), 'comment':(165/255.0,10/255.0,15/255.0)}
DRAW_COLOR=(1,0.7,1)
codeMap = {'text':0, 'textP':1, 'textMinor':2, 'textInst':3, 'textNumber':4, 'fieldCircle':5, 'field':6, 'fieldP':7, 'fieldCheckBox':8, 'graphic':9, 'comment':10}
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
          'comment':'y',
          }
RkeyMap = {v: k for k, v in keyMap.iteritems()}
toolMap = {'text':'1:text/label', 'textP':'2:text para', 'textMinor':'3:minor label', 'textInst':'4:instructions', 'textNumber':'5:enumeration (#)', 'fieldCircle':'R:to be circled', 'field':'Q:field', 'fieldP':'W:field para', 'fieldCheckBox':'E:check-box', 'graphic':'T:graphic', 'comment':'Y:comment'}
toolYMap = {}
modes = ['text', 'textP', 'textMinor', 'textInst', 'textNumber', 'field', 'fieldP', 'fieldCheckBox', 'fieldCircle', 'graphic', 'comment']
ftypeMap = {'text':0, 'handwriting':1, 'print':2, 'blank':3} #print:typewriter or stamp
RftypeMap = {v: k for k, v in ftypeMap.iteritems()}

def get_side(a, b):
    x = x_product(a, b)
    if x < 0:
        return 'left'
    elif x > 0: 
        return 'right'
    else:
        return None

def v_sub(a, b):
    return (a[0]-b[0], a[1]-b[1])

def x_product(a, b):
    return a[0]*b[1]-a[1]*b[0]


class Control:
    def __init__(self,ax_im,ax_tool,W,H,texts,fields,pairs,page_corners):
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
        self.mode='corners' #this indicates the 'state'
        self.textBBs={} #this holds each text box as (x1,y1,x2,y2,type_code,blank). x1,y1<x2,y2 and blank is always 0
        self.textRects={} #this holds the drawing patches
        self.textBBsCurId=0
        self.fieldBBs={} #this holds each field box as (x1,y1,x2,y2,type_code,blank). x1,y1<x2,y2 blank is 0/1
        self.fieldRects={} #this holds the drawing patches
        self.fieldBBsCurId=0
        self.pairing=[] #this holds each pairing as a tuple (textId,fieldId)
        self.pairLines={} #this holds drawing patches
        self.corners={'tl':None, 'tr':None, 'br':None, 'bl':None}
        self.corners_draw={'tl':None, 'tr':None, 'br':None, 'bl':None}
        #self.image=None
        #self.displayImage=None
        self.startX=-1 #where the user clicks down
        self.startY=-1
        self.endX=-1 #the current postion of the mouse, or where it was released
        self.endY=-1
        self.actionStack=[] #for undos
        self.undoStack=[] #for redos
        self.selectedId=-1
        self.selected='none'
        self.drawRect=None #drawing patch
        self.preTexts=texts
        self.preFields=fields
        self.preCorners=page_corners
        if pairs is not None:
            self.pairing=pairs
        self.corners_text = ax_im.text(W/2,H/2,'Mark the page corners, then press ENTER.\n(outer corners if two pages).\nIf odd position, press BACKSPACE for corner by corner query.',horizontalalignment='center',verticalalignment='center')
        self.ax_im.figure.canvas.draw()
        self.imageW=W
        self.imageH=H


    def init(self):
        self.corners_text.remove()
        for key, dot in self.corners_draw.iteritems():
            dot.remove()
        if self.preTexts is not None and self.preFields is not None:
            #compute an approximate transformation based on the template corners and the just labeled ones
            trans,res_,rank_,s_ = np.linalg.lstsq(np.array([[self.preCorners['tl'][0], self.preCorners['tl'][1], 1],
                                              [self.preCorners['tr'][0], self.preCorners['tr'][1], 1],
                                              [self.preCorners['br'][0], self.preCorners['br'][1], 1],
                                              [self.preCorners['bl'][0], self.preCorners['bl'][1], 1]]),
                                    np.array([[self.corners['tl'][0], self.corners['tl'][1], 1],
                                              [self.corners['tr'][0], self.corners['tr'][1], 1],
                                              [self.corners['br'][0], self.corners['br'][1], 1],
                                              [self.corners['bl'][0], self.corners['bl'][1], 1]]))
            trans = trans.transpose()
            #point_new = trans point_old, done with homogeneour cords

            for (tlX,tlY,trX,trY,brX,brY,blX,blY,para) in self.preTexts:
                old_corners = np.array([[tlX,trX,brX,blX],
                                        [tlY,trY,brY,blY],
                                        [1,1,1,1]])
                new_points = np.matmul(trans,old_corners)
                new_points/=new_points[2,:] #bring back to standard homogeneous form
                #startX = (new_points[0,0]+new_points[0,3])/2.0 #average x of new tl and bl
                #startY = (new_points[1,0]+new_points[1,1])/2.0 #average y of new tl and tr
                #endX = (new_points[0,1]+new_points[0,2])/2.0 #average x of new tr and br
                #endY = (new_points[1,2]+new_points[1,3])/2.0 #average y of new br and bl
                #self.textBBs[self.textBBsCurId] = (int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,0)
                self.textBBs[self.textBBsCurId] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,0)
                self.textBBsCurId+=1
            for (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in self.preFields:
                old_corners = np.array([[tlX,trX,brX,blX],
                                        [tlY,trY,brY,blY],
                                        [1,1,1,1]])
                new_points = np.matmul(trans,old_corners)
                new_points/=new_points[2,:]
                self.fieldBBs[self.fieldBBsCurId] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,blank)
                self.fieldBBsCurId+=1
            #self.pairing=pairs
        self.mode='text'
        self.modeRect = patches.Rectangle((0,0),TOOL_WIDTH,toolH,linewidth=2,edgecolor=(1,0,1),facecolor='none')
        self.ax_tool.add_patch(self.modeRect)
        self.ax_tool.figure.canvas.draw()
        self.selectedRect = patches.Polygon(np.array([[0,0],[0.1,0],[0,0.1]]),linewidth=2,edgecolor=(1,0,1),facecolor='none')
        self.ax_im.add_patch(self.selectedRect)
        self.drawRect = patches.Polygon(np.array([[0,0],[0.1,0],[0,0.1]]),linewidth=2,edgecolor=(1,1,1),facecolor='none')
        self.ax_im.add_patch(self.drawRect)
        #self.ax_im.figure.canvas.draw()
        self.draw()

    def transAll(self,trans):
        for id in self.textBBs:
            tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank = self.textBBs[id]
            old_corners = np.array([[tlX,trX,brX,blX],
                                    [tlY,trY,brY,blY],
                                    [1,1,1,1]])
            new_points = np.matmul(trans,old_corners)
            new_points/=new_points[2,:] #bring back to standard homogeneous form
            self.textBBs[id] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,0)
        for id in self.fieldBBs:
            tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank = self.fieldBBs[id]
            old_corners = np.array([[tlX,trX,brX,blX],
                                    [tlY,trY,brY,blY],
                                    [1,1,1,1]])
            new_points = np.matmul(trans,old_corners)
            new_points/=new_points[2,:] #bring back to standard homogeneous form
            self.fieldBBs[id] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,blank)
        self.draw()

    def clickerDown(self,event):
        #image,displayImage,mode,textBBs,fieldBBs,pairing = param
        if event.inaxes!=self.ax_im.axes or event.button!=mouse_button: return
        if self.mode!='delete' and self.mode!='corners':
            self.mode+='-d'
            self.startX=event.xdata
            self.startY=event.ydata

    def clickerUp(self,event):
        if event.button!=mouse_button: return
        x=event.xdata
        y=event.ydata
        if '-m' == self.mode[-2:]: #we dragged to make a box
            self.drawRect.set_xy(np.array([[0,0],[0.1,0],[0,0.1]]))
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
                selX=None
                selY=None
                selH=None
                selW=None
                sv=(min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),min(self.startX,self.endX),max(self.startY,self.endY),code)
                if self.mode[:4]=='text':
                    self.textBBs[self.textBBsCurId]=sv+(0,)
                    self.actionStack.append(('add-text',self.textBBsCurId,)+sv+(0,didPair,))
                    self.undoStack=[]
                    self.selectedId=self.textBBsCurId
                    self.selected='text'
                    self.textBBsCurId+=1
                else: #self.mode[:5]=='field':
                    self.fieldBBs[self.fieldBBsCurId]=sv+(1,)
                    self.actionStack.append(('add-field',self.fieldBBsCurId,)+sv+(1,didPair,))
                    self.undoStack=[]
                    self.selectedId=self.fieldBBsCurId
                    self.selected='field'
                    self.fieldBBsCurId+=1
                #self.selectedRect.set_xy(np.array([[sv[0]-4,sv[1]-4],[sv[2]+4,sv[3]-4],[sv[4]+4,sv[5]+4],[sv[6]-4,sv[7]+4]]))
                self.setSelectedRect(sv)
                self.draw()
           # draw(self)
        elif '-tl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = (self.endX,self.endY)+bbs[self.selectedId][2:]
                self.setSelectedRect(bbs[self.selectedId])
                self.draw()
        elif '-bl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:6]+(self.endX,self.endY)+bbs[self.selectedId][8:]
                self.setSelectedRect(bbs[self.selectedId])
                self.draw()
        elif '-tr' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:2]+(self.endX,self.endY)+bbs[self.selectedId][4:]
                self.setSelectedRect(bbs[self.selectedId])
                self.draw()
        elif '-br' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:4]+(self.endX,self.endY)+bbs[self.selectedId][6:]
                self.setSelectedRect(bbs[self.selectedId])
                self.draw()
        elif '-mv' == self.mode[-3:]:#we're just moving the box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.actionStack.append(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                shiftX = self.endX-self.startX
                shiftY = self.endY-self.startY
                bbs[self.selectedId] = (bbs[self.selectedId][0]+shiftX,bbs[self.selectedId][1]+shiftY,
                                        bbs[self.selectedId][2]+shiftX,bbs[self.selectedId][3]+shiftY,
                                        bbs[self.selectedId][4]+shiftX,bbs[self.selectedId][5]+shiftY,
                                        bbs[self.selectedId][6]+shiftX,bbs[self.selectedId][7]+shiftY)+bbs[self.selectedId][8:]
                self.setSelectedRect(bbs[self.selectedId])
                self.draw()
        else:
            if '-d' == self.mode[-2:]:
                self.mode=self.mode[:-2]

            if self.mode == 'corners':
                self.ax_im.set_xlim(0,self.imageW)
                self.ax_im.set_ylim(self.imageH,0)
                if x<=self.imageW/2 and y<=self.imageH/2:
                    self.corners['tl']=(x,y)
                    if self.corners_draw['tl'] is not None:
                        self.corners_draw['tl'].remove()
                        self.corners_draw['tl']=None
                    self.corners_draw['tl'], = self.ax_im.plot(x,y,'ro')
                elif x>self.imageW/2 and y<=self.imageH/2:
                    self.corners['tr']=(x,y)
                    if self.corners_draw['tr'] is not None:
                        self.corners_draw['tr'].remove()
                        self.corners_draw['tr']=None
                    self.corners_draw['tr'], = self.ax_im.plot(x,y,'ro')
                elif x>self.imageW/2 and y>self.imageH/2:
                    self.corners['br']=(x,y)
                    if self.corners_draw['br'] is not None:
                        self.corners_draw['br'].remove()
                        self.corners_draw['br']=None
                    self.corners_draw['br'], = self.ax_im.plot(x,y,'ro')
                elif x<=self.imageW/2 and y>self.imageH/2:
                    self.corners['bl']=(x,y)
                    if self.corners_draw['bl'] is not None:
                        self.corners_draw['bl'].remove()
                        self.corners_draw['bl']=None
                    self.corners_draw['bl'], = self.ax_im.plot(x,y,'ro')
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-tl':
                self.corners['tl']=(x,y)
                if self.corners_draw['tl'] is not None:
                    self.corners_draw['tl'].remove()
                    self.corners_draw['tl']=None
                self.corners_draw['tl'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('click on top right corner')
                self.mode = 'corners-tr'
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-tr':
                self.corners['tr']=(x,y)
                if self.corners_draw['tr'] is not None:
                    self.corners_draw['tr'].remove()
                    self.corners_draw['tr']=None
                self.corners_draw['tr'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('click on bottom right corner')
                self.mode = 'corners-br'
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-br':
                self.corners['br']=(x,y)
                if self.corners_draw['br'] is not None:
                    self.corners_draw['br'].remove()
                    self.corners_draw['br']=None
                self.corners_draw['br'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('click on bottom left corner')
                self.mode = 'corners-bl'
                self.ax_im.figure.canvas.draw()
                return
            elif self.mode == 'corners-bl':
                self.corners['bl']=(x,y)
                if self.corners_draw['bl'] is not None:
                    self.corners_draw['bl'].remove()
                    self.corners_draw['bl']=None
                self.corners_draw['bl'], = self.ax_im.plot(x,y,'ro')
                self.corners_text.set_text('BACKSPACE to reset. ENTER to confirm')
                self.mode = 'corners-done'
                self.ax_im.figure.canvas.draw()
                return

            if self.mode=='delete': #first check for pairing lines (we can only delete them)
                for index,(text,field) in enumerate(self.pairing):
                    #if within bounds of line and within distance from it
                    x1=(self.textBBs[text][0]+self.textBBs[text][2]+self.textBBs[text][4]+self.textBBs[text][6])/4
                    y1=(self.textBBs[text][1]+self.textBBs[text][3]+self.textBBs[text][5]+self.textBBs[text][7])/4
                    x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2]+self.fieldBBs[field][4]+self.fieldBBs[field][6])/4
                    y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3]+self.fieldBBs[field][5]+self.fieldBBs[field][7])/4

                    if x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/math.sqrt(pow(y2-y1,2.0) + pow(x2-x1,2.0)) < 9.5:
                        #delete the pairing
                        self.actionStack.append(('remove-pairing',text,field))
                        self.undoStack=[]
                        #self.pairLines[index].remove()
                        #self.ax_im.figure.canvas.draw()
                        #del self.pairLines[index]
                        del self.pairing[index]
                        self.draw()
                        return
            #then bbs
            for id in self.textBBs:
                if self.checkInside(x,y,self.textBBs[id]):
                    #print 'click on text b'
                    if self.mode=='delete':
                        #delete the text BB
                        pairs=[]#pairs this BB is part of
                        pairIds=[]
                        for i,pair in enumerate(self.pairing):
                            if id==pair[0]:
                                pairIds.append(i)
                                pairs.append(pair)
                        for i in pairIds:
                            del self.pairing[i]
                        self.actionStack.append(('remove-text',id)+self.textBBs[id]+(pairs,))
                        self.undoStack=[]
                        del self.textBBs[id]
                        if self.selected=='text' and self.selectedId==id:
                            self.selected='none'
                            self.setSelectedRectOff()

                    else:
                        #pair to prev selected?
                        if self.selected=='field' and (id,self.selectedId) not in self.pairing:
                            self.pairing.append((id,self.selectedId))
                            self.actionStack.append(('add-pairing',id,self.selectedId))
                            self.undoStack=[]
                        #select the text BB
                        self.selectedId=id
                        self.selected='text'
                        self.setSelectedRect(self.textBBs[id])
                    self.draw()
                    return

            for id in self.fieldBBs:
                if self.checkInside(x,y,self.fieldBBs[id]):
                    #print 'click on field b'
                    if self.mode=='delete':
                        #delete the field BB
                        pairs=[]#pairs this BB is part of
                        pairIds=[]
                        for i,pair in enumerate(self.pairing):
                            if id==pair[1]:
                                pairIds.append(i)
                                pairs.append(pair)
                        for i in pairIds:
                            del self.pairing[i]
                        self.actionStack.append(('remove-field',id)+self.fieldBBs[id]+(pairs,))
                        self.undoStack=[]
                        del self.fieldBBs[id]
                        if self.selected=='field' and self.selectedId==id:
                            self.selected='none'
                            self.setSelectedRectOff()

                    else:
                        #pair to prev selected?
                        if self.selected=='text' and (self.selectedId,id) not in self.pairing:
                            self.pairing.append((self.selectedId,id))
                            self.actionStack.append(('add-pairing',self.selectedId,id))
                            self.undoStack=[]
                        #select the field BB
                        self.selectedId=id
                        self.selected='field'
                        self.setSelectedRect(self.fieldBBs[id])
                    self.draw()
                    return

            if self.selected!='none':
                #print 'deselected'
                self.selected='none'

                self.setSelectedRectOff()
                self.ax_im.figure.canvas.draw()
                #draw(self)

    def clickerMove(self,event):           
        #moving only matters if the button is down and we've moved "enough"
        bbs = None
        if self.selected == 'field':
            bbs = self.fieldBBs
        elif self.selected == 'text':
            bbs = self.textBBs
        if '-d' == self.mode[-2:] and math.sqrt(pow(event.xdata-self.startX,2)+pow(event.ydata-self.startY,2))>2:
            if bbs is not None and self.checkInside(self.startX,self.startY,bbs[self.selectedId]):
                #we are going to adjust the selected BB, but how?
                #we see which point (corners and centerofmass) the click is closest to
                xc=(bbs[self.selectedId][0]+bbs[self.selectedId][2]+bbs[self.selectedId][4]+bbs[self.selectedId][6])/4
                yc=(bbs[self.selectedId][1]+bbs[self.selectedId][3]+bbs[self.selectedId][5]+bbs[self.selectedId][7])/4
                #w=bbs[self.selectedId][2]-bbs[self.selectedId][0] +1
                #h=bbs[self.selectedId][3]-bbs[self.selectedId][1] +1
                #leftBoundary = bbs[self.selectedId][0] + 0.5*w
                #rightBoundary = bbs[self.selectedId][0] + 0.5*w
                #topBoundary = bbs[self.selectedId][1] + 0.5*h
                #bottomBoundary = bbs[self.selectedId][1] + 0.5*h
                col=colorMap[self.mode[:-2]]

                closestDist = (self.startX-xc)**2 + (self.startY-yc)**2
                self.mode = self.mode[:-1]+'mv'
                
                dist = (self.startX-bbs[self.selectedId][0])**2 + (self.startY-bbs[self.selectedId][1])**2 #top-left corner
                if dist<closestDist:
                    self.mode = self.mode[:-2]+'tl'
                    closestDist = dist
                dist = (self.startX-bbs[self.selectedId][6])**2 + (self.startY-bbs[self.selectedId][7])**2 #bot-left corner
                if dist<closestDist:
                    self.mode = self.mode[:-2]+'bl'
                    closestDist = dist
                dist = (self.startX-bbs[self.selectedId][2])**2 + (self.startY-bbs[self.selectedId][3])**2 #top-right corner
                if dist<closestDist:
                    self.mode = self.mode[:-2]+'tr'
                    closestDist = dist
                dist = (self.startX-bbs[self.selectedId][4])**2 + (self.startY-bbs[self.selectedId][5])**2 #bot-right corner
                if dist<closestDist:
                    self.mode = self.mode[:-2]+'br'
                    closestDist = dist
                #elif self.startX<leftBoundary:#left
                #    self.mode = self.mode[:-1]+'l'
                #elif self.startX>rightBoundary:#right
                #    self.mode = self.mode[:-1]+'r'
                #elif self.startY<topBoundary:#top
                #    self.mode = self.mode[:-1]+'t'
                #elif self.startY<bottomBoundary:#bot
                #    self.mode = self.mode[:-1]+'b'
                self.drawRect.set_edgecolor(col)
            elif 'none' not in self.mode and 'delete' not in self.mode:
                col=DRAW_COLOR
                if self.mode[:-2] in colorMap:
                    col=colorMap[self.mode[:-2]]
                self.mode = self.mode[:-1]+'m'
                self.drawRect.set_edgecolor(col)
                self.drawRect.set_xy(np.array([[self.startX,self.startY],[self.startX,event.ydata],[event.xdata,event.ydata],[event.xdata,self.startY]]))
            else:
                self.mode = self.mode[:-2]
        if '-m' == self.mode[-2:]:
            self.endX=event.xdata
            self.endY=event.ydata
            self.drawRect.set_xy(np.array([[self.startX,self.startY],[self.startX,event.ydata],[event.xdata,event.ydata],[event.xdata,self.startY]]))
            self.ax_im.figure.canvas.draw()
            #draw(self)
        elif (self.mode[:6]!='corner' and
             (('-tl' == self.mode[-3:])or # and  event.xdata<bbs[self.selectedId][2] and event.ydata<bbs[self.selectedId][3]) or
              ('-bl' == self.mode[-3:])or # and  event.xdata<bbs[self.selectedId][2] and event.ydata>bbs[self.selectedId][1]) or
              ('-tr' == self.mode[-3:])or # and  event.xdata>bbs[self.selectedId][0] and event.ydata<bbs[self.selectedId][3]) or
              ('-br' == self.mode[-3:])or # and  event.xdata>bbs[self.selectedId][0] and event.ydata>bbs[self.selectedId][1]) or
              ('-l' == self.mode[-3:] )or # and  event.xdata<bbs[self.selectedId][2]) or
              ('-r' == self.mode[-3:] )or # and  event.xdata>bbs[self.selectedId][0]) or
              ('-t' == self.mode[-3:] )or # and  event.ydata<bbs[self.selectedId][3]) or
              ('-b' == self.mode[-3:] )or # and  event.ydata>bbs[self.selectedId][1]))):
              ('-mv' == self.mode[-3:] ))):
            self.endX=event.xdata
            self.endY=event.ydata
            tlX=bbs[self.selectedId][0]
            tlY=bbs[self.selectedId][1]
            trX=bbs[self.selectedId][2]
            trY=bbs[self.selectedId][3]
            brX=bbs[self.selectedId][4]
            brY=bbs[self.selectedId][5]
            blX=bbs[self.selectedId][6]
            blY=bbs[self.selectedId][7]
            if '-tl' == self.mode[-3:]:
                tlX=self.endX
                tlY=self.endY
            elif '-bl' == self.mode[-3:]:
                blX=self.endX
                blY=self.endY
            elif '-tr' == self.mode[-3:]:
                trX=self.endX
                trY=self.endY
            elif '-br' == self.mode[-3:]:
                brX=self.endX
                brY=self.endY
            elif '-mv' == self.mode[-3:]:
                shiftX=self.endX-self.startX
                shiftY=self.endY-self.startY
                tlX+=shiftX
                tlY+=shiftY
                blX+=shiftX
                blY+=shiftY
                trX+=shiftX
                trY+=shiftY
                brX+=shiftX
                brY+=shiftY
            self.drawRect.set_xy(np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]]))
            self.ax_im.figure.canvas.draw()
            #draw(self)

    def doKey(self,event):
        if self.mode=='change':
            key = event.key
            for mode in keyMap:
                if key==keyMap[mode] and self.selected[:4]==mode[:4]:
                    if self.selected=='text':
                        self.actionStack.append(('change-text',self.selectedId,self.textBBs[self.selectedId][4]))
                        self.textBBs[self.selectedId]=self.textBBs[self.selectedId][0:8]+(codeMap[mode],)+self.textBBs[self.selectedId][9:]
                    elif self.selected=='field':
                        self.actionStack.append(('change-field',self.selectedId,self.fieldBBs[self.selectedId][4]))
                        self.fieldBBs[self.selectedId]=self.fieldBBs[self.selectedId][0:8]+(codeMap[mode],)+self.fieldBBs[self.selectedId][9:]
                    self.draw()

            self.mode=self.tmpMode
            self.modeRect.set_y(toolYMap[self.mode])
            self.ax_tool.figure.canvas.draw()
            #drawToolbar(p)
        elif self.mode[:6] == 'corner':
            if event.key=='escape': #quit
                self.textBBs={}
                self.fieldBBs={}
                self.pairing=[]
                self.corners={}
                plt.close('all')
            elif event.key=='backspace':
                self.corners['tl']=None
                if self.corners_draw['tl'] is not None:
                    self.corners_draw['tl'].remove()
                    self.corners_draw['tl']=None
                self.corners['tr']=None
                if self.corners_draw['tr'] is not None:
                    self.corners_draw['tr'].remove()
                    self.corners_draw['tr']=None
                self.corners['br']=None
                if self.corners_draw['br'] is not None:
                    self.corners_draw['br'].remove()
                    self.corners_draw['br']=None
                self.corners['bl']=None
                if self.corners_draw['bl'] is not None:
                    self.corners_draw['bl'].remove()
                    self.corners_draw['bl']=None
                self.corners_text.set_text('click on the top left corner')
                self.mode='corners-tl'
                self.ax_im.figure.canvas.draw()
            elif event.key=='enter':
                if self.corners['tl'] is not None and self.corners['tr'] is not None and self.corners['br'] is not None and self.corners['bl'] is not None:
                    self.init()
        else:
            key = event.key
            if key in RkeyMap:
                newMode = RkeyMap[key]
                if self.mode != newMode:
                    self.mode = newMode
                    self.modeRect.set_y(toolYMap[self.mode])
                    self.ax_tool.figure.canvas.draw()
                    #print newMode
                    #drawToolbar(p)
            elif key=='escape': #quit
                plt.close('all')
            elif key=='f': #delete:
                if self.mode != 'delete':
                    self.modeRect.set_y(toolYMap['delete'])
                    self.ax_tool.figure.canvas.draw()
                    self.mode='delete'
                    #drawToolbar(p)
            elif key=='a': # undo
                self.undo()
            elif key=='s': #S redo
                self.redo()
            elif key=='d': #D change
                self.change()
            elif key=='z': # set field to print/stamp
                self.setFieldType(ftypeMap['print'])
            elif key=='x': # set field to blank
                self.setFieldType(ftypeMap['blank'])
            elif key=='c': # set field to handwriting (default)
                self.setFieldType(ftypeMap['handwriting'])
            elif key=='up':
                trans = np.array([[1,0,0],
                                  [0,1,-2],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='down':
                trans = np.array([[1,0,0],
                                  [0,1,2],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='left':
                trans = np.array([[1,0,-2],
                                  [0,1,0],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='right':
                trans = np.array([[1,0,2],
                                  [0,1,0],
                                  [0,0,1]])
                self.transAll(trans)
            elif key==',':#rotate
                t=-0.01
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[math.cos(t),-math.sin(t),-x*math.cos(t)+y*math.sin(t)+x],
                                  [math.sin(t),math.cos(t),-x*math.sin(t)-y*math.cos(t)+y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='.':#rotate
                t=0.01
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[math.cos(t),-math.sin(t),-x*math.cos(t)+y*math.sin(t)+x],
                                  [math.sin(t),math.cos(t),-x*math.sin(t)-y*math.cos(t)+y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='-':#scale
                t=0.97
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[t,0,x-t*x],
                                  [0,t,y-t*y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='=':#scale
                t=1.03
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[t,0,x-t*x],
                                  [0,t,y-t*y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='backspace':
                self.draw()

    #def updatePairLines(self):
    #    for i, pair in enumerate(self.pairing):
    #        if (self.selected=='text' and pair[0]==self.selectedId) or (self.selected=='field' and pair[1]==self.selectedId):
    #            x=(self.textBBs[pair[0]][2]+self.textBBs[pair[0]][0])/2
    #            y=(self.textBBs[pair[0]][3]+self.textBBs[pair[0]][1])/2
    #            xe=(self.fieldBBs[pair[1]][2]+self.fieldBBs[pair[1]][0])/2
    #            ye=(self.fieldBBs[pair[1]][3]+self.fieldBBs[pair[1]][1])/2
    #            #self.pairLines[i].set_x(x)
    #            #self.pairLines[i].set_y(y)
    #            #self.pairLines[i].set_dx(xe-x)
    #            #self.pairLines[i].set_dy(ye-y)
    #            self.pairLines[i].remove()
    #            self.pairLines[i]=patches.Arrow(x,y,xe-x,ye-y,2,edgecolor='g',facecolor='none')
    #            self.ax_im.add_patch(self.pairLines[i])



    def undo(self):
        if len(self.actionStack)>0:
            action = self.actionStack.pop()
            action = self.undoAction(action)

            self.undoStack.append(action)
            self.draw()

    def redo(self):
        if len(self.undoStack)>0:
            action = self.undoStack.pop()
            action = self.undoAction(action)

            self.actionStack.append(action)
            self.draw()

    def undoAction(self,action):
        if action[0] == 'add-pairing':
            #i = self.pairing.index((action[1],action[2]))
            self.pairing.remove((action[1],action[2]))
            #self.pairLines[i].remove()
            #del self.pairLines[i]
            #self.ax_im.figure.canvas.draw()
            return ('remove-pairing',action[1],action[2])
        elif action[0] == 'remove-pairing':
            self.pairing.append((action[1],action[2]))
            #self.pairLines[len(self.pairing)-1] = 
            return ('add-pairing',action[1],action[2])
        elif action[0] == 'add-text':
            id = action[1]
            pairs = action[-1]
            del self.textBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if self.selected=='text' and self.selectedId==id:
                self.selected='none'
            return ('remove-text',)+action[1:]
        elif action[0] == 'remove-text':
            id = action[1]
            pairs = action[-1]
            self.textBBs[id]=action[2:-1]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            return ('add-text',)+action[1:]
        elif action[0] == 'add-field':
            id = action[1]
            pairs = action[-1]
            del self.fieldBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if self.selected=='field' and self.selectedId==id:
                self.selected='none'
            return ('remove-field',)+action[1:]
        elif action[0] == 'remove-field':
            id = action[1]
            pairs = action[-1]
            self.fieldBBs[id]=action[2:-1]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            return ('add-field',)+action[1:]
        elif action[0] == 'drag-field':
            id = action[1]
            toRet = ('drag-field',id)+self.fieldBBs[id][0:8]
            self.fieldBBs[id] = action[2:]+self.fieldBBs[id][8:]
            return toRet
        elif action[0] == 'drag-text':
            id = action[1]
            toRet = ('drag-text',id)+self.textBBs[id][0:8]
            self.textBBs[id] = action[2:]+self.textBBs[id][8:]
            return toRet
        elif action[0] == 'change-text':
            label,id,code = action
            toRet = (label,id,self.textBBs[id][4])
            self.textBBs[id] = self.textBBs[id][0:8]+(code,)+self.textBBs[id][9:]
            return toRet
        elif action[0] == 'change-field':
            label,id,code = action
            toRet = (label,id,self.fieldBBs[id][4])
            self.fieldBBs[id] = self.fieldBBs[id][0:8]+(code,)+self.fieldBBs[id][9:]
            return toRet
        elif action[0] == 'set-field-type':#only occurs with fields
            label,id, ftype= action
            toRet = (label,id,self.fieldBBs[id][9])
            self.fieldBBs[id] = self.fieldBBs[id][0:9]+(ftype,)
            return toRet
        else:
            print 'Unimplemented action: '+action[0]

    def change(self):
            self.tmpMode = self.mode
            self.mode='change'
            self.modeRect.set_y(toolYMap['change'])
            self.ax_tool.figure.canvas.draw()
            #drawToolbar(p)

    def setFieldType(self,ftype):
        if self.selected=='field':
            self.actionStack.append(('set-field-type',self.selectedId,self.fieldBBs[self.selectedId][9]))
            self.fieldBBs[self.selectedId] = self.fieldBBs[self.selectedId][:9]+(ftype,)
            self.draw()

    def setSelectedRect(self,bb):
        xc=(bb[0]+bb[2]+bb[4]+bb[6])/4.0
        yc=(bb[1]+bb[3]+bb[5]+bb[7])/4.0
        size=10
        tld = size/math.sqrt((xc-bb[0])**2 + (yc-bb[1])**2)
        tlX = bb[0]+(bb[0]-xc)*tld
        tlY = bb[1]+(bb[1]-yc)*tld

        trd = size/math.sqrt((xc-bb[2])**2 + (yc-bb[3])**2)
        trX = bb[2]+(bb[2]-xc)*trd
        trY = bb[3]+(bb[3]-yc)*trd

        brd = size/math.sqrt((xc-bb[4])**2 + (yc-bb[5])**2)
        brX = bb[4]+(bb[4]-xc)*brd
        brY = bb[5]+(bb[5]-yc)*brd

        bld = size/math.sqrt((xc-bb[6])**2 + (yc-bb[7])**2)
        blX = bb[6]+(bb[6]-xc)*bld
        blY = bb[7]+(bb[7]-yc)*bld

        self.selectedRect.set_xy(np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]]))

    def setSelectedRectOff(self):
        self.selectedRect.set_xy(np.array([[0,0],[0.1,0],[0,0.1]]))

    def checkInside(self,x,y,bb):
        vertices = [(bb[0],bb[1]),(bb[2],bb[3]),(bb[4],bb[5]),(bb[6],bb[7])]
        point=(x,y)
        previous_side = None
        n_vertices = len(vertices)
        for n in xrange(n_vertices):
            a, b = vertices[n], vertices[(n+1)%n_vertices]
            affine_segment = v_sub(b, a)
            affine_point = v_sub(point, a)
            current_side = get_side(affine_segment, affine_point)
            if current_side is None:
                return False #outside or over an edge
            elif previous_side is None: #first segment
                previous_side = current_side
            elif previous_side != current_side:
                return False
        return True


    def draw(self):
        self.drawRect.set_xy(np.array([[0,0],[0.1,0],[0,0.1]]))
        if self.selected=='field':
            self.setSelectedRect(self.fieldBBs[self.selectedId])
        elif self.selected=='text':
            self.setSelectedRect(self.textBBs[self.selectedId])
        else:
            self.setSelectedRectOff()
        #clear all
        #print self.textRects
        #print self.textBBs
        for id,rect in self.textRects.iteritems():
            rect.remove()
        self.textRects={}
        for id,rect in self.fieldRects.iteritems():
            rect.remove()
        self.fieldRects={}
        for id,line in self.pairLines.iteritems():
            line.remove()
        self.pairLines={}

        #self.displayImage[0:self.image.shape[0], 0:self.image.shape[1]] = self.image
        for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,code,blank) in self.textBBs.iteritems():
            #cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
            self.textRects[id] = patches.Polygon(np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]]),linewidth=2,edgecolor=colorMap[RcodeMap[code]],facecolor='none')
            self.ax_im.add_patch(self.textRects[id])

        for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,code,ftype) in self.fieldBBs.iteritems():
            #cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
            fill = 'none'
            if ftype==ftypeMap['blank']:
                fill=(0.9,0.9,0.9,0.55)
            elif ftype==ftypeMap['print']:
                fill=(0.9,0.3,0.5,0.25)
            self.fieldRects[id] = patches.Polygon(np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]]),linewidth=2,edgecolor=colorMap[RcodeMap[code]],facecolor=fill)
            self.ax_im.add_patch(self.fieldRects[id])
            #if blank==1:
            #    w = endX-startX
            #    h = endY-startY
            #    cv2.rectangle(self.displayImage,(startX+2,startY+2),(endX-2,endY-2),(240,240,240),1)
            #    cv2.rectangle(self.displayImage,(int(startX+0.25*w),int(startY+0.25*h)),(int(endX-0.25*w),int(endY-0.25*h)),(240,240,240),1)
            #    cv2.rectangle(self.displayImage,(int(startX+0.15*w),int(startY+0.15*h)),(int(endX-0.15*w),int(endY-0.15*h)),(240,240,240),1)
            #    cv2.rectangle(self.displayImage,(int(startX+0.35*w),int(startY+0.35*h)),(int(endX-0.35*w),int(endY-0.35*h)),(240,240,240),1)

        id=0
        for text,field in self.pairing:
            x1=(self.textBBs[text][0]+self.textBBs[text][2]+self.textBBs[text][4]+self.textBBs[text][6])/4
            y1=(self.textBBs[text][1]+self.textBBs[text][3]+self.textBBs[text][5]+self.textBBs[text][7])/4
            x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2]+self.fieldBBs[field][4]+self.fieldBBs[field][6])/4
            y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3]+self.fieldBBs[field][5]+self.fieldBBs[field][7])/4
            #cv2.line(self.displayImage,(x1,y1),(x2,y2),(0,255,0),1)
            self.pairLines[id]=patches.Arrow(x1,y1,x2-x1,y2-y1,2,edgecolor='g',facecolor='none')
            self.ax_im.add_patch(self.pairLines[id])
            id+=1

        #if self.selected == 'text':
        #    self.selectedRect.set_bounds(self.startX-4,self.startY-4,self.endX-self.startX+8,self.endY-self.startY+8)
        #    startX,startY,endX,endY,para,blank = self.textBBs[self.selectedId]
        #    if self.mode[-3:]=='-tl':
        #        cv2.rectangle(self.displayImage,(self.endX,self.endY),(max(startX,endX),max(startY,endY)),(255,240,100),1)
        #    elif self.mode[-3:]=='-tr':
        #        cv2.rectangle(self.displayImage,(startX,self.endY),(self.endX,endY),(255,240,100),1)
        #    elif self.mode[-3:]=='-bl':
        #        cv2.rectangle(self.displayImage,(self.endX,startY),(endX,self.endY),(255,240,100),1)
        #    elif self.mode[-3:]=='-br':
        #        cv2.rectangle(self.displayImage,(startX,startY),(self.endX,self.endY),(255,240,100),1)
        #    cv2.rectangle(self.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)
        #elif self.selected == 'field':
        #    startX,startY,endX,endY,para,blank = self.fieldBBs[self.selectedId]
        #    if self.mode[-3:]=='-tl':
        #        cv2.rectangle(self.displayImage,(self.endX,self.endY),(max(startX,endX),max(startY,endY)),(120,255,255),1)
        #    elif self.mode[-3:]=='-tr':
        #        cv2.rectangle(self.displayImage,(startX,self.endY),(self.endX,endY),(120,255,255),1)
        #    elif self.mode[-3:]=='-bl':
        #        cv2.rectangle(self.displayImage,(self.endX,startY),(endX,self.endY),(120,255,255),1)
        #    elif self.mode[-3:]=='-br':
        #        cv2.rectangle(self.displayImage,(startX,startY),(self.endX,self.endY),(120,255,255),1)
        #    cv2.rectangle(self.displayImage,(min(startX,endX)-2,min(startY,endY)-2),(max(startX,endX)+2,max(startY,endY)+2),(255,0,255),1)

        #if self.mode[-2:]=='-m':
        #    cv2.rectangle(self.displayImage,(self.startX,self.startY),(self.endX,self.endY),colorMap[self.mode[:-2]],1)

        #cv2.imshow("labeler",self.displayImage)
        self.ax_im.figure.canvas.draw()

def drawToolbar(ax):
    #im[0:,-TOOL_WIDTH:]=(140,140,140)
    im = np.zeros(((toolH+1)*(len(modes)+9),TOOL_WIDTH,3),dtype=np.uint8)
    im[:,:] = (140,140,140)

    y=0

    for mode in modes:
        im[y:y+toolH,:]=(255*colorMap[mode][0],255*colorMap[mode][1],255*colorMap[mode][2])
        #if self.mode==mode:
        #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-1,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
        #cv2.putText(im,toolMap[mode],(im.shape[1]TOOL_WIDTH-3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        #patches.Polygon((,linewidth=2,edgecolor=colorMap[mode],facecolor=fill)
        ax.text(1,y+toolH-10,toolMap[mode])
        toolYMap[mode]=y
        y+=toolH+1

    #undo
    im[y:y+toolH,:]=(160,160,160)
    ax.text(1,y+toolH-10,'A:undo')
    y+=toolH+1

    #redo
    im[y:y+toolH,:]=(190,190,190)
    ax.text(1,y+toolH-10,'S:redo')
    y+=toolH+1

    #change
    im[y:y+toolH,:]=(230,230,230)
    #if self.mode=='change':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-10,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-10,'D:switch type')
    toolYMap['change']=y
    y+=toolH+1

    #delete
    im[y:y+toolH,:]=(250,250,250)
    #if self.mode=='delete':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-10,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-10,'F:delete')
    toolYMap['delete']=y
    y+=toolH+1

    #print
    im[y:y+toolH,:]=(255, 230, 242)
    ax.text(1,y+toolH-10,'Z:mark field as print')
    toolYMap['print']=y
    y+=toolH+1

    #blank
    im[y:y+toolH,:]=(250,250,250)
    #if self.mode=='blank':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-10,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    #cv2.putText(im,'Z:mark blank',(im.shape[1]TOOL_WIDTH-3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(240,240,240))
    ax.text(1,y+toolH-10,'X:mark field as blank')
    toolYMap['blank']=y
    y+=toolH+1

    #handwriting
    im[y:y+toolH,:]=(190,190,190)
    ax.text(1,y+toolH-10,'C:mark field as handwriting')
    toolYMap['handwriting']=y
    y+=toolH+1

    #move
    im[y:y+toolH,:]=(30,30,30)
    ax.text(1,y+toolH-10,'Arrow keys:move all labels', color=(1,1,1))
    toolYMap['move']=y
    y+=toolH+1

    #rotate
    im[y:y+toolH,:]=(30,30,30)
    ax.text(1,y+toolH-10,'<,>:rotate all labels', color=(1,1,1))
    toolYMap['rotate']=y
    y+=toolH+1

    #scale
    im[y:y+toolH,:]=(30,30,30)
    ax.text(1,y+toolH-10,'-,+:scale all labels', color=(1,1,1))
    toolYMap['scale']=y
    y+=toolH+1

    return im

    #cv2.imshow("labeler",self.displayImage)
        

def labelImage(imagePath,texts,fields,pairs,page_corners):
    #p = Params()
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
    ax_im.set_axis_off()
    ax_im.imshow(image,cmap='gray')
    ax_tool = plt.subplot(gs[1])
    ax_tool.set_axis_off()
    toolImage = drawToolbar(ax_tool)
    ax_tool.imshow(toolImage)
    ax_im.figure.canvas.mpl_disconnect(fig.canvas.manager.key_press_handler_id)
    control = Control(ax_im,ax_tool,image.shape[1],image.shape[0],texts,fields,pairs,page_corners)
    #control.draw()
    plt.show()


    idToIdxText={}
    textBBs=[]
    for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in control.textBBs.iteritems():
        idToIdxText[id]=len(textBBs)
        textBBs.append((int(round(tlX)),int(round(tlY)),int(round(trX)),int(round(trY)),int(round(brX)),int(round(brY)),int(round(blX)),int(round(blY)),para))
    idToIdxField={}
    fieldBBs=[]
    for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in control.fieldBBs.iteritems():
        idToIdxField[id]=len(fieldBBs)
        fieldBBs.append((int(round(tlX)),int(round(tlY)),int(round(trX)),int(round(trY)),int(round(brX)),int(round(brY)),int(round(blX)),int(round(blY)),para,blank))
    pairing=[]
    for text,field in control.pairing:
        pairing.append((idToIdxText[text],idToIdxField[field]))

    return textBBs, fieldBBs, pairing, control.corners

texts=None
fields=None
pairs=None
page_corners=None
if len(sys.argv)>4:
    with open(sys.argv[4]) as f:
        read = json.loads(f.read())
        texts=read['textBBs']
        fields=read['fieldBBs']
        pairs=read['pairs']
        page_corners=read['page_corners']

texts,fields,pairs,corners = labelImage(sys.argv[1],texts,fields,pairs,page_corners)
outFile='test.json'
if len(texts)+len(fields)+len(corners)>0:
    with open(outFile,'w') as out:
        out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "page_corners":corners}))
