import sysz
import cv2

def clicker(event, x, y, flags, p):
    #image,displayImage,mode,textBBs,fieldBBs,pairing = param

    if event == cv2.EVENT_LBUTTONDOWN:
        if mode!='none' and mode!='delete':
            mode+='-d'
            p.startX=x
            p.startY=y
    elif event == cv2.EVENT_LBUTTONUP:
        if '-m' == p.mode[-2:]:
            p.mode=p.mode:[-2]
            if p.mode=='text':
                p.textBBs.insert((p.startX,p.startY,p.endX,p.endY,0))
                p.actionQueue.insert(('insert-text',p.startX,p.startY,p.endX,p.endY,0))
                p.selectedIdx=len(p.textBBs)-1
                p.selected='text'
            elif p.mode=='textP':
                p.textBBs.insert((p.startX,p.startY,p.endX,p.endY,1))
                p.actionQueue.insert(('insert-textP',p.startX,p.startY,p.endX,p.endY,1))
                p.selectedIdx=len(p.textBBs)-1
                p.selected='text'
            elif p.mode=='field':
                p.fieldBBs.insert((p.startX,p.startY,p.endX,p.endY,0))
                p.actionQueue.insert(('insert-field',p.startX,p.startY,p.endX,p.endY,0))
                p.selectedIdx=len(p.fieldBBs)-1
                p.selected='field'
            elif p.mode=='fieldP':
                p.fieldBBs.insert((p.startX,p.startY,p.endX,p.endY,1))
                p.actionQueue.insert(('insert-fieldP',p.startX,p.startY,p.endX,p.endY,1))
                p.selectedIdx=len(p.fieldBBs)-1
                p.selected='field'
            draw(p)
        else:
            if '-d' == p.mode[-2:]:
                p.mode=p.mode:[-2]

            if mode=='delete':
                for index,(text,field) in enumerate(p.pairing):
                    #if within bounds of line and within distance from it
                    x1=(p.textBBs[text][0]+p.textBBs[text][2])/2.0
                    y1=(p.textBBs[text][1]+p.textBBs[text][3])/2.0
                    x2=(p.fieldBBs[field][0]+p.fieldBBs[field][2])/2.0
                    y2=(p.fieldBBs[field][1]+p.fieldBBs[field][3])/2.0

                    if x>=min(x1,x2) and x<=max(x1,x2) and y>=min(y1,y2) and y<=max(y1,y2) and abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1)/Math.sqrt(pow(y2-y1,2) + pow(x2-x1,2)) < 3.5:
                        p.actionQueue.insert(('remove-pairing',text,field))
                        del p.pairing[index]
                        draw(p)
                        return

            for index, (startX,startY,endX,endY,para) in enumerate(p.textBBs):
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if mode=='delete':
                        p.actionQueue.insert(('remove-text',startX,startY,endX,endY,para))
                        del p.textBBs[index]
                    else:
                        if p.selected=='field' and (index,p.selectedIdx) not in p.pairing:
                            p.pairing.append((index,p.selectedIdx))
                            p.actionQueue.insert(('insert-pairing',index,p.selectedIdx))
                        p.selectedIdx=index
                        p.selected='text'
                    draw(p)
                    return

            for index, (startX,startY,endX,endY,para) in enumerate(p.fieldBBs):
                if x>=startX and x<=endX and y>=startY and y<=endY:
                    if mode=='delete':
                        p.actionQueue.insert(('remove-field',startX,startY,endX,endY,para))
                        del p.textBBs[index]
                    else:
                        if p.selected=='text' and (p.selectedIdx,index) not in p.pairing:
                            p.pairing.append((p.selectedIdx,index))
                            p.actionQueue.insert(('insert-pairing',p.selectedIdx,index))
                        p.selectedIdx=index
                        p.selected='field'
                    draw(p)
                    return

            
    elif event == cv2.EVENT_MOUSEMOVE:
        if '-d' == p.mode[-2:]:
            p.mode = p.mode[:-1]+'m'
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


def labelImage(imagePath,displayH,displayW):
    p = Params()
    p.image = cv2.imread(imagePath)
    if p.image is None:
        print 'cannot open image '+imagePath
        exit(1)
    scale = min(displayH/p.image.shape[0],(displayW-TOOL_WIDTH)/p.image.shape[1])
    cv2.resize(p.image,(0,0),p.image,scale,scale)
    


    cv2.namedWindow("labeler")
    cv2.setMouseCallback("labeler", clicker,param=p)
    draw(p)
    drawToolbar(p)
    #cv2.imshow('labeler',p.displayImage)

    while True:
        key = cv2.waitKey() & 0xFF
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
    return textBBs, fieldBBs, pairing
