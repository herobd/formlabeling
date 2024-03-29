import sys
#import cv2
from matplotlib import pyplot as plt
import matplotlib.image as mpimg
import matplotlib.patches as patches
from matplotlib import gridspec
import numpy as np
import math
import json
from collections import defaultdict
from random import shuffle

#Globals
mouse_button=3
TOOL_WIDTH=320
toolH=40
MAX_ARR_LEN=200
BOX_MIN_AREA=200
MIN_MOVE_DIST=5
colorMap = {'text':(0/255.0,0/255.0,255/255.0,0.51), 'textP':(0/255.0,150/255.0,255/255.0,0.51), 'textMinor':(80/255.0,170/255.0,190/255.0,0.65), 'textInst':(170/255.0,160/255.0,225/255.0,0.71), 'textNumber':(0/255.0,160/255.0,100/255.0,0.51), 'fieldCircle':(255/255.0,190/255.0,210/255.0,0.61), 'field':(255/255.0,0/255.0,0/255.0,0.51), 'fieldP':(255/255.0,120/255.0,0/255.0,0.51), 'fieldCheckBox':(255/255.0,220/255.0,0/255.0,0.51), 'graphic':(255/255.0,105/255.0,250/255.0,0.51), 'comment':(165/255.0,10/255.0,15/255.0,0.51), 'pair':(15/255.0,150/255.0,15/255.0,0.51), 'col':(5/255.0,70/255.0,5/255.0,0.35), 'row':(25/255.0,5/255.0,75/255.0,0.35), 'fieldRegion':(15/255.0,15/255.0,75/255.0,0.51), 'fieldCol':(65/255.0,70/255.0,5/255.0,0.65), 'fieldRow':(65/255.0,5/255.0,75/255.0,0.65), 'move':(1,0,1,0.5), 'trans':(0.5,0.5,0.5)}
DRAW_COLOR=(1,0.7,1)
codeMap = {'text':0, 'textP':1, 'textMinor':2, 'textInst':3, 'textNumber':4, 'fieldCircle':5, 'field':6, 'fieldP':7, 'fieldCheckBox':8, 'graphic':9, 'comment':10, 'fieldRegion':11, 'fieldCol':12, 'fieldRow':13, 'detectorPrediction':14}
RcodeMap = {v: k for k, v in codeMap.items()}
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
          'fieldCol':'u',
          'fieldRow':'i',
          'fieldRegion':'`',
          #'col':'6',
          #'row':'7',
          }
RkeyMap = {v: k for k, v in keyMap.items()}
toolMap = {'text':'1:text/label', 'textP':'2:text para', 'textMinor':'3:minor label', 'textInst':'4:instructions', 'textNumber':'5:enumeration (#)', 'fieldCircle':'R:to be circled', 'field':'Q:field', 'fieldP':'W:field para', 'fieldCheckBox':'E:check-box', 'graphic':'T:graphic', 'comment':'Y:comment', 'fieldRegion':'~:Partitioned region', 'fieldCol':'U:col (cells)', 'fieldRow':'I:row (cells)','trans':'F1:transcribe'}
toolYMap = {}
modes = ['text', 'textP', 'textMinor', 'textInst', 'textNumber', 'field', 'fieldP', 'fieldCheckBox', 'fieldCircle', 'graphic', 'comment', 'fieldCol', 'fieldRow', 'fieldRegion', 'trans']
ftypeMap = {'text':0, 'handwriting':1, 'print':2, 'blank':3, 'signature':4} #print:typewriter or stamp
RftypeMap = {v: k for k, v in ftypeMap.items()}

def invalidPoly(points):
    def getQuad(a):
        if a<-0.5*math.pi:
            return 0
        elif a<0:
            return 1
        elif a<0.5*math.pi:
            return 2
        else:
            return 3
    #we check if every angle is positive
    for i in range(len(points)):
        m = np.array(points[i])
        f = np.array(points[i-1])
        s = np.array(points[(i+1)%len(points)])
        f-=m #conver to vector
        s-=m
        a2 = math.atan2(f[1],f[0])
        a1 = math.atan2(s[1],s[0])
        #print('{} and {}'.format(f,s))
        #c = np.dot(f,s)/np.linalg.norm(f)/np.linalg.norm(s)
        #angle = np.arccos(c)
        #print('c {}, a {}'.format(c,angle))
        #if not angle>0:
        q1 = getQuad(a1)
        q2 = getQuad(a2)
        if q2>q1 or (q1<2 and q2<2) or (q1>1 and q2>1):
            diff = a2-a1
        elif (q1==3 or q1==2) and (q2==1 or q2==0):
            diff = (a2+2*math.pi)-a1
        else:
            print(('error, unaccounted quads: q1={} q2={}'.format(q1,q2)))
            exit()
        if diff<=0 or diff>=math.pi:
            return True
    return False


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

def onLine(x,y,x1,y1,x2,y2):
     return x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/math.sqrt(pow(y2-y1,2.0) + pow(x2-x1,2.0)) < 9.5

def checkInsidePoly(x,y,vertices):
    point=(x,y)
    previous_side = None
    n_vertices = len(vertices)
    for n in range(n_vertices):
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

class Group:
    def __init__(self,typeStr=None,holdsFields=None,json=None):
        self.typeStr=typeStr
        self.holdsFields=holdsFields
        self.elements=set()
        self.pairings=set()
        self.samePairings=set()

        if json is not None:
            self.typeStr=json['type']
            self.holdsFields=json['holds']=='field'
            typ= 'f' if self.holdsFields else 't'
            self.elements=set( int(x[1:]) for x in json['elements'] if x[0]==typ)
            self.pairings=set(int(x[1:]) for x in json['pairings'] if x[0]!=typ)
            self.samePairings=set(int(x[1:]) for x in json['samePairings'] if x[0]==typ)

    def contains(self,index):
        return index in self.elements

    def add(self,index):
        self.elements.add(index)

    def remove(self,index):
        if index in self.elements:
            self.elements.remove(index)
            return True
        else:
            return False

    def pair(self,index,normal):
        if normal:
            self.pairings.add(index)
        else:
            self.samePairings.add(index)

    def unpair(self,index,normal):
        if normal:
            self.pairings.remove(index)
        else:
            self.samePairings.remove(index)

    def getPoly(self,control):
        if not self.holdsFields:
            bbs=control.textBBs
        else:
            bbs=control.fieldBBs

        minX=9999999
        maxX=-1
        minY=9999999
        maxY=-1

        for idx in self.elements:
            if idx in bbs: #check in case element was deleted
                maxX = max(maxX,bbs[idx][0],bbs[idx][2],bbs[idx][4],bbs[idx][6])
                minX = min(minX,bbs[idx][0],bbs[idx][2],bbs[idx][4],bbs[idx][6])
                maxY = max(maxY,bbs[idx][1],bbs[idx][3],bbs[idx][5],bbs[idx][7])
                minY = min(minY,bbs[idx][1],bbs[idx][3],bbs[idx][5],bbs[idx][7])

        minX-=3
        minY-=3
        maxX+=3
        maxY+=3

        return [(minX,minY), (minX,maxY), (maxX,maxY), (maxX,minY)]

    def getCentroid(self,control):
        if not self.holdsFields:
            bbs=control.textBBs
        else:
            bbs=control.fieldBBs
        x=0
        y=0
        count=0
        
        for idx in self.elements:
            if idx in bbs: #check in case element was deleted
                count+=1
                x+=bbs[idx][0]+bbs[idx][2]+bbs[idx][4]+bbs[idx][6]
                y+=bbs[idx][1]+bbs[idx][3]+bbs[idx][5]+bbs[idx][7]
        if count==0:
            return -1,-1

        return x/(4*count), y/(4*count)


class Control:
    def __init__(self,ax_im,ax_tool,W,H,texts,fields,pairs,samePairs,horzLinks,groups,transcriptions,pre_corners,page_corners=None, page_cornersActual=None):
        #print(page_corners)
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
        self.keyup_cid = self.ax_im.figure.canvas.mpl_connect(
                            'key_release_event', self.doKeyUp)
        self.mode='corners' #this indicates the 'state'
        self.secondaryMode=None
        self.resizeMode='edges'
        self.shiftAmount=4
        self.textBBs={} #this holds each text box as (x1,y1,x2,y2,x3,y3,x4,y4,type_code,filltype).  filltype is always 0
        self.textRects={} #this holds the drawing patches
        self.fieldBBs={} #this holds each field box as (x1,y1,x2,y2,x3,y3,x4,y4,type_code,filltype). filltype is according to ftypeMap
        self.fieldRects={} #this holds the drawing patches
        self.textBBCurId=0
        self.fieldBBCurId=0
        self.pairing=[] #this holds each pairing as a tuple (textId,fieldId)
        self.pairLines={} #this holds drawing patches for ALL pairlines (samePairs and group pairings)
        self.horzLinks={} #this is a special pairing indicating that a series of bbs form a single horz line. Represented as arrays of ids
        self.transcriptions=defaultdict(lambda: '') #holds transcriptions for the boxes, uses "t#"/"f#" id notation
        if transcriptions is not None:
            self.transcriptions.update(transcriptions)
        self.transText={} #holds drawing elements for text
        self.transLoc='up'
        self.selectedText=None
        self.cur_hlid=0
        self.samePairing=[] #this holds each pairing between two of the same type as a tuple (Id,Id,bool_field)
        self.groups={} #groups are rows or columns
        self.groupCurId=0
        self.groupPolys={} #for drawing
        self.arrowPolys=[]
        self.selectedRects=[] #for drawing in move mode
        self.corners={'tl':None, 'tr':None, 'br':None, 'bl':None}
        self.cornersActual=None
        self.corners_draw=defaultdict(lambda: None) #{'tl':None, 'tr':None, 'br':None, 'bl':None}
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
        self.preCorners=pre_corners
        self.complete=False #this is for returning whether the user is done labeling
        if pairs is not None:
            self.pairing=[(int(x[1:]),int(y[1:])) for (x,y) in pairs if ((x[0]=='t' and y[0]=='f') or (x[0]=='m' and u[0]=='m'))]
            switched = [(int(y[1:]),int(x[1:])) for (x,y) in pairs if (x[0]=='f' and y[0]=='t')]
            if len(switched)>0:
                self.pairing += switched
        if samePairs is not None:
            self.samePairing=[(int(x[1:]),int(y[1:]),(1 if x[0]=='f' else 0)) for (x,y) in samePairs if x[0]==y[0]]
        self.corners_text = ax_im.text(W/2,H/2,'Mark the page corners OR WHERE THEY SHOULD BE, then press ENTER.\n(outer corners if two pages).\nIf odd position, press BACKSPACE for corner by corner query.',horizontalalignment='center',verticalalignment='center', color='red')
        if horzLinks is not None:
            for link in horzLinks:
                self.horzLinks[self.cur_hlid]=link
                #print('{}: {}'.format(self.cur_hlid,link))
                self.cur_hlid+=1
        self.ax_im.figure.canvas.draw()
        self.imageW=W
        self.imageH=H

        if groups is not None:
            for group in groups:
                self.groups[self.groupCurId] = Group(json=group)
                self.groupCurId+=1

        if page_corners is not None:
            self.corners=page_corners
            self.preCorners=page_corners
            self.cornersActual=page_cornersActual
            self.init()
        #elif TEST:
        #    self.corners=[


    def init(self):
        self.corners_text.remove()
        for key, dot in self.corners_draw.items():
            dot.remove()
        if self.preTexts is not None and self.preFields is not None:
            if self.preCorners is None:
                self.preCorners = self.corners
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

            for bb in self.preTexts:
                if invalidPoly(bb['poly_points']):
                    continue
                tlX,tlY = bb['poly_points'][0]
                trX,trY = bb['poly_points'][1]
                brX,brY = bb['poly_points'][2]
                blX,blY = bb['poly_points'][3]
                para = codeMap[bb['type']]
                old_corners = np.array([[tlX,trX,brX,blX],
                                        [tlY,trY,brY,blY],
                                        [1,1,1,1]])
                new_points = np.matmul(trans,old_corners)
                new_points/=new_points[2,:] #bring back to standard homogeneous form
                #startX = (new_points[0,0]+new_points[0,3])/2.0 #average x of new tl and bl
                #startY = (new_points[1,0]+new_points[1,1])/2.0 #average y of new tl and tr
                #endX = (new_points[0,1]+new_points[0,2])/2.0 #average x of new tr and br
                #endY = (new_points[1,2]+new_points[1,3])/2.0 #average y of new br and bl
                #self.textBBs[self.bbCurId] = (int(round(startX)),int(round(startY)),int(round(endX)),int(round(endY)),para,0)
                id = int(bb['id'][1:])
                assert(bb['id'][0]=='t')
                self.textBBs[id] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,0)
                self.textBBCurId=max(self.textBBCurId,id+1)
            for bb in self.preFields:
                if invalidPoly(bb['poly_points']):
                    continue
                id = int(bb['id'][1:])
                assert(bb['id'][0]=='f')
                tlX,tlY = bb['poly_points'][0]
                trX,trY = bb['poly_points'][1]
                brX,brY = bb['poly_points'][2]
                blX,blY = bb['poly_points'][3]
                para = codeMap[bb['type']]
                blank = int(bb['isBlank'])
                old_corners = np.array([[tlX,trX,brX,blX],
                                        [tlY,trY,brY,blY],
                                        [1,1,1,1]])
                new_points = np.matmul(trans,old_corners)
                new_points/=new_points[2,:]
                self.fieldBBs[id] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,blank)
                self.fieldBBCurId=max(self.fieldBBCurId,id+1)
            #self.pairing=pairs
        self.mode='text'
        self.modeRect = patches.Rectangle((0,0),TOOL_WIDTH,toolH,linewidth=2,edgecolor=(1,0,1),facecolor='none')
        self.ax_tool.add_patch(self.modeRect)
        self.secondaryModeRect = patches.Rectangle((0,0),TOOL_WIDTH,toolH,linewidth=2,edgecolor=(1,1,0),facecolor='none')
        self.secondaryModeRect.set_visible(False)
        self.ax_tool.add_patch(self.secondaryModeRect)
        self.ax_tool.figure.canvas.draw()
        self.selectedRect = patches.Polygon(np.array([[0,0],[0.1,0],[0,0.1]]),linewidth=2,edgecolor=(1,0,1),facecolor='none')
        self.ax_im.add_patch(self.selectedRect)
        self.drawRect = patches.Polygon(np.array([[0,0],[0.1,0],[0,0.1]]),linewidth=2,edgecolor=(1,1,1),facecolor='none')
        self.ax_im.add_patch(self.drawRect)
        #self.ax_im.figure.canvas.draw()
        self.moveTrans()
        self.draw()

    #applies the given transformation to every BB specified by Ids. Or all BBs if none
    def transAll(self,trans, textIds=None, fieldIds=None, recordAction=True):
        if textIds is None:
            if self.mode != 'move':
                textIds = list(self.textBBs.keys())
                fieldIds = list(self.fieldBBs.keys())
            else:
                textIds=list(self.selectedTextIds)
                fieldIds=list(self.selectedFieldIds)
        for id in textIds:
            tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank = self.textBBs[id]
            old_corners = np.array([[tlX,trX,brX,blX],
                                    [tlY,trY,brY,blY],
                                    [1.0,1.0,1.0,1.0]], dtype='float')
            new_points = np.matmul(trans,old_corners)
            new_points/=new_points[2,:] #bring back to standard homogeneous form
            self.textBBs[id] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,0)
        for id in fieldIds:
            tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank = self.fieldBBs[id]
            old_corners = np.array([[tlX,trX,brX,blX],
                                    [tlY,trY,brY,blY],
                                    [1,1,1,1]])
            new_points = np.matmul(trans,old_corners)
            new_points/=new_points[2,:] #bring back to standard homogeneous form
            self.fieldBBs[id] = (int(round(new_points[0,0])),int(round(new_points[1,0])),int(round(new_points[0,1])),int(round(new_points[1,1])),int(round(new_points[0,2])),int(round(new_points[1,2])),int(round(new_points[0,3])),int(round(new_points[1,3])),para,blank)

        self.draw()
    
        if recordAction:
            if len(self.actionStack)>0 and self.actionStack[-1][0]=='trans' and self.actionStack[-1][1]==textIds and self.actionStack[-1][2]==fieldIds:
                #if the last action was a trans on the same set, we'll combine them to one action
                trans = np.matmul(trans,self.actionStack[-1][3]) #the trans on the stack is left becuse it occured first
                self.actionStack.pop()
            self.didAction(('trans',textIds,fieldIds,trans))

    def selectAllInRect(self,xa,ya,xb,yb):
        x0 = min(xa,xb)
        x1 = max(xa,xb)
        y0 = min(ya,yb)
        y1 = max(ya,yb)

        def checkDim(tup,indicies,v0,v1):
            for index in indicies:
                #print '  {}: {}< {}'.format(index,tup[index]<v0,tup[index]>v1)
                if tup[index]<v0 or tup[index]>v1:
                    return False
            return True


        def checkBBs(bbs,x0,y0,x1,y1):
            ret=[]
            for id in bbs:
                #print id
                #print checkDim(bbs[id],[0,2,4,6],x0,x1)
                #print checkDim(bbs[id],[1,3,5,7],y0,y1)
                if checkDim(bbs[id],[0,2,4,6],x0,x1) and checkDim(bbs[id],[1,3,5,7],y0,y1):
                    ret.append(id)
            return ret
        
        self.selectedTextIds=checkBBs(self.textBBs,x0,y0,x1,y1)
        self.selectedFieldIds=checkBBs(self.fieldBBs,x0,y0,x1,y1)
        self.drawSelected()

            

    def clickerDown(self,event):
        #image,displayImage,mode,textBBs,fieldBBs,pairing = param
        if event.inaxes!=self.ax_im.axes or event.button!=mouse_button: return
        if self.mode=='trans':
            return
        if self.mode!='delete' and 'corner' not in self.mode:
            self.mode+='-d'
            self.startX=event.xdata
            self.startY=event.ydata

    def clickerUp(self,event):
        if event.button!=mouse_button: return
        if event.inaxes!=self.ax_im.axes:
            self.selected='none'
            self.setSelectedRectOff()
            if '-d' == self.mode[-2:] or '-m' == self.mode[-2:]:
                self.mode=self.mode[:-2]
            return
        x=event.xdata
        y=event.ydata
        if '-m' == self.mode[-2:]: #we dragged to make a box
            self.drawRect.set_xy(np.array([[0,0],[0.1,0],[0,0.1]]))
            self.mode=self.mode[:-2] #make state readable

            if self.mode=='move':
                if abs((self.startX-self.endX)*(self.startY-self.endY))>BOX_MIN_AREA: #the box is "big enough"
                    self.selectAllInRect(self.startX,self.startY,self.endX,self.endY)
                return

            if abs((self.startX-self.endX)*(self.startY-self.endY))>BOX_MIN_AREA: #the box is "big enough"
                didPair=None #for storing auto-pair for undo/action stack

                #auto-pair to selected
                if 'text' in self.mode and 'field' in self.selected:
                    self.pairing.append((self.textBBCurId,self.selectedId))
                    didPair=[(self.textBBCurId,self.selectedId)]
                elif 'field' in self.mode and 'text' in self.selected:
                    self.pairing.append((self.selectedId,self.fieldBBCurId))
                    didPair=[(self.selectedId,self.fieldBBCurId)]

                code = codeMap[self.mode]
                #selX=None
                #selY=None
                #selH=None
                #selW=None
                sv=(min(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),min(self.startY,self.endY),max(self.startX,self.endX),max(self.startY,self.endY),min(self.startX,self.endX),max(self.startY,self.endY),code)
                
                if self.mode[:4]=='text':
                    self.textBBs[self.textBBCurId]=sv+(0,)
                    newId=self.textBBCurId
                    self.didAction(('add-text',self.textBBCurId,)+sv+(0,didPair,None,))
                    if self.secondaryMode is None:
                        self.selectedId=self.textBBCurId
                        self.selected='text'
                    self.textBBCurId+=1
                else: #self.mode[:5]=='field':
                    self.fieldBBs[self.fieldBBCurId]=sv+(1,)
                    newId=self.fieldBBCurId
                    self.didAction(('add-field',self.fieldBBCurId,)+sv+(1,didPair,None,))
                    if self.secondaryMode is None:
                        self.selectedId=self.fieldBBCurId
                        self.selected='field'
                    self.fieldBBCurId+=1

                if self.secondaryMode=='row' or self.secondaryMode=='col':
                    if self.selected!='none' and (self.mode[:4]=='text') != self.groups[self.selectedId].holdsFields:
                        #add to group
                        self.groups[self.selectedId].add(newId)
                        self.didAction(('added-to-group',self.selectedId,newId))
                    else:
                        #new group!
                        self.groups[self.groupCurId] = Group(typeStr=self.secondaryMode, holdsFields=self.mode[:4]!='text')
                        self.groups[self.groupCurId].add(newId)
                        self.didAction(('add-group',self.groupCurId,self.groups[self.groupCurId]))
                        self.selected=self.secondaryMode
                        self.selectedId=self.groupCurId
                        #self.setSelectedPoly(self.groups[self.groupCurId].getPoly(self))
                        self.groupCurId+=1
                #else:
                   #self.setSelectedRect(sv)
            self.draw()

        elif 'corners' in self.mode:
            if self.mode=='corners':
                cornersStore=self.corners
            else:
                cornersStore=self.cornersActual
            self.ax_im.set_xlim(0,self.imageW)
            self.ax_im.set_ylim(self.imageH,0)
            if x<=self.imageW/2 and y<=self.imageH/2:
                cornersStore['tl']=(x,y)
                if self.corners_draw['tl'] is not None:
                    self.corners_draw['tl'].remove()
                    self.corners_draw['tl']=None
                self.corners_draw['tl'], = self.ax_im.plot(x,y,'ro')
            elif x>self.imageW/2 and y<=self.imageH/2:
                cornersStore['tr']=(x,y)
                if self.corners_draw['tr'] is not None:
                    self.corners_draw['tr'].remove()
                    self.corners_draw['tr']=None
                self.corners_draw['tr'], = self.ax_im.plot(x,y,'ro')
            elif x>self.imageW/2 and y>self.imageH/2:
                cornersStore['br']=(x,y)
                if self.corners_draw['br'] is not None:
                    self.corners_draw['br'].remove()
                    self.corners_draw['br']=None
                self.corners_draw['br'], = self.ax_im.plot(x,y,'ro')
            elif x<=self.imageW/2 and y>self.imageH/2:
                cornersStore['bl']=(x,y)
                if self.corners_draw['bl'] is not None:
                    self.corners_draw['bl'].remove()
                    self.corners_draw['bl']=None
                self.corners_draw['bl'], = self.ax_im.plot(x,y,'ro')

            if cornersStore['tl'] is not None and cornersStore['tr'] is not None:
                if self.corners_draw['tl-tr'] is not None:
                    self.corners_draw['tl-tr'].remove()
                self.corners_draw['tl-tr'], =self.ax_im.plot([cornersStore['tl'][0],cornersStore['tr'][0]],[cornersStore['tl'][1],cornersStore['tr'][1]],'r-')
            if cornersStore['br'] is not None and cornersStore['tr'] is not None:
                if self.corners_draw['br-tr'] is not None:
                    self.corners_draw['br-tr'].remove()
                self.corners_draw['br-tr'], =self.ax_im.plot([cornersStore['br'][0],cornersStore['tr'][0]],[cornersStore['br'][1],cornersStore['tr'][1]],'r-')
            if cornersStore['tl'] is not None and cornersStore['bl'] is not None:
                if self.corners_draw['tl-bl'] is not None:
                    self.corners_draw['tl-bl'].remove()
                self.corners_draw['tl-bl'], =self.ax_im.plot([cornersStore['tl'][0],cornersStore['bl'][0]],[cornersStore['tl'][1],cornersStore['bl'][1]],'r-')
            if cornersStore['br'] is not None and cornersStore['bl'] is not None:
                if self.corners_draw['br-bl'] is not None:
                    self.corners_draw['br-bl'].remove()
                self.corners_draw['br-bl'], =self.ax_im.plot([cornersStore['br'][0],cornersStore['bl'][0]],[cornersStore['br'][1],cornersStore['bl'][1]],'r-')

            self.ax_im.figure.canvas.draw()
        elif 'corner' in self.mode and '-' in self.mode:
            if 'Actual' in self.mode:
                cornersStore=self.cornersActual
            else:
                cornersStore=self.corners
            curCorner = self.mode[-2:]
            cornersStore[curCorner]=(x,y)
            if self.corners_draw[curCorner] is not None:
                self.corners_draw[curCorner].remove()
                self.corners_draw[curCorner]=None
            self.corners_draw[curCorner], = self.ax_im.plot(x,y,'ro')
            if curCorner=='tl':
                self.corners_text.set_text('click on top right corner')
                self.mode = self.mode[:-2]+'tr'
            elif curCorner=='tr':
                self.corners_text.set_text('click on bottom right corner')
                self.mode = self.mode[:-2]+'br'
            elif curCorner=='br':
                self.corners_text.set_text('click on bottom left corner')
                self.mode = self.mode[:-2]+'bl'
            elif curCorner=='bl':
                self.corners_text.set_text('BACKSPACE to reset. ENTER to confirm')
                self.mode = 'corners-done'

            if cornersStore['tl'] is not None and cornersStore['tr'] is not None:
                if self.corners_draw['tl-tr'] is not None:
                    self.corners_draw['tl-tr'].remove()
                self.corners_draw['tl-tr'], =self.ax_im.plot([cornersStore['tl'][0],cornersStore['tr'][0]],[cornersStore['tl'][1],cornersStore['tr'][1]],'r-')
            if cornersStore['br'] is not None and cornersStore['tr'] is not None:
                if self.corners_draw['br-tr'] is not None:
                    self.corners_draw['br-tr'].remove()
                self.corners_draw['br-tr'], =self.ax_im.plot([cornersStore['br'][0],cornersStore['tr'][0]],[cornersStore['br'][1],cornersStore['tr'][1]],'r-')
            if cornersStore['tl'] is not None and cornersStore['bl'] is not None:
                if self.corners_draw['tl-bl'] is not None:
                    self.corners_draw['tl-bl'].remove()
                self.corners_draw['tl-bl'], =self.ax_im.plot([cornersStore['tl'][0],cornersStore['bl'][0]],[cornersStore['tl'][1],cornersStore['bl'][1]],'r-')
            if cornersStore['br'] is not None and cornersStore['bl'] is not None:
                if self.corners_draw['br-bl'] is not None:
                    self.corners_draw['br-bl'].remove()
                self.corners_draw['br-bl'], =self.ax_im.plot([cornersStore['br'][0],cornersStore['bl'][0]],[cornersStore['br'][1],cornersStore['bl'][1]],'r-')

            self.ax_im.figure.canvas.draw()
        elif '-tl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = (self.endX,self.endY)+bbs[self.selectedId][2:]
                #self.setSelectedRect(bbs[self.selectedId])
            self.draw()
        elif '-bl' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:6]+(self.endX,self.endY)+bbs[self.selectedId][8:]
                #self.setSelectedRect(bbs[self.selectedId])
            self.draw()
        elif '-tr' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:2]+(self.endX,self.endY)+bbs[self.selectedId][4:]
                #self.setSelectedRect(bbs[self.selectedId])
            self.draw()
        elif '-br' == self.mode[-3:]:#we dragged the top-left corner to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:4]+(self.endX,self.endY)+bbs[self.selectedId][6:]
                #self.setSelectedRect(bbs[self.selectedId])
            self.draw()
        elif '-le' == self.mode[-3:]:#we dragged the left edge to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                shiftX=self.endX-self.startX
                shiftY=self.endY-self.startY
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = (bbs[self.selectedId][0]+shiftX,bbs[self.selectedId][1]+shiftY,) + bbs[self.selectedId][2:6] +  (bbs[self.selectedId][6]+shiftX,bbs[self.selectedId][7]+shiftY,) + bbs[self.selectedId][8:]
            self.draw()
        elif '-re' == self.mode[-3:]:#we dragged the right edge to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                shiftX=self.endX-self.startX
                shiftY=self.endY-self.startY
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:2] + (bbs[self.selectedId][2]+shiftX,bbs[self.selectedId][3]+shiftY,bbs[self.selectedId][4]+shiftX,bbs[self.selectedId][5]+shiftY,) + bbs[self.selectedId][6:]
            self.draw()
        elif '-te' == self.mode[-3:]:#we dragged the right edge to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                shiftX=self.endX-self.startX
                shiftY=self.endY-self.startY
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = (bbs[self.selectedId][0]+shiftX,bbs[self.selectedId][1]+shiftY,bbs[self.selectedId][2]+shiftX,bbs[self.selectedId][3]+shiftY,) + bbs[self.selectedId][4:]
            self.draw()
        elif '-be' == self.mode[-3:]:#we dragged the right edge to resize the selected box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                shiftX=self.endX-self.startX
                shiftY=self.endY-self.startY
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:4] + (bbs[self.selectedId][4]+shiftX,bbs[self.selectedId][5]+shiftY,bbs[self.selectedId][6]+shiftX,bbs[self.selectedId][7]+shiftY,) + bbs[self.selectedId][8:]
            self.draw()
        elif '-mv' == self.mode[-3:]:#we're just moving the box
            self.mode=self.mode[:-3]
            bbs = None
            if self.selected=='field':
                bbs = self.fieldBBs
            elif self.selected=='text':
                bbs = self.textBBs
            if bbs is not None:
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                shiftX = self.endX-self.startX
                shiftY = self.endY-self.startY
                bbs[self.selectedId] = (bbs[self.selectedId][0]+shiftX,bbs[self.selectedId][1]+shiftY,
                                        bbs[self.selectedId][2]+shiftX,bbs[self.selectedId][3]+shiftY,
                                        bbs[self.selectedId][4]+shiftX,bbs[self.selectedId][5]+shiftY,
                                        bbs[self.selectedId][6]+shiftX,bbs[self.selectedId][7]+shiftY)+bbs[self.selectedId][8:]
                #self.setSelectedRect(bbs[self.selectedId])
            self.draw()
        else:
            if '-d' == self.mode[-2:]:
                self.mode=self.mode[:-2]




            if self.mode=='delete':
                if self.secondaryMode is None:
                    #first check for pairing lines (we can only delete them)
                    for index,(text,field) in enumerate(self.pairing):
                        #if within bounds of line and within distance from it
                        x1=(self.textBBs[text][0]+self.textBBs[text][2]+self.textBBs[text][4]+self.textBBs[text][6])/4
                        y1=(self.textBBs[text][1]+self.textBBs[text][3]+self.textBBs[text][5]+self.textBBs[text][7])/4
                        x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2]+self.fieldBBs[field][4]+self.fieldBBs[field][6])/4
                        y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3]+self.fieldBBs[field][5]+self.fieldBBs[field][7])/4

                        if onLine(x,y,x1,y1,x2,y2):
                            #delete the pairing
                            self.didAction(('remove-pairing',text,field))
                            #self.pairLines[index].remove()
                            #self.ax_im.figure.canvas.draw()
                            #del self.pairLines[index]
                            del self.pairing[index]
                            self.draw()
                            return

                    for index,(a,b,field) in enumerate(self.samePairing):
                        #if within bounds of line and within distance from it
                        bbs=None
                        if field:
                            bbs=self.fieldBBs
                        else:
                            bbs=self.textBBs
                        x1=(bbs[a][0]+bbs[a][2]+bbs[a][4]+bbs[a][6])/4
                        y1=(bbs[a][1]+bbs[a][3]+bbs[a][5]+bbs[a][7])/4
                        x2=(bbs[b][0]+bbs[b][2]+bbs[b][4]+bbs[b][6])/4
                        y2=(bbs[b][1]+bbs[b][3]+bbs[b][5]+bbs[b][7])/4

                        if onLine(x,y,x1,y1,x2,y2):
                            #delete the pairing
                            self.didAction(('remove-samePairing',a,b,field))
                            #self.pairLines[index].remove()
                            #self.ax_im.figure.canvas.draw()
                            #del self.pairLines[index]
                            del self.samePairing[index]
                            self.draw()
                            return
                elif self.secondaryMode=='row' or self.secondaryMode=='col':
                    #again, first check for linesitems
                    for id, group in self.groups.items():
                        if group.typeStr==self.secondaryMode:
                            x1,y1 = group.getCentroid(self)
                            if not group.holdsFields:
                                bbs=self.fieldBBs
                            else:
                                bbs=self.textBBs
                            for b in group.pairings:
                                if b in bbs:
                                    x2=(bbs[b][0]+bbs[b][2]+bbs[b][4]+bbs[b][6])/4
                                    y2=(bbs[b][1]+bbs[b][3]+bbs[b][5]+bbs[b][7])/4

                                    if onLine(x,y,x1,y1,x2,y2):
                                        self.didAction(('remove-group-pairing',id,b))
                                        group.unpair(b,True)
                                        self.draw()
                                        return

                            if not group.holdsFields:
                                bbs=self.textBBs
                            else:
                                bbs=self.fieldBBs
                            for b in group.samePairings:
                                if b in bbs:
                                    x2=(bbs[b][0]+bbs[b][2]+bbs[b][4]+bbs[b][6])/4
                                    y2=(bbs[b][1]+bbs[b][3]+bbs[b][5]+bbs[b][7])/4

                                    if onLine(x,y,x1,y1,x2,y2):
                                        self.didAction(('remove-group-samePairing',id,b))
                                        group.unpair(b,False)
                                        self.draw()
                                        return
            #then bbs
            if self.mode == 'move':
                remove=None
                add=None
                for id in self.textBBs:
                    if self.checkInside(x,y,self.textBBs[id]):
                        if id not in self.selectedTextIds:
                            add=id
                        else:
                            remove=id
                        break
                for id in self.fieldBBs:
                    canAdd = add is None and id not in self.selectedFieldIds
                    canRemove = remove is None and id in self.selectedFieldIds
                    if canAdd or canRemove:
                        if self.checkInside(x,y,self.fieldBBs[id]):
                            if canAdd:
                                self.selectedFieldIds.append(id)
                                self.drawSelected()
                                return
                            elif canRemove:
                                self.selectedFieldIds.remove(id)
                                self.drawSelected()
                                return
                        
                if add is not None:
                    self.selectedTextIds.append(add)
                    self.drawSelected()
                    return
                elif remove is not None:
                    self.selectedTextIds.remove(remove)
                    self.drawSelected()
                    return

                self.selectedTextIds=[]
                self.selectedFieldIds=[]
                self.drawSelected()
                return
                            
            elif self.secondaryMode is None:
                indecies = list(range(len(self.textBBs)))
                shuffle(indecies)
                for index in indecies:
                    id = list(self.textBBs.keys())[index]
                    if self.checkInside(x,y,self.textBBs[id]):
                        #print 'click on text b'
                        if self.mode=='delete':
                            for hlid in self.horzLinks:
                                s_id='t'+str(id)
                                if s_id in self.horzLinks[hlid]:
                                    if len(self.horzLinks[hlid])>2:
                                        link_ind = self.horzLinks[hlid].index(s_id)
                                        self.horzLinks[hlid].remove(s_id)
                                        self.didAction(('minus-horzLink',hlid,s_id,link_ind))
                                    else:
                                        toDel = self.horzLinks[hlid]
                                        del self.horzLinks[hlid]
                                        self.didAction(('remove-horzLink',hlid,toDel))
                                    self.draw()
                                    return

                            #delete the text BB
                            pairs=[]#pairs this BB is part of
                            pairIds=[]
                            for i,pair in enumerate(self.pairing):
                                if id==pair[0]:
                                    pairIds.append(i)
                                    pairs.append(pair)
                            for i in sorted(pairIds, reverse=True):
                                del self.pairing[i]
                            samePairs=[]#pairs this BB is part of
                            samePairIds=[]
                            for i,pair in enumerate(self.samePairing):
                                if id==pair[0] or id==pair[1]:
                                    samePairIds.append(i)
                                    samePairs.append(pair)
                            for i in sorted(samePairIds, reverse=True):
                                del self.samePairing[i]
                            self.didAction(('remove-text',id)+self.textBBs[id]+(pairs,samePairs,))
                            del self.textBBs[id]
                            if self.selected=='text' and self.selectedId==id:
                                self.selected='none'
                                self.setSelectedRectOff()
                            self.draw()
                            return

                        else:
                            if self.selected!='text' or self.selectedId!=id:
                                if self.mode!='trans':
                                    #pair to prev selected?
                                    if self.mode=='horzLink':
                                        self.doHorzLink('t'+str(id))
                                    elif self.selected=='field' and (id,self.selectedId) not in self.pairing:
                                        self.pairing.append((id,self.selectedId))
                                        self.didAction(('add-pairing',id,self.selectedId))
                                    elif self.mode=='pair' and self.selected=='text' and (id,self.selectedId) not in self.samePairing and (self.selectedId,id) not in self.samePairing:
                                        self.samePairing.append((id,self.selectedId,0))
                                        self.didAction(('add-samePairing',id,self.selectedId,0))
                                #select the text BB
                                self.selectedId=id
                                self.selected='text'
                                #self.setSelectedRect(self.textBBs[id])
                                self.draw()
                                return

                indecies = list(range(len(self.fieldBBs)))
                shuffle(indecies)
                indecies.sort(key=lambda a: int(self.fieldBBs[list(self.fieldBBs.keys())[a]][8]==codeMap['fieldCol'] or self.fieldBBs[list(self.fieldBBs.keys())[a]][8]==codeMap['fieldRow'] or self.fieldBBs[list(self.fieldBBs.keys())[a]][8]==codeMap['fieldRegion']))
                for index in indecies:
                    id = list(self.fieldBBs.keys())[index]
                    if self.checkInside(x,y,self.fieldBBs[id]):
                        #print 'click on field b'
                        if self.mode=='delete':
                            for hlid in self.horzLinks:
                                s_id='f'+str(id)
                                if s_id in self.horzLinks[hlid]:
                                    if len(self.horzLinks[hlid])>2:
                                        link_ind = self.horzLinks[hlid].index(s_id)
                                        self.horzLinks[hlid].remove(s_id)
                                        self.didAction(('minus-horzLink',hlid,s_id,link_ind))
                                    else:
                                        toDel = self.horzLinks[hlid]
                                        del self.horzLinks[hlid]
                                        self.didAction(('remove-horzLink',hlid,toDel))
                                    self.draw()
                                    return
                            #delete the field BB
                            pairs=[]#pairs this BB is part of
                            pairIds=[]
                            for i,pair in enumerate(self.pairing):
                                if id==pair[1]:
                                    pairIds.append(i)
                                    pairs.append(pair)
                            for i in sorted(pairIds, reverse=True):
                                del self.pairing[i]
                            samePairs=[]#pairs this BB is part of
                            samePairIds=[]
                            for i,pair in enumerate(self.samePairing):
                                if id==pair[0] or id==pair[1]:
                                    samePairIds.append(i)
                                    samePairs.append(pair)
                            for i in sorted(samePairIds, reverse=True):
                                del self.samePairing[i]
                            self.didAction(('remove-field',id)+self.fieldBBs[id]+(pairs,samePairs,))
                            del self.fieldBBs[id]
                            if self.selected=='field' and self.selectedId==id:
                                self.selected='none'
                                self.setSelectedRectOff()
                            self.draw()
                            return

                        else:
                            if self.selected!='field' or self.selectedId!=id:
                                #pair to prev selected?
                                if self.mode=='horzLink':
                                    self.doHorzLink('f'+str(id))
                                elif self.selected=='text' and (self.selectedId,id) not in self.pairing:
                                    self.pairing.append((self.selectedId,id))
                                    self.didAction(('add-pairing',self.selectedId,id))
                                elif self.mode=='pair' and self.selected=='field' and (id,self.selectedId) not in self.samePairing and (self.selectedId,id) not in self.samePairing:
                                    self.samePairing.append((id,self.selectedId,1))
                                    self.didAction(('add-samePairing',id,self.selectedId,1))
                                #select the field BB
                                self.selectedId=id
                                self.selected='field'
                                #self.setSelectedRect(self.fieldBBs[id])
                                self.draw()
                                return

            elif self.secondaryMode=='row' or self.secondaryMode=='col':
                if self.mode!='delete':
                    for id in self.textBBs:
                        if self.checkInside(x,y,self.textBBs[id]):
                            if self.selected=='none':
                                skip=False
                                for gId,group in self.groups.items():
                                    if not group.holdsFields and group.contains(id):
                                        skip=True
                                        break
                                if not skip:
                                    self.groups[self.groupCurId] = Group(typeStr=self.secondaryMode, holdsFields=False)
                                    self.groups[self.groupCurId].add(id)
                                    self.didAction(('add-group',self.groupCurId,self.groups[self.groupCurId]))
                                    self.selected=self.secondaryMode
                                    self.selectedId=self.groupCurId
                                    self.groupCurId+=1
                                    self.draw()
                                    return
                            elif self.groups[self.selectedId].holdsFields:
                                self.didAction(('add-group-pairing',self.selectedId,id))
                                self.groups[self.selectedId].pair(id,True)
                                self.draw()
                                return
                            elif self.groups[self.selectedId].contains(id):
                                self.didAction(('removed-from-group',self.selectedId,id))
                                self.groups[self.selectedId].remove(id)
                                self.setSelectedPoly(self.groups[self.selectedId].getPoly(self))
                                self.draw()
                                return
                            elif self.mode=='pair':
                                if not self.groups[self.selectedId].contains(id):
                                    self.didAction(('add-group-samePairing',self.selectedId,id))
                                    self.groups[self.selectedId].pair(id,False)
                                    self.draw()
                                    return
                            else:
                                self.didAction(('added-to-group',self.selectedId,id))
                                self.groups[self.selectedId].add(id)
                                self.setSelectedPoly(self.groups[self.selectedId].getPoly(self))
                                self.draw()
                                return
                    for id in self.fieldBBs:
                        if self.checkInside(x,y,self.fieldBBs[id]):
                            if self.selected=='none':
                                skip=False
                                for gId,group in self.groups.items():
                                    if group.holdsFields and group.contains(id): # and group.typeStr==self.secondaryMode:
                                        skip=True
                                        break
                                if not skip:
                                    self.groups[self.groupCurId] = Group(typeStr=self.secondaryMode, holdsFields=True)
                                    self.groups[self.groupCurId].add(id)
                                    self.didAction(('add-group',self.groupCurId,self.groups[self.groupCurId]))
                                    self.selected=self.secondaryMode
                                    self.selectedId=self.groupCurId
                                    self.groupCurId+=1
                                    self.draw()
                                    return
                            elif not self.groups[self.selectedId].holdsFields:
                                self.didAction(('add-group-pairing',self.selectedId,id))
                                self.groups[self.selectedId].pair(id,True)
                                self.draw()
                                return
                            elif self.groups[self.selectedId].contains(id):
                                self.didAction(('removed-from-group',self.selectedId,id))
                                self.groups[self.selectedId].remove(id)
                                self.setSelectedPoly(self.groups[self.selectedId].getPoly(self))
                                self.draw()
                                return
                            elif self.mode=='pair':
                                if not self.groups[self.selectedId].contains(id):
                                    self.didAction(('add-group-samePairing',self.selectedId,id))
                                    self.groups[self.selectedId].pair(id,False)
                                    self.draw()
                                    return
                            else:
                                self.didAction(('added-to-group',self.selectedId,id))
                                self.groups[self.selectedId].add(id)
                                self.setSelectedPoly(self.groups[self.selectedId].getPoly(self))
                                self.draw()
                                return
                for id, group in self.groups.items():
                    if group.typeStr==self.secondaryMode and checkInsidePoly(x,y,group.getPoly(self)):
                        if self.mode=='delete':
                            self.didAction(('remove-group',id,group))
                            del self.groups[id]
                            if self.selectedId==id:
                                self.setSelectedRectOff()
                                self.selected='none'
                                self.selectedId=None
                        else:
                            self.selectedId=id
                            self.selected=group.typeStr
                            self.setSelectedPoly(group.getPoly(self))
                            
                        self.draw()
                        return

            if self.selected!='none':
                #print 'deselected'
                self.selected='none'

                self.setSelectedRectOff()
                self.typed()
                self.ax_im.figure.canvas.draw()

    def clickerMove(self,event):           
        #moving only matters if the button is down and we've moved "enough"
        bbs = None
        if self.mode=='trans':
            return
        if self.selected == 'field':
            bbs = self.fieldBBs
        elif self.selected == 'text':
            bbs = self.textBBs
        if '-d' == self.mode[-2:] and math.sqrt(pow(event.xdata-self.startX,2)+pow(event.ydata-self.startY,2))>MIN_MOVE_DIST:
            if bbs is not None and self.checkInside(self.startX,self.startY,bbs[self.selectedId]):
                self.draw(clear=True)
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
                col=colorMap[RcodeMap[bbs[self.selectedId][8]]] #colorMap[self.mode[:-2]]

                self.mode = self.mode[:-1]+'mv'
                
                closestDist = (self.startX-xc)**2 + (self.startY-yc)**2
                if self.resizeMode=='corners':
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
                elif self.resizeMode=='edges':
                    dist = ((self.startX-bbs[self.selectedId][0]+self.startX-bbs[self.selectedId][6])/2)**2 + ((self.startY-bbs[self.selectedId][1]+self.startY-bbs[self.selectedId][7])/2)**2 #left edge
                    if dist<closestDist:
                        self.mode = self.mode[:-2]+'le'
                        closestDist = dist
                    dist = (-(self.startX-bbs[self.selectedId][2]+self.startX-bbs[self.selectedId][4])/2)**2 + ((self.startY-bbs[self.selectedId][3]+self.startY-bbs[self.selectedId][5])/2)**2 #right edge
                    if dist<closestDist:
                        self.mode = self.mode[:-2]+'re'
                        closestDist = dist
                    dist = ((self.startY-bbs[self.selectedId][1]+self.startY-bbs[self.selectedId][3])/2)**2 + ((self.startX-bbs[self.selectedId][0]+self.startX-bbs[self.selectedId][2])/2)**2 #top edge
                    if dist<closestDist:
                        self.mode = self.mode[:-2]+'te'
                        closestDist = dist
                    dist = (-(self.startY-bbs[self.selectedId][5]+self.startY-bbs[self.selectedId][7])/2)**2 + ((self.startX-bbs[self.selectedId][4]+self.startX-bbs[self.selectedId][6])/2)**2 #bot edge
                    if dist<closestDist:
                        self.mode = self.mode[:-2]+'be'
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
            elif 'none' not in self.mode and 'delete' not in self.mode and 'change' not in self.mode and 'pair' not in self.mode and 'horzLink' not in self.mode:
                if 'move' not in self.mode:
                    self.draw(clear=True)
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
        elif (self.mode[:6]!='corner' and
             (('-tl' == self.mode[-3:])or # and  event.xdata<bbs[self.selectedId][2] and event.ydata<bbs[self.selectedId][3]) or
              ('-bl' == self.mode[-3:])or # and  event.xdata<bbs[self.selectedId][2] and event.ydata>bbs[self.selectedId][1]) or
              ('-tr' == self.mode[-3:])or # and  event.xdata>bbs[self.selectedId][0] and event.ydata<bbs[self.selectedId][3]) or
              ('-br' == self.mode[-3:])or # and  event.xdata>bbs[self.selectedId][0] and event.ydata>bbs[self.selectedId][1]) or
              ('-le' == self.mode[-3:])or
              ('-re' == self.mode[-3:])or
              ('-te' == self.mode[-3:] )or # and  event.ydata<bbs[self.selectedId][3]) or
              ('-be' == self.mode[-3:] )or # and  event.ydata>bbs[self.selectedId][1]))):
              ('-mv' == self.mode[-3:] ))):
            self.endX=event.xdata
            self.endY=event.ydata
            if self.endX is None or self.endY is None:
                return
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
            elif '-le' == self.mode[-3:]:
                tlX += self.endX-self.startX
                blX += self.endX-self.startX
                tlY += self.endY-self.startY
                blY += self.endY-self.startY
            elif '-re' == self.mode[-3:]:
                trX += self.endX-self.startX
                brX += self.endX-self.startX
                trY += self.endY-self.startY
                brY += self.endY-self.startY
            elif '-te' == self.mode[-3:]:
                tlX += self.endX-self.startX
                trX += self.endX-self.startX
                tlY += self.endY-self.startY
                trY += self.endY-self.startY
            elif '-be' == self.mode[-3:]:
                blX += self.endX-self.startX
                brX += self.endX-self.startX
                blY += self.endY-self.startY
                brY += self.endY-self.startY
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

    def doKey(self,event):
        key = event.key
        if self.mode=='trans':
            if key=='f1':
                self.setMode(self.tmpMode)
                self.moveTrans()
            elif key=='up' or key=='down' or key=='left' or key=='right':
                self.moveTrans(key)
            elif key=='backspace':
                self.typed(None,True)
            elif key is not None and len(key)==1:
                self.typed(key)
            elif key=='escape': #quit, unfinished
                plt.close('all')
            elif key=='enter': #quit, finished
                self.complete=True
                plt.close('all')
            elif key=='f12': #quit, no save
                self.textBBs={}
                self.fieldBBs={}
                self.pairing=[]
                self.samePairing=[]
                self.corners={}
                self.cornersActual={}
                self.transcriptions={}
                plt.close('all')

        elif self.mode=='change':
            for mode in keyMap:
                if key==keyMap[mode] and self.selected[:4]==mode[:4] or (mode=='comment' and self.selected=='field'):
                    if self.selected=='text':
                        self.didAction(('change-text',self.selectedId,self.textBBs[self.selectedId][8]))
                        self.textBBs[self.selectedId]=self.textBBs[self.selectedId][0:8]+(codeMap[mode],)+self.textBBs[self.selectedId][9:]
                    elif self.selected=='field':
                        self.didAction(('change-field',self.selectedId,self.fieldBBs[self.selectedId][8]))
                        self.fieldBBs[self.selectedId]=self.fieldBBs[self.selectedId][0:8]+(codeMap[mode],)+self.fieldBBs[self.selectedId][9:]
                    self.draw()

            if self.tmpMode in modes:
                self.mode=self.tmpMode
            else:
                self.mode='text'
            self.modeRect.set_y(toolYMap[self.mode])
            self.ax_tool.figure.canvas.draw()
        elif self.mode[:6] == 'corner':
            if event.key=='escape' or event.key=='f12': #quit
                self.textBBs={}
                self.fieldBBs={}
                self.pairing=[]
                self.samePairing=[]
                self.corners={}
                self.cornersActual={}
                plt.close('all')
            elif event.key=='backspace':
                if 'Actual' in self.mode:
                    self.mode='cornerActual-tl'
                    for key in self.cornersActual:
                        self.cornersActual[key]=None
                else:
                    self.mode='corner-tl'
                    for key in self.corners:
                        self.corners[key]=None
                for key in self.corners_draw:
                    if self.corners_draw[key] is not None:
                        self.corners_draw[key].remove()
                        self.corners_draw[key]=None
                self.corners_text.set_text('click on the top left corner')
                self.ax_im.figure.canvas.draw()
            elif event.key=='enter':
                if 'Actual' in self.mode and self.cornersActual['tl'] is not None and self.cornersActual['tr'] is not None and self.cornersActual['br'] is not None and self.cornersActual['bl'] is not None:
                    self.init()
                elif self.corners['tl'] is not None and self.corners['tr'] is not None and self.corners['br'] is not None and self.corners['bl'] is not None:
                    self.cornersActual=dict(self.corners)
                    self.mode='cornersActual'
                    self.corners_text.set_text('Mark the ACTUAL page corner (physical paper), then press ENTER.\n(outer corners if two pages).\nIf odd position, press BACKSPACE for corner by corner query.')
                    self.corners_text.set_color('darkmagenta')
                    self.ax_im.figure.canvas.draw()
        else:
            key = event.key
            if key in RkeyMap:
                newMode = RkeyMap[key]
                if self.mode != newMode:
                    self.mode = newMode
                    self.modeRect.set_y(toolYMap[self.mode])
                    self.ax_tool.figure.canvas.draw()
                    #print newMode
            elif key=='escape': #quit, unfinished
                plt.close('all')
            elif key=='enter': #quit, finished
                self.complete=True
                plt.close('all')
            elif key=='f12': #quit, no save
                self.textBBs={}
                self.fieldBBs={}
                self.pairing=[]
                self.samePairing=[]
                self.corners={}
                self.cornersActual={}
                self.transcriptions={}
                plt.close('all')
            elif key=='g': #delete:
                if self.mode != 'delete':
                    self.modeRect.set_y(toolYMap['delete'])
                    self.ax_tool.figure.canvas.draw()
                    self.mode='delete'
            elif key=='a': # undo
                self.undo()
            elif key=='s': #S redo
                self.redo()
            elif key=='d': #D change
                self.setMode('change')
            elif key=='z': # set field to print/stamp
                self.setFieldType(ftypeMap['print'])
            elif key=='x': # set field to blank
                self.setFieldType(ftypeMap['blank'])
            elif key=='c': # set field to handwriting (default)
                self.setFieldType(ftypeMap['handwriting'])
            elif key=='v': # set field to signature
                self.setFieldType(ftypeMap['signature'])
            elif key=='f': #V pair
                self.setMode('pair')
            elif key=='h':
                self.setMode('horzLink')
                self.draw()
            elif key=='j':
                self.rotateOrien()
            elif key=='k': #K copy selected
                self.copy()
            elif key=='m': #M select muliple BBs to apply transformations to
                self.moveSelect()
            elif key=="'": #row
                self.setSecondaryMode('row')
            elif key==';': #col
                self.setSecondaryMode('col')
            elif key=='up' or key=='shift+up':
                trans = np.array([[1.0,0,0],
                                  [0,1,-self.shiftAmount],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='down' or key=='shift+down':
                trans = np.array([[1,0,0],
                                  [0,1,self.shiftAmount],
                                  [0,0,1.0]])
                self.transAll(trans)
            elif key=='left' or key=='shift+left':
                trans = np.array([[1,0,-self.shiftAmount],
                                  [0,1,0],
                                  [0,0,1.0]])
                self.transAll(trans)
            elif key=='right' or key=='shift+right':
                trans = np.array([[1,0,self.shiftAmount],
                                  [0,1,0],
                                  [0,0,1.0]])
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
                t=0.99
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[t,0,x-t*x],
                                  [0,t,y-t*y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='=':#scale
                t=1.01
                x=self.imageW/2.0
                y=self.imageH/2.0
                trans = np.array([[t,0,x-t*x],
                                  [0,t,y-t*y],
                                  [0,0,1]])
                self.transAll(trans)
            elif key=='backspace':
                self.draw()
            elif key=='f4' and self.mode=='move':
                textBBs=[]
                for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in self.textBBs.items():
                    if id in self.selectedTextIds:
                        textBBs.append({
                                        'id': 't'+str(id+1000),
                                        'poly_points':[[int(round(tlX)),int(round(tlY))],[int(round(trX)),int(round(trY))],[int(round(brX)),int(round(brY))],[int(round(blX)),int(round(blY))]],
                                        'type':RcodeMap[para]
                                       })
                fieldBBs=[]
                for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in self.fieldBBs.items():
                    if id in self.selectedFieldIds:
                        fieldBBs.append({
                                        'id': 'f'+str(id+1000),
                                        'poly_points':[[int(round(tlX)),int(round(tlY))],[int(round(trX)),int(round(trY))],[int(round(brX)),int(round(brY))],[int(round(blX)),int(round(blY))]],
                                        'type':RcodeMap[para],
                                        'isBlank':blank,
                                       })
                with open('copied.json','w') as out:
                    out.write(json.dumps({'textBBs':textBBs, 'fieldBBs':fieldBBs}))
            elif key=='shift':
                self.resizeMode='corners'
                self.shiftAmount=40
            elif key=='f8' and self.selected!='none':
                #split selected at click point
                if self.selected == 'field':
                    bbs=self.fieldBBs
                elif self.selected == 'text':
                    bbs=self.textBBs
                nTop, nBot = self.getDividingLine(self.startX,self.startY,*bbs[self.selectedId][0:8])
                bb = bbs[self.selectedId]
                self.didAction(('drag-'+self.selected,self.selectedId)+bbs[self.selectedId][0:8])
                bbs[self.selectedId] = bbs[self.selectedId][0:2]+(nTop[0],nTop[1],nBot[0],nBot[1])+bbs[self.selectedId][6:]
                new_bb = (nTop[0], nTop[1], bb[2], bb[3], bb[4], bb[5], nBot[0], nBot[1],) + bb[8:]
                if 'text'==self.selected:
                    self.textBBs[self.textBBCurId]=new_bb
                    self.didAction(('add-text',self.textBBCurId,)+new_bb+(None,None,))
                    if self.secondaryMode is None:
                        self.selectedId=self.textBBCurId
                        self.selected='text'
                    self.textBBCurId+=1
                elif 'field'==self.selected:
                    self.fieldBBs[self.fieldBBCurId]=new_bb
                    self.didAction(('add-field',self.fieldBBCurId,)+new_bb+(None,None,))
                    if self.secondaryMode is None:
                        self.selectedId=self.fieldBBCurId
                        self.selected='field'
                    self.fieldBBCurId+=1
                self.draw()
            elif key=='f9':
                self.pairing=self.transformAllToRect()
                self.samePairing=[]
                self.draw()
            elif key=='f1':
                self.setMode('trans')
                self.moveTrans()


    
    def doKeyUp(self,event):
        if event.key=='shift':
            self.resizeMode='edges'
            self.shiftAmount=4

    def typed(self,key='',backspace=False):
        if self.selected != 'none' and self.mode=='trans':
            id = self.selected[0]+str(self.selectedId)
            if backspace:
                self.transcriptions[id]=self.transcriptions[id][:-1]
            else:
                self.transcriptions[id]+=key
            #update visuals
            if 'field' in self.selected:
                bb=self.fieldBBs[self.selectedId]
            else:
                bb=self.textBBs[self.selectedId]
            if self.transLoc=='down':
                x = bb[6]
                y = bb[7]+10
            elif self.transLoc=='right':
                x = bb[4]
                y = bb[5]-3
            #elif self.transLoc=='left':
            #    x = bb[2]
            #    y = bb[3]-3
            else:
                x = bb[0]
                y = bb[1]

            if id in self.transText:
                self.transText[id].remove()
            if self.selectedText is not None:
                self.selectedText.remove()
            self.selectedText=self.ax_im.text(x+1,y+1,self.transcriptions[id]+'|',color=(.95,.95,.95))
            self.transText[id]=self.ax_im.text(x,y,self.transcriptions[id],color=(.15,.2,.03))
            self.ax_im.figure.canvas.draw()
        elif self.selectedText is not None:
            self.selectedText.remove()
            self.selectedText=None
    def moveTrans(self,pos=None):
        if pos is not None:
            self.transLoc=pos
        if self.mode=='trans':
            color = (.15,.2,.03)
        else:
            color = (.15,.2,.03,0.3)
        for id in self.transcriptions:
            if 'f' == id[0]:
                bb=self.fieldBBs[int(id[1:])]
            else:
                bb=self.textBBs[int(id[1:])]
            if self.transLoc=='down':
                x = bb[6]
                y = bb[7]+10
            elif self.transLoc=='right':
                x = bb[4]
                y = bb[5]-3
            #elif self.transLoc=='left':
            #    x = bb[2]
            #    y = bb[3]-3
            else:
                x = bb[0]
                y = bb[1]
            if id in self.transText:
                self.transText[id].set_x(x)
                self.transText[id].set_y(y)
                self.transText[id].set_color(color)
            else:
                self.transText[id]=self.ax_im.text(x,y,'['+id+']'+self.transcriptions[id],color=color)
                #self.transText[id]=self.ax_im.text(x,y,self.transcriptions[id],color=color)
        self.typed()
        self.ax_im.figure.canvas.draw()

    
    def transformAllToRect(self):
        fields=[]
        fieldIds=[]
        for id in self.fieldBBs:
            self.fieldBBs[id], ang = self.transformToRect(self.fieldBBs[id])
            fields.append(ang)
            fieldIds.append(id)
        predictions = np.array([fields])
        texts=[]
        textIds=[]
        for id in self.textBBs:
            self.textBBs[id], ang = self.transformToRect(self.textBBs[id])
            texts.append(ang)
            textIds.append(id)
        targets = np.array([texts])

        #print 'ang pred'
        pred_points = self.convPoints(predictions)
        pred_heights = predictions[:,:,4]
        pred_widths = predictions[:,:,5]
        #print 'ang targ'
        target_points = self.convPoints(targets)
        target_heights = targets[:,:,3]
        target_widths = targets[:,:,4]
        #print 'pred field'
        #print pred_points
        #print 'target text'
        #print target_points
        expanded_pred_points = pred_points[:,:,None]
        expanded_pred_heights = pred_heights[:,:,None]
        expanded_pred_widths = pred_widths[:,:,None]

        expanded_target_points = target_points[:,None,:]
        expanded_target_heights = target_heights[:,None,:]
        expanded_target_widths = target_widths[:,None,:]

        #expanded_pred_points = expanded_pred_points.expand(pred_points.shape[0], pred_points.shape[1], target_points.shape[1], pred_points.shape[2])
        expanded_pred_points = np.tile(expanded_pred_points,(1,1,target_points.shape[1],1))
        expanded_pred_heights = np.tile(expanded_pred_heights,(1,1,target_heights.shape[1]))
        expanded_pred_widths = np.tile(expanded_pred_widths,(1,1,target_widths.shape[1]))
        #expanded_target_points = expanded_target_points.expand(target_points.shape[0], pred_points.shape[1], target_points.shape[1], target_points.shape[2])
        expanded_target_points = np.tile(expanded_target_points,(1,pred_points.shape[1],1,1))
        expanded_target_heights = np.tile(expanded_target_heights,(1,pred_heights.shape[1],1))
        expanded_target_widths = np.tile(expanded_target_widths,(1,pred_widths.shape[1],1))

        point_deltas = (expanded_pred_points - expanded_target_points)
        #avg_heights = ((expanded_target_heights+expanded_pred_heights)/2)
        #avg_widths = ((expanded_target_widths+expanded_pred_widths)/2)
        avg_heights=avg_widths = (expanded_target_heights+expanded_pred_heights+expanded_target_widths+expanded_pred_widths)/4
        #print point_deltas

        normed_difference = (
            np.linalg.norm(point_deltas[:,:,:,0:2],2,3)/avg_widths +
            np.linalg.norm(point_deltas[:,:,:,2:4],2,3)/avg_widths +
            np.linalg.norm(point_deltas[:,:,:,4:6],2,3)/avg_heights +
            np.linalg.norm(point_deltas[:,:,:,6:8],2,3)/avg_heights
            )**2
        #print normed_difference

        best = normed_difference.argmin(1)
        minV = normed_difference.min(1)

        pairs=[]
        for i in range(best.shape[1]):
            pairs.append((textIds[i],fieldIds[best[0,i]]))
        bb1=self.textBBs[textIds[0]]
        bb2=self.fieldBBs[fieldIds[best[0,0]]]
        #get IOU
        minX = min(bb1[0],bb1[2],bb1[4],bb1[6],
                bb2[0],bb2[2],bb2[4],bb2[6])
        maxX = max(bb1[0],bb1[2],bb1[4],bb1[6],
                bb2[0],bb2[2],bb2[4],bb2[6])
        minY = min(bb1[1],bb1[3],bb1[5],bb1[7],
                bb2[1],bb2[3],bb2[5],bb2[7])
        maxY = max(bb1[1],bb1[3],bb1[5],bb1[7],
                bb2[1],bb2[3],bb2[5],bb2[7])
        import cv2
        draw1 = np.zeros((maxY-minY,maxX-minX))#,dtype=np.int)
        cv2.fillConvexPoly(draw1,np.array([[bb1[0]-minX,bb1[1]-minY],[bb1[2]-minX, bb1[3]-minY],[bb1[4]-minX,bb1[5]-minY],[bb1[6]-minX,bb1[7]-minY]],dtype=np.int),1)
        draw2 = np.zeros((maxY-minY,maxX-minX))#,dtype=np.int)
        cv2.fillConvexPoly(draw2,np.array([[bb2[0]-minX,bb2[1]-minY],[bb2[2]-minX, bb2[3]-minY],[bb2[4]-minX,bb2[5]-minY],[bb2[6]-minX,bb2[7]-minY]],dtype=np.int),1)
        intersection = (draw1*draw2).sum()
        union = (draw1+draw2).sum()-intersection
        print('IOU:'+str(float(intersection)/union))
        print('sum dist:'+str(minV[0,0]))
        return pairs

    def transformToRect(self,bb):
        
        tlX = bb[0]
        tlY = bb[1]
        trX = bb[2]
        trY = bb[3]
        brX = bb[4]
        brY = bb[5]
        blX = bb[6]
        blY = bb[7]

        lX = (tlX+blX)/2.0
        lY = (tlY+blY)/2.0
        rX = (trX+brX)/2.0
        rY = (trY+brY)/2.0
        d=math.sqrt((lX-rX)**2 + (lY-rY)**2)

        hl = ((tlX-lX)*-(rY-lY) + (tlY-lY)*(rX-lX))/d #projection of half-left edge onto transpose horz run
        hr = ((brX-rX)*-(lY-rY) + (brY-rY)*(lX-rX))/d #projection of half-right edge onto transpose horz run
        h = (hl+hr)/2.0

        tX = lX + h*-(rY-lY)/d
        tY = lY + h*(rX-lX)/d
        bX = lX - h*-(rY-lY)/d
        bY = lY - h*(rX-lX)/d

        etX =tX + rX-lX
        etY =tY + rY-lY
        ebX =bX + rX-lX
        ebY =bY + rY-lY

        cX = (lX+rX)/2.0
        cY = (lY+rY)/2.0
        rot = math.atan2((rY-lY),rX-lX) #flip y so angle is true to image
        height = abs(h)    #this is half height ##abs
        width = d/2.0 #and half width

        return (tX,tY,etX,etY,ebX,ebY,bX,bY)+bb[8:], [-1,cX,cY,rot,height,width]
    def convPoints(self,ang):
        #print ang
        cos_rot = np.cos(ang[:,:,3])
        sin_rot = np.sin(ang[:,:,3])
        p_left_x = ang[:,:,1]-cos_rot*ang[:,:,5] ##*
        p_left_y = ang[:,:,2]-sin_rot*ang[:,:,5]
        p_right_x = ang[:,:,1]+cos_rot*ang[:,:,5]
        p_right_y = ang[:,:,2]+sin_rot*ang[:,:,5]
        p_top_x = ang[:,:,1]+sin_rot*ang[:,:,4]
        p_top_y = ang[:,:,2]-cos_rot*ang[:,:,4]
        p_bot_x = ang[:,:,1]-sin_rot*ang[:,:,4]
        p_bot_y = ang[:,:,2]+cos_rot*ang[:,:,4]
        return np.stack([p_left_x,p_left_y,p_right_x,p_right_y,p_top_x,p_top_y,p_bot_x,p_bot_y],axis=2)
        
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
    def rotateOrien(self):
        bbs=None
        if 'text'==self.selected:
            bbs=self.textBBs
        elif 'field'==self.selected:
            bbs=self.fieldBBs

        if bbs is not None:
            bb = bbs[self.selectedId]
            if RcodeMap[bb[8]]!='graphic' and RcodeMap[bb[8]]!='fieldRow' and RcodeMap[bb[8]]!='fieldCol' and RcodeMap[bb[8]]!='fieldCheckBox' and RcodeMap[bb[8]]!='fieldRegion':
                self.didAction(('rotate-orien',bbs,self.selectedId,bb))
                #bbs[self.selectedId] = (bb[2], bb[3],  bb[4], bb[5], bb[6], bb[7], bb[0], bb[1]) + bb[8:]
                bbs[self.selectedId] = (bb[6], bb[7], bb[0], bb[1], bb[2], bb[3],  bb[4], bb[5]) + bb[8:]
                self.draw()

    def copy(self):
        if 'text'==self.selected:
            bb = self.textBBs[self.selectedId]
            ydif = bb[5]-bb[1]
            bb = (bb[0], bb[1]+ydif, bb[2], bb[3]+ydif, bb[4], bb[5]+ydif, bb[6], bb[7]+ydif,) + bb[8:]
            self.textBBs[self.textBBCurId]=bb
            self.didAction(('add-text',self.textBBCurId,)+bb+(None,None,))
            if self.secondaryMode is None:
                self.selectedId=self.textBBCurId
                self.selected='text'
            self.textBBCurId+=1
            self.draw()
        elif 'field'==self.selected:
            bb = self.fieldBBs[self.selectedId]
            ydif = bb[5]-bb[1]
            bb = (bb[0], bb[1]+ydif, bb[2], bb[3]+ydif, bb[4], bb[5]+ydif, bb[6], bb[7]+ydif,) + bb[8:]
            self.fieldBBs[self.fieldBBCurId]=bb
            self.didAction(('add-field',self.fieldBBCurId,)+bb+(None,None,))
            if self.secondaryMode is None:
                self.selectedId=self.fieldBBCurId
                self.selected='field'
            self.fieldBBCurId+=1
            self.draw()

    def doHorzLink(self,id):
        oid=None
        if self.selected=='field':
            oid='f'+str(self.selectedId)
            rot = self.getRotation(self.fieldBBs[self.selectedId])
        elif self.selected=='text':
            oid='t'+str(self.selectedId)
            rot = self.getRotation(self.textBBs[self.selectedId])
        if oid is not None:
            id_hlid=None
            oid_hlid=None
            for hlid, hl in self.horzLinks.items():
                if id_hlid is None and id in hl:
                    id_hlid=hlid
                    if oid_hlid is not None:
                        break
                if oid_hlid is None and oid in hl:
                    oid_hlid=hlid
                    if id_hlid is not None:
                        break
            if id_hlid is None and oid_hlid is None:
                x = self.getOrd(id,rot)
                ox = self.getOrd(oid,rot)
                if x<ox:
                    self.horzLinks[self.cur_hlid]=[id,oid]
                else:
                    self.horzLinks[self.cur_hlid]=[oid,id]
                self.didAction(('create-horzLink',self.cur_hlid))
                self.cur_hlid+=1
            elif id_hlid is None:
                self.addLink(id,oid_hlid,rot)
            elif oid_hlid is None:
                self.addLink(oid,id_hlid,rot)
            elif id_hlid==oid_hlid:
                return
            else:
                #merge
                newLink=[]
                indexI=0
                indexO=0
                linkI=self.horzLinks[id_hlid]
                linkO=self.horzLinks[oid_hlid]
                while indexI<len(linkI) and indexO<len(linkO):
                    if self.getOrd(linkI[indexI],rot) < self.getOrd(linkO[indexO],rot):
                        newLink.append(linkI[indexI])
                        indexI+=1
                    else:
                        newLink.append(linkO[indexO])
                        indexO+=1
                if indexI<len(linkI):
                    newLink+=linkI[indexI:]
                elif indexO<len(linkO):
                    newLink+=linkO[indexO:]
                del self.horzLinks[oid_hlid]
                self.horzLinks[id_hlid]=newLink
                self.didAction(('merge-horzLink',id_hlid,linkI,oid_hlid,linkO))
            self.draw()

    def addLink(self,id,hlid,rot):
        hit=False
        x = self.getOrd(id,rot)
        for index in range(len(self.horzLinks[hlid])):
            ox = self.getOrd(self.horzLinks[hlid][index],rot)
            if x<ox:
                hit=True
                break
        if hit:
            self.horzLinks[hlid].insert(index,id)
        else:
            self.horzLinks[hlid].append(id)
        #self.horzMap[id]=hlid
        self.didAction(('add-horzLink',hlid,id))

    def getOrd(self,lid,rot):
        id=int(lid[1:])
        if lid[0]=='t':
            bbs=self.textBBs
        elif lid[0]=='f':
            bbs=self.fieldBBs
        if rot=='left-right':
            return (bbs[id][0]+bbs[id][2]+bbs[id][4]+bbs[id][6])/4.0
        elif rot=='right-left':
            return -(bbs[id][0]+bbs[id][3]+bbs[id][4]+bbs[id][6])/4.0
        elif rot=='down':
            return (bbs[id][1]+bbs[id][3]+bbs[id][5]+bbs[id][7])/4.0
        elif rot=='up':
            return -(bbs[id][1]+bbs[id][3]+bbs[id][5]+bbs[id][7])/4.0
        else:
            return (bbs[id][0]+bbs[id][2]+bbs[id][4]+bbs[id][6]+bbs[id][1]+bbs[id][3]+bbs[id][5]+bbs[id][7])/8.0
    
    def didAction(self,tup):
        self.actionStack.append(tup)
        self.undoStack=[]

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
        elif action[0] == 'add-samePairing':
            self.samePairing.remove(action[1:])
            return ('remove-samePairing',)+action[1:]
        elif action[0] == 'remove-samePairing':
            self.samePairing.append(action[1:])
            return ('add-samePairing',)+action[1:]
        elif action[0] == 'add-text':
            id = action[1]
            pairs = action[-2]
            samePairs = action[-1]
            del self.textBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if samePairs is not None:
                for samePair in samePairs:
                    self.samePairing.remove(samePair)
            if self.selected=='text' and self.selectedId==id:
                self.selected='none'
            return ('remove-text',)+action[1:]
        elif action[0] == 'remove-text':
            id = action[1]
            pairs = action[-2]
            samePairs = action[-1]
            self.textBBs[id]=action[2:-2]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            if samePairs is not None:
                for samePair in samePairs:
                    self.samePairing.append(samePair)
            return ('add-text',)+action[1:]
        elif action[0] == 'add-field':
            id = action[1]
            pairs = action[-2]
            samePairs = action[-1]
            del self.fieldBBs[id]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.remove(pair)
            if samePairs is not None:
                for samePair in samePairs:
                    self.samePairing.remove(samePair)
            if self.selected=='field' and self.selectedId==id:
                self.selected='none'
            return ('remove-field',)+action[1:]
        elif action[0] == 'remove-field':
            id = action[1]
            pairs = action[-2]
            samePairs = action[-1]
            self.fieldBBs[id]=action[2:-2]
            if pairs is not None:
                for pair in pairs:
                    self.pairing.append(pair)
            if samePairs is not None:
                for samePair in samePairs:
                    self.samePairing.append(samePair)
            return ('add-field',)+action[1:]
        elif action[0] == 'add-group':
            id = action[1]
            group = action[2]
            del self.groups[id]
            if self.selected==group.typeStr and self.selectedId==id:
                self.selected='none'
                self.setSelectedRectOff()
            return ('remove-group',id,group)
        elif action[0] == 'remove-group':
            id = action[1]
            group = action[2]
            self.groups[id]=group
            return ('add-group',id,group)
        elif action[0] == 'added-to-group':
            groupId = action[1]
            eleId = action[2]
            self.groups[groupId].remove(eleId)
            return ('removed-from-group',groupId,eleId)
        elif action[0] == 'removed-from-group':
            groupId = action[1]
            eleId = action[2]
            self.groups[groupId].add(eleId)
            return ('added-to-group',groupId,eleId)
        elif action[0] == 'add-group-pairing':
            groupId = action[1]
            eleId = action[2]
            self.groups[groupId].unpair(eleId,True)
            return ('remove-group-pairing',groupId,eleId)
        elif action[0] == 'remove-group-pairing':
            groupId = action[1]
            eleId = action[2]
            self.groups[groupId].pair(eleId,True)
            return ('add-group-pairing',groupId,eleId)
        elif action[0] == 'add-group-samePairing':
            groupId = action[1]
            eleId = action[2]
            self.groups[groupId].unpair(eleId,False)
            return ('remove-group-samePairing',groupId,eleId)
        elif action[0] == 'remove-group-samePairing':
            groupId = action[1]
            eleId = action[2]
            self.groups[groupId].pair(eleId,False)
            return ('add-group-samePairing',groupId,eleId)
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
            toRet = (label,id,self.textBBs[id][8])
            self.textBBs[id] = self.textBBs[id][0:8]+(code,)+self.textBBs[id][9:]
            return toRet
        elif action[0] == 'change-field':
            label,id,code = action
            toRet = (label,id,self.fieldBBs[id][8])
            self.fieldBBs[id] = self.fieldBBs[id][0:8]+(code,)+self.fieldBBs[id][9:]
            return toRet
        elif action[0] == 'set-field-type':#only occurs with fields
            label,id, ftype= action
            toRet = (label,id,self.fieldBBs[id][9])
            self.fieldBBs[id] = self.fieldBBs[id][0:9]+(ftype,)
            return toRet
        elif action[0] == 'trans':
            label, textIds, fieldIds, trans = action
            invTrans = np.linalg.inv(trans)
            self.transAll(invTrans, textIds=textIds, fieldIds=fieldIds, recordAction=False)
            return (label, textIds, fieldIds, invTrans)
        elif action[0] == 'rotate-orien':
            label, bbs, id, bb = action
            toRet = (label,bbs,id,bbs[id])
            bbs[id]=bb
            return toRet
        elif action[0] == 'create-horzLink':
            label, hlid = action
            toRet = ('remove-horzLink',hlid,self.horzLinks[hlid])
            del self.horzLinks[hlid]
            return toRet
        elif action[0] == 'remove-horzLink':
            label, hlid, link = action
            self.horzLinks[hlid]=link
            return ('create-horzLink',hlid)
        elif action[0]=='add-horzLink':
            label, hlid, id = action
            ind = self.horzLinks[hlid].index(id)
            self.horzLinks[hlid].remove(id)
            return ('minus-horzLink',hlid,id,ind)
        elif action[0]=='minus-horzLink':
            label,hlid,id,index = action
            self.horzLinks[hlid].insert(index,id)
            return ('add-horzLink',hlid,id)
        elif action[0]=='merge-horzLink':
            label,hlid1,link1,hlid2,link2 = action
            toRet = ('unmerge-horzLink',hlid1,hlid2,self.horzLinks[hlid1])
            self.horzLinks[hlid1]=link1
            self.horzLinks[hlid2]=link2
            return toRet
        elif action[0]=='unmerge-horzLink':
            label,hlid1,hlid2,merged = action
            toRet = ('merge-horzLink',hlid1,self.horzLinks[hlid1],hlid2,self.horzLinks[hlid2])
            self.horzLinks[hlid1]=merged
        else:
            print('Unimplemented action: '+str(action[0]))

    def setMode(self,mode):
            self.tmpMode = self.mode
            self.mode=mode
            self.modeRect.set_y(toolYMap[mode])
            self.ax_tool.figure.canvas.draw()

    def moveSelect(self):
            self.mode='move'
            self.modeRect.set_y(toolYMap['move'])
            self.selectedTextIds=[]
            self.selectedFieldIds=[]
            self.ax_tool.figure.canvas.draw()
            self.selected='none'
            self.selectedId=None
            self.setSelectedRectOff()

    #def pairMode(self):
    #        self.tmpMode = self.mode
    #        self.mode='pair'
    #        self.modeRect.set_y(toolYMap['pair'])
    #        self.ax_tool.figure.canvas.draw()
            
    def setSecondaryMode(self,mode):
        self.selected='none'
        self.selectedId=None
        self.setSelectedRectOff()
        if self.secondaryMode==mode:
            self.secondaryMode=None;
            self.secondaryModeRect.set_visible(False)
        else:
            self.secondaryMode=mode
            self.secondaryModeRect.set_visible(True)
            self.secondaryModeRect.set_y(toolYMap[mode])
        self.ax_tool.figure.canvas.draw()
            
    def setFieldType(self,ftype):
        if self.selected=='field':
            self.didAction(('set-field-type',self.selectedId,self.fieldBBs[self.selectedId][9]))
            self.fieldBBs[self.selectedId] = self.fieldBBs[self.selectedId][:9]+(ftype,)
            self.draw()

    def setSelectedPoly(self,poly):
        minX=9999999
        maxX=-1
        minY=9999999
        maxY=-1
        for (x,y) in poly:
            minX=min(minX,x)
            maxX=max(maxX,x)
            minY=min(minY,y)
            maxY=max(maxY,y)
        #print (minX,minY,maxX,minY,maxX,maxY,minX,maxY)
        self.setSelectedRect((minX,minY,maxX,minY,maxX,maxY,minX,maxY),size=30)

    def getSelectedPoly(self,bb, size=15):
        xc=(bb[0]+bb[2]+bb[4]+bb[6])/4.0
        yc=(bb[1]+bb[3]+bb[5]+bb[7])/4.0
        
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
        return np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]])


    def setSelectedRect(self,bb,size=15):
        self.selectedRect.set_xy(self.getSelectedPoly(bb,size))

    def setSelectedRectOff(self):
        self.selectedRect.set_xy(np.array([[0,0],[0.1,0],[0,0.1]]))

    def checkInside(self,x,y,bb):
        if bb[0] is None or bb[1] is None or bb[2] is None or bb[3] is None or bb[4] is None or bb[5] is None or bb[6] is None or bb[7] is None:
            print(bb)
        vertices = [(bb[0],bb[1]),(bb[2],bb[3]),(bb[4],bb[5]),(bb[6],bb[7])]
        return checkInsidePoly(x,y,vertices)

    def drawSelected(self, clear=True):
        if clear:
            for rect in self.selectedRects:
                    rect.remove()
            self.selectedRects=[]
        for id in self.selectedTextIds:
            polyPts = self.getSelectedPoly(self.textBBs[id])
            poly = patches.Polygon(np.array(polyPts),linewidth=2,edgecolor=colorMap['move'],facecolor='none')
            self.ax_im.add_patch(poly)
            self.selectedRects.append(poly)
        for id in self.selectedFieldIds:
            polyPts = self.getSelectedPoly(self.fieldBBs[id])
            poly = patches.Polygon(np.array(polyPts),linewidth=2,edgecolor=colorMap['move'],facecolor='none')
            self.ax_im.add_patch(poly)
            self.selectedRects.append(poly)

        self.ax_im.figure.canvas.draw()

    def draw(self, clear=False):
        self.drawRect.set_xy(np.array([[0,0],[0.1,0],[0,0.1]]))
        
        if self.selected=='field':
            self.setSelectedRect(self.fieldBBs[self.selectedId])
        elif self.selected=='text':
            self.setSelectedRect(self.textBBs[self.selectedId])
        elif self.selected=='row' or self.selected=='col':
            self.setSelectedPoly(self.groups[self.selectedId].getPoly(self))
        else:
            self.setSelectedRectOff()
        self.typed()

        if self.mode != 'trans':
            
            #clear all
            for id,rect in self.textRects.items():
                rect.remove()
            self.textRects={}
            for id,rect in self.fieldRects.items():
                rect.remove()
            self.fieldRects={}
            for id,line in self.pairLines.items():
                line.remove()
            self.pairLines={}
            for id,poly in self.groupPolys.items():
                poly.remove()
            self.groupPolys={}
            for poly in self.arrowPolys:
                    poly.remove()
            self.arrowPolys=[]
            for rect in self.selectedRects:
                    rect.remove()
            self.selectedRects=[]

            if not clear:

                lineId=0
                for id, group in self.groups.items():
                    vertices = group.getPoly(self)
                    ar = []
                    for tup in vertices:
                        ar.append([tup[0],tup[1]])
                    self.groupPolys[id] = patches.Polygon(np.array(ar),linewidth=4,edgecolor=colorMap[group.typeStr],facecolor='none')
                    self.ax_im.add_patch(self.groupPolys[id])

                    for idx in group.pairings:
                        if group.holdsFields:
                            bbs=self.textBBs
                        else:
                            bbs=self.fieldBBs
                        if idx in bbs:
                            x1,y1 = group.getCentroid(self)
                            x2=(bbs[idx][0]+bbs[idx][2]+bbs[idx][4]+bbs[idx][6])/4
                            y2=(bbs[idx][1]+bbs[idx][3]+bbs[idx][5]+bbs[idx][7])/4
                            self.pairLines[lineId]=patches.Arrow(x1,y1,x2-x1,y2-y1,2,edgecolor='turquoise',facecolor='none')
                            self.ax_im.add_patch(self.pairLines[lineId])
                            lineId+=1
                    for idx in group.samePairings:
                        if group.holdsFields:
                            bbs=self.fieldBBs
                        else:
                            bbs=self.textBBs
                        if idx in bbs:
                            x1,y1 = group.getCentroid(self)
                            x2=(bbs[idx][0]+bbs[idx][2]+bbs[idx][4]+bbs[idx][6])/4
                            y2=(bbs[idx][1]+bbs[idx][3]+bbs[idx][5]+bbs[idx][7])/4
                            self.pairLines[lineId]=patches.Arrow(x1,y1,x2-x1,y2-y1,2,edgecolor='orchid',facecolor='none')
                            self.ax_im.add_patch(self.pairLines[lineId])
                            lineId+=1

                #self.displayImage[0:self.image.shape[0], 0:self.image.shape[1]] = self.image
                for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,code,blank) in self.textBBs.items():
                    #cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
                    color = colorMap[RcodeMap[code]]
                    if (self.selected=='row' or self.selected=='col') and not self.groups[self.selectedId].holdsFields and self.groups[self.selectedId].contains(id):
                        color = (color[0]/2.0, color[1]/2.0, color[2]/2.0,)+color[3:]
                    self.textRects[id] = patches.Polygon(np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]]),linewidth=2,edgecolor=color,facecolor='none')
                    self.ax_im.add_patch(self.textRects[id])
                    
                    if self.selected=='text' and self.selectedId==id:
                        color = (color[0]/2.0, color[1]/2.0, color[2]/2.0,2.0)
                    arrow = self.createArrow(tlX,tlY,trX,trY,brX,brY,blX,blY,color)
                    self.arrowPolys.append(arrow)
                    self.ax_im.add_patch(arrow)

                for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,code,ftype) in self.fieldBBs.items():
                    #cv2.rectangle(self.displayImage,(startX,startY),(endX,endY),colorMap[RcodeMap[code]],1)
                    fill = 'none'
                    if ftype==ftypeMap['blank']:
                        fill=(0.5,0.5,0.9,0.25)
                    elif ftype==ftypeMap['print']:
                        fill=(0.9,0.3,0.5,0.15)
                    elif ftype==ftypeMap['signature']:
                        fill=(0.3,0.9,0.5,0.1)
                    color = colorMap[RcodeMap[code]]
                    if (self.selected=='row' or self.selected=='col') and self.groups[self.selectedId].holdsFields and self.groups[self.selectedId].contains(id):
                        color = (color[0]/2.0, color[1]/2.0, color[2]/2.0,)+color[3:]
                    self.fieldRects[id] = patches.Polygon(np.array([[tlX,tlY],[trX,trY],[brX,brY],[blX,blY]]),linewidth=2,edgecolor=color,facecolor=fill)
                    self.ax_im.add_patch(self.fieldRects[id])

                    if RcodeMap[code]!='graphic' and RcodeMap[code]!='fieldRow' and RcodeMap[code]!='fieldCol' and RcodeMap[code]!='fieldCheckBox' and RcodeMap[code]!='fieldRegion':

                        if self.selected=='field' and self.selectedId==id:
                            color = (color[0]/2.0, color[1]/2.0, color[2]/2.0,color[3]*1.5)
                        arrow = self.createArrow(tlX,tlY,trX,trY,brX,brY,blX,blY,color)
                        self.arrowPolys.append(arrow)
                        self.ax_im.add_patch(arrow)

                for hlid, link in self.horzLinks.items():
                    pointsTop=[]
                    pointsBot=[]
                    rot=None
                    sel=False
                    for lid in link:
                        id=int(lid[1:])
                        if lid[0]=='t':
                            bbs=self.textBBs
                            sel = self.selected=='text' and self.selectedId==id
                        elif lid[0]=='f':
                            bbs=self.fieldBBs
                            sel = self.selected=='field' and self.selectedId==id
                        if id in bbs:
                            if rot is None:
                                rot=self.getRotation(bbs[id])
                                #print(rot)
                            #print(bbs[id])

                            if (len(pointsTop)==0 or 
                                    (rot=='left-right' and bbs[id][0]>pointsTop[-1][0]) or
                                    (rot=='right-left' and bbs[id][0]<pointsTop[-1][0]) or
                                    (rot=='up' and bbs[id][1]<pointsTop[-1][1]) or
                                    (rot=='down' and bbs[id][1]>pointsTop[-1][1]) ):
                                pointsTop.append(bbs[id][0:2])
                            else:
                                pointsTop[-1]=( (pointsTop[-1][0]+bbs[id][0])/2.0, (pointsTop[-1][1]+bbs[id][1])/2.0 )
                            #pointsTop.append(bbs[id][0:2])
                            pointsTop.append(bbs[id][2:4])

                            if len(pointsBot)==0 or ( 
                                    (rot=='left-right' and bbs[id][6]>pointsBot[-1][0]) or
                                    (rot=='right-left' and bbs[id][6]<pointsBot[-1][0]) or
                                    (rot=='up' and bbs[id][7]<pointsBot[-1][1]) or
                                    (rot=='down' and bbs[id][7]>pointsBot[-1][1]) ):
                                pointsBot.append(bbs[id][6:8])
                            else:
                                pointsBot[-1]=( (pointsBot[-1][0]+bbs[id][6])/2.0, (pointsBot[-1][1]+bbs[id][7])/2.0 )
                            #pointsBot.append(bbs[id][6:8])
                            pointsBot.append(bbs[id][4:6])
                    pointsBot.reverse()
                    #print(pointsTop)
                    #print(pointsBot)
                    if self.mode=='horzLink':
                        if sel:
                            color=(0,1,0,0.8)
                        else:
                            color=(0,1,0,0.6)
                    if sel:
                        color=(0,1,0,0.4)
                    else:
                        color=(0,1,0,0.2)
                    self.pairLines[lineId] = patches.Polygon(np.array(pointsTop+pointsBot),linewidth=3,edgecolor=color,fill=False)
                    self.ax_im.add_patch(self.pairLines[lineId])
                    lineId+=1
                
                toRemove=[]
                for text,field in self.pairing:
                    if text not in self.textBBs or field not in self.fieldBBs:
                        toRemove.append((text,field))
                        continue
                    x1=(self.textBBs[text][0]+self.textBBs[text][2]+self.textBBs[text][4]+self.textBBs[text][6])/4
                    y1=(self.textBBs[text][1]+self.textBBs[text][3]+self.textBBs[text][5]+self.textBBs[text][7])/4
                    x2=(self.fieldBBs[field][0]+self.fieldBBs[field][2]+self.fieldBBs[field][4]+self.fieldBBs[field][6])/4
                    y2=(self.fieldBBs[field][1]+self.fieldBBs[field][3]+self.fieldBBs[field][5]+self.fieldBBs[field][7])/4
                    #cv2.line(self.displayImage,(x1,y1),(x2,y2),(0,255,0),1)
                    self.pairLines[lineId]=patches.Arrow(x1,y1,x2-x1,y2-y1,2,edgecolor='g',facecolor='none')
                    self.ax_im.add_patch(self.pairLines[lineId])
                    lineId+=1
                for inst in toRemove:
                    self.pairing.remove(inst)

                toRemove=[]
                for a,b,field in self.samePairing:
                    if field:
                        bbs=self.fieldBBs
                    else:
                        bbs=self.textBBs
                    if a not in bbs or b not in bbs:
                        toRemove.append((a,b,field))
                        continue
                    x1=(bbs[a][0]+bbs[a][2]+bbs[a][4]+bbs[a][6])/4
                    y1=(bbs[a][1]+bbs[a][3]+bbs[a][5]+bbs[a][7])/4
                    x2=(bbs[b][0]+bbs[b][2]+bbs[b][4]+bbs[b][6])/4
                    y2=(bbs[b][1]+bbs[b][3]+bbs[b][5]+bbs[b][7])/4
                    #cv2.line(self.displayImage,(x1,y1),(x2,y2),(0,255,0),1)
                    self.pairLines[lineId]=patches.Arrow(x1,y1,x2-x1,y2-y1,2,edgecolor='purple',facecolor='none')
                    self.ax_im.add_patch(self.pairLines[lineId])
                    lineId+=1
                for inst in toRemove:
                    self.samePairing.remove(inst)
            else:
                #text stuff
                pass
        if self.mode=='move':
            self.drawSelected(clear=False)
        else:
            self.ax_im.figure.canvas.draw()

    def getRotation(self,bb): #read direction
        if max(bb[1],bb[3])<min(bb[5],bb[7]) and max(bb[0],bb[6])<min(bb[2],bb[4]):
            return 'left-right'
        elif max(bb[0],bb[2])<min(bb[6],bb[4]) and max(bb[3],bb[5])<min(bb[1],bb[7]):
            return 'up'
        elif min(bb[1],bb[3])>max(bb[5],bb[7]) and min(bb[0],bb[6])>max(bb[2],bb[4]):
            return 'right-left'
        elif max(bb[6],bb[4])<min(bb[0],bb[2]) and max(bb[7],bb[1])<min(bb[5],bb[3]):
            return 'down'
        else:
            return 'diag'

    def createArrow(self,tlX,tlY,trX,trY,brX,brY,blX,blY,color):
        lX = (tlX+blX)/2.0
        lY = (tlY+blY)/2.0
        rX = (trX+brX)/2.0
        rY = (trY+brY)/2.0
        d=math.sqrt((lX-rX)**2 + (lY-rY)**2)
        if rX-lX!=0:
            s = (rY-lY)/(rX-lX)
            ds = math.sqrt(s**2 + 1)
            arrLen = min(d*0.25,MAX_ARR_LEN)
            pX = lX+math.copysign(arrLen/ds,rX-lX)
            pY = lY+math.copysign(s*arrLen/ds,rY-lY)
        else:
            arrLen = min(abs(rY-lY)*0.25,MAX_ARR_LEN)
            pX = lX
            pY = lY+math.copysign(arrLen,rY-lY)

        hl = ((tlX-lX)*-(rY-lY) + (tlY-lY)*(rX-lX))/d #projection of half-left edge onto transpose horz run
        hr = ((brX-rX)*-(lY-rY) + (brY-rY)*(lX-rX))/d #projection of half-right edge onto transpose horz run
        h = (hl+hr)/2.0

        tX = lX + h*-(rY-lY)/d
        tY = lY + h*(rX-lX)/d
        bX = lX - h*-(rY-lY)/d
        bY = lY - h*(rX-lX)/d
        color = color[0:3]+(color[3]/2.0,)
        return patches.Polygon(np.array([[lX,lY],[tX,tY],[pX,pY],[bX,bY],[lX,lY],[pX,pY]]),linewidth=2,edgecolor=color,facecolor='none')

    def getDividingLine(self,mX,mY,tlX,tlY,trX,trY,brX,brY,blX,blY):
        vTop = np.array([trY-tlY,trX-tlX])
        vTop=vTop/np.linalg.norm(vTop)
        vmTop = np.array([mY-tlY,mX-tlX])
        dTop = vTop.dot(vmTop)
        print(('vTop:{}, vmTop:{}, dTop:{}'.format(vTop,vmTop,dTop)))
        pointTop = np.array([tlY,tlX]) + dTop*vTop
        print(pointTop)
        vBot = np.array([brY-blY,brX-blX])
        vBot=vBot/np.linalg.norm(vBot)
        vmBot = np.array([mY-blY,mX-blX])
        dBot = vBot.dot(vmBot)
        pointBot = np.array([blY,blX]) + dBot*vBot
        return (pointTop[1],pointTop[0]), (pointBot[1],pointBot[0])


def drawToolbar(ax):
    #im[0:,-TOOL_WIDTH:]=(140,140,140)
    im = np.zeros(((toolH+1)*(len(modes)+22),TOOL_WIDTH,3),dtype=np.uint8)
    im[:,:] = (140,140,140)

    y=0

    for mode in modes:
        im[y:y+toolH,:]=(255*colorMap[mode][0],255*colorMap[mode][1],255*colorMap[mode][2])
        #if self.mode==mode:
        #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-1,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
        #cv2.putText(im,toolMap[mode],(im.shape[1]TOOL_WIDTH-3,y+toolH-3),cv2.FONT_HERSHEY_PLAIN,2.0,(40,40,40))
        #patches.Polygon((,linewidth=2,edgecolor=colorMap[mode],facecolor=fill)
        textColor='black'
        if mode=='fieldRegion' or mode=='fieldCol' or mode=='fieldRow':
            textColor='white'
        ax.text(1,y+toolH-10,toolMap[mode],color=textColor)
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
    ax.text(1,y+toolH-10,'D:switch BB type')
    toolYMap['change']=y
    y+=toolH+1

    #pair
    im[y:y+toolH,:]=(19,160,19)
    ax.text(1,y+toolH-10,'F:pair mode')
    toolYMap['pair']=y
    y+=toolH+1

    #delete
    im[y:y+toolH,:]=(250,250,250)
    #if self.mode=='delete':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-10,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-10,'G:delete')
    toolYMap['delete']=y
    y+=toolH+1

    #pair
    im[y:y+toolH,:]=(10,250,10)
    ax.text(1,y+toolH-10,'H:horz link mode')
    toolYMap['horzLink']=y
    y+=toolH+1

    #rotateOrien
    im[y:y+toolH,:]=(80,80,150)
    #if self.mode=='delete':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-10,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-10,'J:rotate BB orientation')
    toolYMap['rotateOrien']=y
    y+=toolH+1

    #copy
    im[y:y+toolH,:]=(5,5,5)
    #if self.mode=='delete':
    #    cv2.rectangle(im,(im.shape[1]TOOL_WIDTH-10,y),(im.shape[1]-1,y+toolH),(255,0,255),2)
    ax.text(1,y+toolH-10,'K:copy selected BB', color=(1,1,1))
    toolYMap['copy']=y
    y+=toolH+1

    #move
    im[y:y+toolH,:]=(202,22,202)
    ax.text(1,y+toolH-10,'M:select and move')
    toolYMap['move']=y
    y+=toolH+1

    #print
    im[y:y+toolH,:]=(255, 230, 242)
    ax.text(1,y+toolH-10,'Z:mark field as print/stamp')
    toolYMap['print']=y
    y+=toolH+1

    #blank
    im[y:y+toolH,:]=(240,240,255)
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

    #signature
    im[y:y+toolH,:]=(235,250,235)
    ax.text(1,y+toolH-10,'V:mark field as signature')
    toolYMap['signature']=y
    y+=toolH+1

    #col
    im[y:y+toolH,:]=(255*colorMap['col'][0],255*colorMap['col'][1],255*colorMap['col'][2]) #(5,50,5)
    ax.text(1,y+toolH-10,';:special col mode', color=(1,1,1))
    toolYMap['col']=y
    y+=toolH+1

    #row
    im[y:y+toolH,:]=(255*colorMap['row'][0],255*colorMap['row'][1],255*colorMap['row'][2]) #(45,45,5)
    ax.text(1,y+toolH-10,"':special row mode", color=(1,1,1))
    toolYMap['row']=y
    y+=toolH+1

    #translate
    im[y:y+toolH,:]=(30,30,30)
    ax.text(1,y+toolH-10,'Arrow keys:move all labels', color=(1,1,1))
    toolYMap['translate']=y
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

    #shift
    im[y:y+toolH,:]=(50,40,40)
    ax.text(1,y+toolH-10,'SHIFT (hold):to drag corners', color=(1,1,1))
    toolYMap['corners']=y
    y+=toolH+1

    #enter
    im[y:y+toolH,:]=(5,35,5)
    ax.text(1,y+toolH-10,'ENTER: complete, save-close', color=(1,1,1))
    toolYMap['quit']=y
    y+=toolH+1

    #esc
    im[y:y+toolH,:]=(5,5,35)
    ax.text(1,y+toolH-10,'ESC: incomplete, save-close', color=(1,1,1))
    toolYMap['quitNF']=y
    y+=toolH+1

    #f12
    im[y:y+toolH,:]=(25,0,0)
    ax.text(1,y+toolH-10,'F12: close without saving', color=(1,1,1))
    toolYMap['quitNS']=y
    y+=toolH+1

    return im

    #cv2.imshow("labeler",self.displayImage)
        

def labelImage(imagePath,texts,fields,pairs,samePairs,horzLinks,groups,transcriptions,pre_corners=None, page_corners=None, page_cornersActual=None):
    #p = Params()
    image = mpimg.imread(imagePath)
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
    control = Control(ax_im,ax_tool,image.shape[1],image.shape[0],texts,fields,pairs,samePairs,horzLinks,groups,transcriptions,pre_corners, page_corners, page_cornersActual)
    #control.draw()
    plt.show()

    allIds=set()
    #idToIdxText={}
    textBBs=[]
    for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in control.textBBs.items():
        #idToIdxText[id]=len(textBBs)
        textBBs.append({
            #'id': 't'+str(idToIdxText[id]),
                        'id': 't'+str(id),
                        'poly_points':[[int(round(tlX)),int(round(tlY))],[int(round(trX)),int(round(trY))],[int(round(brX)),int(round(brY))],[int(round(blX)),int(round(blY))]],
                        'type':RcodeMap[para]
                       })
        allIds.add(textBBs[-1]['id'])
    #idToIdxField={}
    fieldBBs=[]
    for id, (tlX,tlY,trX,trY,brX,brY,blX,blY,para,blank) in control.fieldBBs.items():
        pp=[[int(round(tlX)),int(round(tlY))],[int(round(trX)),int(round(trY))],[int(round(brX)),int(round(brY))],[int(round(blX)),int(round(blY))]]
        if invalidPoly(pp):
            continue
        #idToIdxField[id]=len(fieldBBs)
        fieldBBs.append({
            #'id': 'f'+str(idToIdxField[id]),
                        'id': 'f'+str(id),
                        'poly_points': pp,
                        'type':RcodeMap[para],
                        'isBlank':blank,
                       })
        allIds.add(fieldBBs[-1]['id'])
    pairing=[]
    for text,field in control.pairing:
        #pairing.append(('t'+str(idToIdxText[text]),'f'+str(idToIdxField[field])))
        pairing.append(('t'+str(text),'f'+str(field)))
    samePairing=[]
    for a,b,field in control.samePairing:
        if field:
            #idToIdx = idToIdxField
            typ='f'
        else:
            #idToIdx = idToIdxText
            typ='t'
        #samePairing.append((typ+str(idToIdx[a]),typ+str(idToIdx[b])))
        samePairing.append((typ+str(a),typ+str(b)))
    #horzLinks=[link for hid,link in control.horzLinks.iteritems()]
    horzLinks=[]
    for hid,link in control.horzLinks.items():
        newLink = [id for id in link if id in allIds] #we don't ever remove deleted bb ids, do it here
        #newLink = []
        #for id in link:
        #    if id in allIds
        horzLinks.append(newLink)
        

    groups=[]
    for id,group in control.groups.items():
        elements=[]
        if group.holdsFields:
            #idToIdx = idToIdxField
            typ='f'
        else:
            #idToIdx = idToIdxText
            typ='t'
        for eleId in group.elements:
            if typ+str(eleId) in allIds:
                elements.append(typ+str(eleId))
        if len(elements)>0:
            samePairings=[]
            for eleId in group.samePairings:
                if typ+str(eleId) in allIds:
                    samePairings.append(typ+str(eleId))
            pairings=[]
            if not group.holdsFields:
                #idToIdx = idToIdxField
                typ='f'
            else:
                #idToIdx = idToIdxText
                typ='t'
            for eleId in group.pairings:
                if typ+str(eleId) in allIds:
                    pairings.append(typ+str(eleId))
            newGroup= { 'id': 'g'+str(len(groups)),
                        'type':group.typeStr,
                        'holds': ('field' if group.holdsFields else 'text'),
                        'elements': elements,
                        'pairings': pairings,
                        'samePairings': samePairings,
                      }
            groups.append(newGroup)


    return textBBs, fieldBBs, pairing, samePairing, horzLinks, groups, control.transcriptions, control.corners, control.cornersActual, control.complete, image.shape[0], image.shape[1]

if __name__ == "__main__":

    texts=None
    fields=None
    pairs=None
    samePairs=None
    horzLinks=None
    groups=None
    page_corners=None
    if len(sys.argv)>4:
        with open(sys.argv[4]) as f:
            read = json.loads(f.read())
            texts=read['textBBs']
            fields=read['fieldBBs']
            pairs=read['pairs']
            samePairs=read['samePairs']
            if 'horzLinks' in read:
                horzLinks=read['horzLinks']
            #for i in len(samePairs):
            #    if samePairs[i][-1][0]=='f':
            groups=read['groups']
                    
            page_corners=read['page_corners']

    imageName = sys.argv[1][(sys.argv[1].rfind('/')+1):]
    texts,fields,pairs,samePairs,horzLinks,groups,corners,actualCorners,complete,H,W = labelImage(sys.argv[1],texts,fields,pairs,samePairs,horzLinks,groups,page_corners)
    outFile='test.json'
    if len(texts)+len(fields)+len(corners)>0:
        with open(outFile,'w') as out:
            out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "horzLinks":horzLinks, "groups":groups, "page_corners":corners, "actualPage_corners":actualCorners,  "imageFilename":imageName, 'height':H, 'width':W}))
