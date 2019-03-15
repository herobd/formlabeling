import os
import sys
import json
from random import shuffle
import random
#import Tkinter
#import tkMessageBox
import numpy as np
import math
from collections import defaultdict
from forms_annotations import fixAnnotations
NUM_PER_GROUP=2
NUM_CHECKS=2
USE_SIMPLE=True

if len(sys.argv)<2:
    print 'usage: '+sys.argv[0]+' directory [+:add] [-[-]:progress] [c:create split] [f:poputate info from template [group]] [s:stats]'
    exit()

directory = sys.argv[1]
progress=False
add=False
makesplit=False
saveall=False
populate=False
onlyGroup=None
tableList=False
getStats=False
if len(sys.argv)>2:
    if sys.argv[2][0]=='-' or sys.argv[2][0]=='p':
        progress=True
    elif sys.argv[2][0]=='+':
        add=True
    elif sys.argv[2][0]=='c':# or sys.argv[2][0]=='s' :
        makesplit=True
        mixsplit=False
        if len(sys.argv[2])>1 and sys.argv[2][1]=='m':
            mixsplit=True
        elif len(sys.argv[2])>1 and sys.argv[2][1]=='s':
            simpleDataset=True
        else:
            simpleDataset=False
    elif sys.argv[2][0]=='a':
        saveall=True
        USE_SIMPLE=False
    elif sys.argv[2][0]=='s':
        getStats=True
        if len(sys.argv[2])>1 and sys.argv[2][1]=='m':
            mimic_dataset=True
            mimic_object=type('test', (object,), {})()
            mimic_object.no_blanks=True
            mimic_object.no_print_fields=False
            mimic_object.no_graphics=True
            mimic_object.only_opposite_pairs=True
            mimic_object.swapCircle=True
            if len(sys.argv[2])>2:
                doSplit=sys.argv[2][2:]
            else:
                doSplit=False
        else:
            if len(sys.argv[2])>1:
                doSplit=sys.argv[2][1:]
            else:
                doSplit=False
            mimic_dataset=False
    elif sys.argv[2][0]=='f':
        populate=True
        if len(sys.argv)>3:
            onlyGroup=sys.argv[3]
    elif sys.argv[2][0]=='t':
        tableList=True
    else:
        startHere = sys.argv[2]
        going=False
else:
    progress=True

if directory[-1]!='/':
    directory=directory+'/'
rr=directory[directory[:-1].rindex('/')+1:-1]
if USE_SIMPLE:
    with open(os.path.join(directory,'simple_train_valid_test_split.json')) as f:
        splitFile = json.load(f)
else:
    with open(os.path.join(directory,'train_valid_test_split.json')) as f:
        splitFile = json.load(f)
if getStats:
    if doSplit:
        simpleFiles = splitFile[doSplit]
    else:
        simpleFiles = dict(splitFile['train'].items()+ splitFile['valid'].items())
else:
    simpleFiles = dict(splitFile['train'].items()+ splitFile['test'].items()+ splitFile['valid'].items())
imageGroups={}
groupNames=[]
for root, dirs, files in os.walk(directory):
    #print 'root: '+root
    if root[-1]=='/':
        root=root[:-1]
    groupName = root[root.rindex('/')+1:]
    if rr==groupName:
        continue
    if (not USE_SIMPLE and not getStats) or groupName in simpleFiles:
        imageGroups[groupName]=sorted(files)
        groupNames.append(groupName)

if progress:
    numTemplateDone=0
    temped=[]
    numDoneTotal=0
    numCheckedTotal=0
    realDoneTotal=0
    numTotal=0
    numTimed=0
    timed=[]
    timedAlign=[]
    timedIsTemp=[]
    timeTotal=0
    numTempTimed=0
    timeTemp=0
    numDoneTrain=0
    numDoneTest=0
    numDoneValid=0
    if len(sys.argv)>2 and len(sys.argv[2])>1:
        doTime=True
    else:
        doTime=False
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imagesInGroup=0
        numDoneG=0
        templateImage=None
        timesByImage={}
        for f in files:
            if 'lock' not in f:
                if f[-4:]=='.jpg' or f[-5:]=='.jpeg' or f[-4:]=='.png':
                    imagesInGroup+=1
                elif 'templa' in f and f[-5:]=='.json':
                    numTemplateDone+=1
                    if doTime:
                        with open(os.path.join(directory,groupName,f)) as annFile:
                            read = json.loads(annFile.read())
                            if 'labelTime' in read and read['labelTime'] is not None:
                                numTempTimed+=1
                                temped.append(read['labelTime'])
                                timeTemp+=read['labelTime']
                            assert templateImage is None
                            templateImage = read['imageFilename']
                elif f[-5:]=='.json':
                    numDoneG+=1
                    if groupName in splitFile['train']:
                        numDoneTrain+=1
                    elif groupName in splitFile['test']:
                        numDoneTest+=1
                    elif groupName in splitFile['valid']:
                        numDoneValid+=1
                    if doTime:
                        with open(os.path.join(directory,groupName,f)) as annFile:
                            read = json.loads(annFile.read())
                            if 'labelTime' in read and read['labelTime'] is not None:
                                numTimed+=1
                                timeTotal+=read['labelTime']
                                timed.append(read['labelTime'])
                                timesByImage[read['imageFilename']]=read['labelTime']
                            if 'checkedBy' in read:
                                #print(read['checkedBy'])
                                #numCheckedTotal+=len(read['checkedBy'])
                                numCheckedTotal += len( [x for x in read['checkedBy'] if x!='doublecheck'])
        for image,time in timesByImage.iteritems():
            if image!=templateImage:
                timedAlign.append(time)
            else:
                timedIsTemp.append(time)
        numDoneTotal += min(numDoneG,NUM_PER_GROUP)
        numTotal += min(imagesInGroup,NUM_PER_GROUP)
        realDoneTotal += max(numDoneG,NUM_PER_GROUP)
    checksNeeded = NUM_CHECKS*realDoneTotal
    print('Templates: {}/{}  {}'.format(numTemplateDone,len(groupNames),float(numTemplateDone)/len(groupNames)))
    print('Images:    {}/{}  {}'.format(numDoneTotal,numTotal,float(numDoneTotal)/numTotal))
    print('Checking:    {}/{}  {}'.format(numCheckedTotal,checksNeeded,float(numCheckedTotal)/checksNeeded))
    print('Num train:{}, valid:{}, test:{}'.format(numDoneTrain,numDoneValid,numDoneTest))
    if doTime:
        timeTotal/=numTimed
        timeTemp/=numTempTimed
        print (' Templates take {} secs, or {} minutes   ({} samples)'.format(timeTemp,timeTemp/60,numTempTimed))
        med = np.median(temped)
        print (' Templates(Med) take {} secs, or {} minutes   ({} samples)'.format(med,med/60,numTempTimed))
        print ('Alignment(Mean) takes {} secs, or {} minutes   ({} samples)'.format(timeTotal,timeTotal/60,numTimed))
        stddev = np.std(timed)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))
        med = np.median(timed)
        print ('Alignment(Med) takes {} secs, or {} minutes   ({} samples)'.format(med,med/60,numTimed))

        print ('\nThresholding long times...')
        thresh = stddev*2 + timeTotal
        new_time=[t for t in timed if t<thresh and t>0]
        new_temped=[t for t in temped if t<thresh and t>0]
        new_timeA=[t for t in timedAlign if t<thresh and t>0]
        new_timeT=[t for t in timedIsTemp if t<thresh and t>0]

        mean = np.mean(new_temped)
        print ('Templating(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_temped)))
        stddev = np.std(new_temped)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

        mean = np.mean(new_time)
        print ('Alignment(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_time)))
        stddev = np.std(new_time)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

        
        mean = np.mean(new_timeA)
        print ('Alignment not temp(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_timeA)))
        stddev = np.std(new_timeA)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

        mean = np.mean(new_timeT)
        print ('Alignment is temp(Mean) takes {} secs, or {} minutes   ({} samples)'.format(mean,mean/60,len(new_timeT)))
        stddev = np.std(new_timeT)
        print ('   std dev {} secs, or {} minutes'.format(stddev,stddev/60))

    
if add:
    import matplotlib.image as mpimg
    count=0
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        for f in files:
            if f[-5:]=='.json' and 'template' not in f:
                #print('{} / {}'.format(groupName,f))
                with open(os.path.join(directory,groupName,f)) as annFile:
                    read = json.loads(annFile.read())
                if 'height' not in read or 'width' not in read:
                    image = mpimg.imread(os.path.join(directory,groupName,f[:-5]+'.jpg'))
                    read['height']=image.shape[0]
                    read['width']=image.shape[1]
                    with open(os.path.join(directory,groupName,f),'w') as annFile:
                        annFile.write(json.dumps(read))
                        count+=1
    print 'added to '+str(count)+' jsons'

if populate:
    count=0
    for groupName in sorted(groupNames):
        if onlyGroup is not None and groupName!=onlyGroup:
            continue
        files = imageGroups[groupName]
        tempHorz=None
        for f in files:
            if 'template' in f and f[-5:]=='.json':
                with open(os.path.join(directory,groupName,f)) as tempf:
                    read = json.loads(tempf.read())
                    if 'horzLinks' in read:
                        tempHorz=read['horzLinks']
                break
        if tempHorz is not None:
            for f in files:
                if f[-5:]=='.json' and 'template' not in f:
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    if 'horzLinks' not in read or len(read['horzLinks'])==0:
                        allIds = set()
                        #for bb in read['textBBs']:
                        #    addIds.add(bb['id'])
                        #for bb in read['fieldBBs']:
                        #    addIds.add(bb['id'])
                        read['horzLinks']=tempHorz
                        with open(os.path.join(directory,groupName,f),'w') as annFile:
                            annFile.write(json.dumps(read))
                            count+=1
    print 'added to '+str(count)+' jsons'


if tableList:
    groupImages={}#defaultdict(list)
    groupTablePresence={}
    sumCountField =0
    sumCountText =0
    count=0
    tableGroups=[]
    circleGroups=[]
    upsidedown=[]
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imageFiles=[]
        tempFound=False
        hasTable=False
        circleFound=False
        for f in files:
            if 'lock' not in f:
                if f[-4:]=='.jpg' or f[-5:]=='.jpeg' or f[-4:]=='.png':
                    imageFiles.append(f)
                elif 'template' in f and f[-5:]=='.json':
                    tempFound=True
                    validTemp=False
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    for bb in read['fieldBBs']:
                        if bb['type']=='fieldCol' or bb['type']=='fieldRow':
                            hasTable=True
                            if validTemp:
                                break
                        if bb['type']!='fieldCol' and bb['type']!='fieldRow':
                            validTemp=True
                            if hasTable:
                                break
                        if bb['type']=='fieldCircle':
                            circleFound=True
                elif f[-5:]=='.json':
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    upsideDownCount=0
                    total=0
                    for bb in read['fieldBBs']:
                        if bb['type']=='fieldRow' or bb['type']=='fieldCol' or bb['type']=='fieldRegion' or bb['type']=='textRegion' or bb['type']=='graphic':
                            continue
                        tlX = bb['poly_points'][0][0]
                        tlY = bb['poly_points'][0][1]
                        trX = bb['poly_points'][1][0]
                        trY = bb['poly_points'][1][1]
                        brX = bb['poly_points'][2][0]
                        brY = bb['poly_points'][2][1]
                        blX = bb['poly_points'][3][0]
                        blY = bb['poly_points'][3][1]
                        lX = (tlX+blX)/2.0
                        lY = (tlY+blY)/2.0
                        rX = (trX+brX)/2.0
                        rY = (trY+brY)/2.0
                        rot=np.arctan2((rY-lY),rX-lX)
                        total+=1
                        if rot>1 and rot<2:
                            upsideDownCount+=1
                    for bb in read['textBBs']:
                        tlX = bb['poly_points'][0][0]
                        tlY = bb['poly_points'][0][1]
                        trX = bb['poly_points'][1][0]
                        trY = bb['poly_points'][1][1]
                        brX = bb['poly_points'][2][0]
                        brY = bb['poly_points'][2][1]
                        blX = bb['poly_points'][3][0]
                        blY = bb['poly_points'][3][1]
                        lX = (tlX+blX)/2.0
                        lY = (tlY+blY)/2.0
                        rX = (trX+brX)/2.0
                        rY = (trY+brY)/2.0
                        rot=np.arctan2((rY-lY),rX-lX)
                        total+=1
                        if rot>1 and rot<2:
                            upsideDownCount+=1
                    if upsideDownCount/float(total) > 0.4:
                        upsidedown.append(groupName+'/'+f)

                #elif f[-5:]=='.json' and 'temp' not in f:

        if tempFound and validTemp and hasTable:
            tableGroups.append(groupName)
            #groupImages[groupName]=imageFiles
            #groupTablePresence[groupName]=hasTable
        if tempFound and circleFound:
            circleGroups.append(groupName)
    print('Tables: {}'.format(tableGroups))
    print('Circles: {}'.format(circleGroups))
    print('Upsidedown: {}'.format(upsidedown))
if getStats:
    groupImages={}#defaultdict(list)
    sumCountTotal =0
    maxBoxes=0
    count=0
    widths=[]
    heights=[]
    ratios=[]
    rots=[]
    widths_norot=[]
    heights_norot=[]
    ratios_norot=[]
    bbs=[]
    page_heights=[]
    page_widths=[]
    page_areas=[]
    numBBs=[]
    numNeighbors=([],[])
    neighborXDiff=([],[])
    neighborYDiff=([],[])
    numNeighbors_same=([],[])
    neighborXDiff_same=([],[])
    neighborYDiff_same=([],[])
    numNeighborsHist = [0]*10
    totalText=0
    totalField=0
    totalRelationships=0
    totalRelationshipsSame=0
    numGroupsUsed=0
    numImagesUsed=0
    maxPairDist=0
    maxPairDistX=0
    maxPairDistY=0
    for groupName in sorted(groupNames):
        if groupName=='121':
            continue
        files = imageGroups[groupName]
        usedGroup=False
        imageFiles=[]
        for f in files:
            if 'lock' not in f:
                if 'template' not in f and f[-5:]=='.json':
                    if not usedGroup:
                        numGroupsUsed+=1
                        usedGroup=True
                    numImagesUsed+=1
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    if mimic_dataset:
                        fixAnnotations(mimic_object,read)
                        countTotal = len(read['byId'])
                        bbs = read['byId'].values()
                    else:
                        sumCountField = len(read['fieldBBs'])
                        sumCountText = len(read['textBBs'])
                        countTotal = sumCountField + sumCountText
                        bbs = read['fieldBBs']+read['textBBs']
                    sumCountTotal+=countTotal
                    count+=1
                    maxBoxes = max(maxBoxes,countTotal)
                    page_heights.append(read['height'])
                    page_widths.append(read['width'])
                    page_areas.append(read['height']*read['width'])
                    numBBs.append(countTotal)
                    byId={}
                    nn=defaultdict(lambda:0)
                    for bb in bbs:
                        byId[bb['id']]=bb
                        nn[bb['id']]=0
                        if bb['type']=='fieldRow' or bb['type']=='fieldCol' or bb['type']=='fieldRegion' or bb['type']=='textRegion' or bb['type']=='graphic':
                            if bb['type']=='graphic':
                                print('has graphic: {}/{}'.format(groupName,f))
                            continue
                        if  bb['type'][:4]=='text':
                            totalText+=1
                        else:
                            totalField+=1
                        #elif !='fieldCheckBox':

                        tlX = bb['poly_points'][0][0]
                        tlY = bb['poly_points'][0][1]
                        trX = bb['poly_points'][1][0]
                        trY = bb['poly_points'][1][1]
                        brX = bb['poly_points'][2][0]
                        brY = bb['poly_points'][2][1]
                        blX = bb['poly_points'][3][0]
                        blY = bb['poly_points'][3][1]
                        lX = (tlX+blX)/2.0
                        lY = (tlY+blY)/2.0
                        rX = (trX+brX)/2.0
                        rY = (trY+brY)/2.0
                        height =  math.sqrt( ((blX+brX)/2.0 - (tlX+trX)/2.0)**2 + ((blY+brY)/2.0 - (tlY+trY)/2.0)**2 )
                        if height>300:
                            print '{} {}'.format(groupName,f)
                            print bb
                            continue
                        widths.append( math.sqrt( (rX - lX)**2 + (rY - lY)**2 ) )
                        heights.append( height)
                        ratios.append(widths[-1]/heights[-1])
                        rot=np.arctan2((rY-lY),rX-lX)
                        if rot<0:
                            rot+=2*math.pi
                        rots.append(rot)

                        widths_norot.append( np.maximum.reduce((tlX,blX,trX,brX))-np.minimum.reduce((tlX,blX,trX,brX)) )
                        heights_norot.append( np.maximum.reduce((tlY,blY,trY,brY))-np.minimum.reduce((tlY,blY,trY,brY)) )
                        ratios_norot.append(widths_norot[-1]/heights_norot[-1])
                    nn_init=nn.copy()
                    totalRelationships+=len(read['pairs'])
                    for id1,id2 in read['pairs']:
                        bb1=byId[id1]
                        bb2=byId[id2]
                        isText1=bb1['type'][0:4]=='text'
                        isText2=bb2['type'][0:4]=='text'
                        nn[id1]+=1
                        nn[id2]+=1

                        bb1X=(bb1['poly_points'][0][0]+bb1['poly_points'][1][0]+bb1['poly_points'][2][0]+bb1['poly_points'][3][0])/4
                        bb1Y=(bb1['poly_points'][0][1]+bb1['poly_points'][1][1]+bb1['poly_points'][2][1]+bb1['poly_points'][3][1])/4
                        bb2X=(bb2['poly_points'][0][0]+bb2['poly_points'][1][0]+bb2['poly_points'][2][0]+bb2['poly_points'][3][0])/4
                        bb2Y=(bb2['poly_points'][0][1]+bb2['poly_points'][1][1]+bb2['poly_points'][2][1]+bb2['poly_points'][3][1])/4

                        neighborXDiff[isText2].append(bb1X-bb2X)
                        neighborXDiff[isText1].append(bb2X-bb1X)
                        neighborYDiff[isText2].append(bb1Y-bb2Y)
                        neighborYDiff[isText1].append(bb2Y-bb1Y)
                        maxPairDist = max(maxPairDist,math.sqrt((bb1X-bb2X)**2 + (bb1Y-bb2Y)**2))
                        maxPairDistX = max(maxPairDistX,abs(bb1X-bb2X))
                        maxPairDistY = max(maxPairDistY,abs(bb1Y-bb2Y))
                    for id,countNN in nn.items():
                        isText=byId[id]['type'][0:4]=='text'
                        numNeighbors[isText].append(countNN)
                        countNN = min(countNN,9)
                        numNeighborsHist[countNN]+=1
                        #if countNN>1:
                        #    print('{} {} : nn {}'.format(groupName,f,countNN))
                    nn=nn_init
                    if 'samePairs' in read:
                        totalRelationshipsSame+=len(read['samePairs'])
                        for id1,id2 in read['samePairs']:
                            bb1=byId[id1]
                            bb2=byId[id2]
                            isText1=bb1['type'][0:4]=='text'
                            isText2=bb2['type'][0:4]=='text'
                            nn[id1]+=1
                            nn[id2]+=1

                            bb1X=(bb1['poly_points'][0][0]+bb1['poly_points'][1][0]+bb1['poly_points'][2][0]+bb1['poly_points'][3][0])/4
                            bb1Y=(bb1['poly_points'][0][1]+bb1['poly_points'][1][1]+bb1['poly_points'][2][1]+bb1['poly_points'][3][1])/4
                            bb2X=(bb2['poly_points'][0][0]+bb2['poly_points'][1][0]+bb2['poly_points'][2][0]+bb2['poly_points'][3][0])/4
                            bb2Y=(bb2['poly_points'][0][1]+bb2['poly_points'][1][1]+bb2['poly_points'][2][1]+bb2['poly_points'][3][1])/4

                            neighborXDiff_same[isText1].append(bb1X-bb2X)
                            neighborXDiff_same[isText2].append(bb2X-bb1X)
                            neighborYDiff_same[isText1].append(bb1Y-bb2Y)
                            neighborYDiff_same[isText2].append(bb2Y-bb1Y)
                            maxPairDist = max(maxPairDist,math.sqrt((bb1X-bb2X)**2 + (bb1Y-bb2Y)**2))
                            maxPairDistX = max(maxPairDistX,abs(bb1X-bb2X))
                            maxPairDistY = max(maxPairDistY,abs(bb1Y-bb2Y))
                    for id,countNN in nn.items():
                        isText=byId[id]['type'][0:4]=='text'
                        numNeighbors_same[isText].append(countNN)
                        countNN = min(countNN,9)
                        numNeighborsHist[countNN]+=1

    print('Number of images: {}'.format(numImagesUsed))
    print('Number of groups: {}'.format(numGroupsUsed))
    print('Number of text lines: {}'.format(totalText))
    print('Number of field lines: {}'.format(totalField))
    print('Number of relationships diff: {}'.format(totalRelationships))
    print('Number of relationships same: {}'.format(totalRelationshipsSame))

    print('\nMax pair dist: {}'.format(maxPairDist))
    print('\nMax pair distX: {}'.format(maxPairDistX))
    print('\nMax pair distY: {}'.format(maxPairDistY))

    print('\nNum Neighbor stuff:')
    print('NN hist {}'.format(numNeighborsHist))
    print('text num neighbors mean: {}, std: {}'.format(np.mean(numNeighbors[1]),np.std(numNeighbors[1])))
    print('text neighbor X diff mean: {}, std: {}'.format(np.mean(neighborXDiff[1]),np.std(neighborXDiff[1])))
    print('text neighbor Y diff mean: {}, std: {}'.format(np.mean(neighborYDiff[1]),np.std(neighborYDiff[1])))
    print('field num neighbors mean: {}, std: {}'.format(np.mean(numNeighbors[0]),np.std(numNeighbors[0])))
    print('field neighbor X diff mean: {}, std: {}'.format(np.mean(neighborXDiff[0]),np.std(neighborXDiff[0])))
    print('field neighbor Y diff mean: {}, std: {}'.format(np.mean(neighborYDiff[0]),np.std(neighborYDiff[0])))
    print('SAME text num neighbors mean: {}, std: {}'.format(np.mean(numNeighbors[1]),np.std(numNeighbors[1])))
    print('SAME text neighbor X diff mean: {}, std: {}'.format(np.mean(neighborXDiff_same[1]),np.std(neighborXDiff_same[1])))
    print('SAME text neighbor Y diff mean: {}, std: {}'.format(np.mean(neighborYDiff_same[1]),np.std(neighborYDiff_same[1])))
    print('SAME field num neighbors mean: {}, std: {}'.format(np.mean(numNeighbors[0]),np.std(numNeighbors[0])))
    print('SAME field neighbor X diff mean: {}, std: {}'.format(np.mean(neighborXDiff_same[0]),np.std(neighborXDiff_same[0])))
    print('SAME field neighbor Y diff mean: {}, std: {}'.format(np.mean(neighborYDiff_same[0]),np.std(neighborYDiff_same[0])))


    print('\nOld Stats:')
    print('BB count mean:{}, max: {}'.format(np.mean(numBBs),np.max(numBBs)))
    print('image mean height: {}, width: {}, area: {}'.format(np.mean(page_heights),np.mean(page_widths),np.mean(page_areas)))
    print('image std height: {}, width: {}, area: {}'.format(np.std(page_heights),np.std(page_widths),np.std(page_areas)))
    print('image max height: {}, width: {}, area: {}'.format(max(page_heights),max(page_widths),max(page_areas)))
    print('image min height: {}, width: {}, area: {}'.format(min(page_heights),min(page_widths),min(page_areas)))
    print 'avg boxes: {}'.format((sumCountTotal)/float(count))
    print 'max boxes: {}'.format(maxBoxes)
    print 'With rotation'
    print 'width mean: {}, std: {}'.format(np.mean(widths),np.std(widths))
    print 'width min: {}, max: {}'.format(min(widths),max(widths))
    print 'height mean: {}, std: {}'.format(np.mean(heights),np.std(heights))
    print 'height min: {}, max: {}'.format(min(heights),max(heights))
    print 'ratio mean: {}, std: {}'.format(np.mean(ratios),np.std(ratios))
    print 'rot mean: {}, std: {}'.format(np.mean(rots),np.std(rots))
    print 'No rotation'
    print 'width mean: {}, std: {}'.format(np.mean(widths_norot),np.std(widths_norot))
    print 'width min: {}, max: {}'.format(min(widths_norot),max(widths_norot))
    print 'height mean: {}, std: {}'.format(np.mean(heights_norot),np.std(heights_norot))
    print 'height min: {}, max: {}'.format(min(heights_norot),max(heights_norot))
    print 'ratio mean: {}, std: {}'.format(np.mean(ratios_norot),np.std(ratios_norot))

    import matplotlib.pyplot as plt
    from matplotlib.ticker import NullFormatter
    #x=np.array(widths)#[:200]
    #y=np.array(heights)#[:200]
    if False:
        x=np.array(ratios)#[:200]
        y=np.array(rots)#[:200]
        nullfmt = NullFormatter()         # no labels

        # definitions for the axes
        left, width = 0.1, 0.65
        bottom, height = 0.1, 0.65
        bottom_h = left_h = left + width + 0.02

        rect_scatter = [left, bottom, width, height]
        rect_histx = [left, bottom_h, width, 0.2]
        rect_histy = [left_h, bottom, 0.2, height]
        # start with a rectangular Figure
        plt.figure(1, figsize=(12,12))

        axScatter = plt.axes(rect_scatter)
        axHistx = plt.axes(rect_histx)
        axHisty = plt.axes(rect_histy)

        # no labels
        axHistx.xaxis.set_major_formatter(nullfmt)
        axHisty.yaxis.set_major_formatter(nullfmt)

        # the scatter plot:
        axScatter.scatter(x, y)

        # now determine nice limits by hand:
        binwidthX = 3
        binwidthY = math.pi/30
        xmax = x.max()
        ymax = y.max()
        limX = (int(xmax/binwidthX) + 1) * binwidthX
        limY = (int(ymax/binwidthY) + 1) * binwidthY

        axScatter.set_xlim((0, limX))
        axScatter.set_ylim((0, limY))

        binsX = np.arange(0, limX + binwidthX, binwidthX)
        binsY = np.arange(0, limY + binwidthY, binwidthY)
        axHistx.hist(x, bins=binsX)
        axHisty.hist(y, bins=binsY, orientation='horizontal')

        axHistx.set_xlim(axScatter.get_xlim())
        axHisty.set_ylim(axScatter.get_ylim())
        plt.show()
    def showScatter(data1,data2,binwidthX,binwidthY):
        x=np.array(data1)#[:200]
        y=np.array(data2)#[:200]
        nullfmt = NullFormatter()         # no labels

        # definitions for the axes
        left, width = 0.1, 0.65
        bottom, height = 0.1, 0.65
        bottom_h = left_h = left + width + 0.02

        rect_scatter = [left, bottom, width, height]
        rect_histx = [left, bottom_h, width, 0.2]
        rect_histy = [left_h, bottom, 0.2, height]
        # start with a rectangular Figure
        plt.figure(1, figsize=(12,12))

        axScatter = plt.axes(rect_scatter)
        axHistx = plt.axes(rect_histx)
        axHisty = plt.axes(rect_histy)

        # no labels
        axHistx.xaxis.set_major_formatter(nullfmt)
        axHisty.yaxis.set_major_formatter(nullfmt)

        # the scatter plot:
        axScatter.scatter(x, y)

        # now determine nice limits by hand:
        #binwidthX = 30
        #binwidthY = 15
        xmax = x.max()
        ymax = y.max()
        limX = (int(xmax/binwidthX) + 1) * binwidthX
        limY = (int(ymax/binwidthY) + 1) * binwidthY
        xmin = x.min()
        ymin = y.min()
        startX = (int(xmin/binwidthX)) * binwidthX
        startY = (int(ymin/binwidthY)) * binwidthY

        axScatter.set_xlim((startX, limX))
        axScatter.set_ylim((startY, limY))

        binsX = np.arange(startX, limX + binwidthX, binwidthX)
        binsY = np.arange(startY, limY + binwidthY, binwidthY)
        axHistx.hist(x, bins=binsX)
        axHisty.hist(y, bins=binsY, orientation='horizontal')

        axHistx.set_xlim(axScatter.get_xlim())
        axHisty.set_ylim(axScatter.get_ylim())
        plt.show()
    showScatter(neighborXDiff[1],neighborYDiff[1],30,15)
    showScatter(numNeighbors[1],len(numNeighbors[1])*[0],0.5,1)


if makesplit:
    groupImages={}#defaultdict(list)
    groupCount={}
    totalJson=0
    groupTablePresence={}
    groupParaPresence={}
    paraThresh=2
    jsons=set()
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imageFiles=[]
        tempFound=False
        hasTable=False
        isPara=False
        paraCount=0
        jsonCount=0
        for f in files:
            if 'lock' not in f:
                if f[-4:]=='.jpg' or f[-5:]=='.jpeg' or f[-4:]=='.png':
                    imageFiles.append(f)
                elif 'template' in f and f[-5:]=='.json':
                    paraCount=0
                    tempFound=True
                    validTemp=False
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    for bb in read['fieldBBs']:
                        if bb['type']=='fieldCol' or bb['type']=='fieldRow':
                            hasTable=True
                            if isPara:
                                break
                        if bb['type']=='fieldP':
                            paraCount+=1
                            if paraCount>paraThresh:
                                isPara=True
                                if hasTable:
                                    break
                    #for bb in read['textBBs']:
                    #    if bb['type']=='textP':
                    #        paraCount+=1
                    #        if paraCount>4:
                    #            isPara=True
                    #            if hasTable:
                    #                break
                elif f[-5:]=='.json' and 'temp' not in f:
                    jsonCount+=1
                    jsons.add(f[:-5])
                    totalJson+=1
                    if not isPara:
                        with open(os.path.join(directory,groupName,f)) as annFile:
                            read = json.loads(annFile.read())
                        for bb in read['fieldBBs']:
                            if bb['type']=='fieldP':
                                paraCount+=1
                                if paraCount>paraThresh:
                                    isPara=True
                                    break

        groupImages[groupName]=imageFiles
        groupCount[groupName]=jsonCount
        groupTablePresence[groupName]=hasTable
        groupParaPresence[groupName]=isPara
        #print('group {}, table:{}, para:{} {}'.format(groupName,hasTable,isPara,'?? para' if paraCount>0 and not isPara else ''))
    


    groupsWithTable=[]
    groupsWithPara=[]
    groupsWithout=[]
    both=0
    for groupName in sorted(groupNames):
        if groupName in groupImages:
            if groupParaPresence[groupName] and  groupTablePresence[groupName]:
                both+=1
                if random.random()>0.5:
                    groupsWithTable.append(groupName)
                else:
                    groupsWithPara.append(groupName)
            elif groupParaPresence[groupName]:
                groupsWithPara.append(groupName)
            elif groupTablePresence[groupName]:
                groupsWithTable.append(groupName)
            else:
                groupsWithout.append(groupName)
            #print groupName
            #print '  {}'.format(len(groupImages[groupName]))
            #print '  {}'.format(groupTablePresence[groupName])
    print('Without: {}, table: {}, para: {}, (both:{})'.format(len(groupsWithout),len(groupsWithTable),len(groupsWithPara),both))

    if mixsplit:
        imagesGT=[]
        imagesNo=[]
        for groupName in groupsWithout:
            for f in groupImages[groupName]:
                name = f[:f.rfind('.')]
                if name in jsons:
                    imagesGT.append((groupName,f))
                else:
                    imagesNo.append((groupName,f))
            #images += [(groupName,f) for f in groupImages[groupName]]
        split = int(0.1*len(imagesGT))
        testImages = imagesGT[:split]
        validImages = imagesGT[split:2*split]
        trainImages = imagesGT[2*split:]
        split = int(0.1*len(imagesNo))
        testImages += imagesNo[:split]
        validImages += imagesNo[split:2*split]
        trainImages += imagesNo[2*split:]
        ret={'train':defaultdict(list), 'valid':defaultdict(list), 'test':defaultdict(list)}
        #if simpleDataset:
        for groupName,f in validImages:
            ret['valid'][groupName].append(f)
        for groupName,f in testImages:
            ret['test'][groupName].append(f)
        for groupName,f in trainImages:
            ret['train'][groupName].append(f)
        fileName='mix_train_valid_test_split.json'
        print('mix train: {}, valid: {}, test: {}'.format(len(ret['train']), len(ret['valid']), len(ret['test'])))
        print('mix train: {}, valid: {}, test: {}'.format(len(trainImages), len(validImages), len(testImages)))
        with open(fileName, 'w') as out:
            out.write(json.dumps(ret,indent=4, sort_keys=True))
    else:
        def split(groups,groupsCount): #prevents colliding groups of slightly different type
            total=0
            for name in groups:
                total+=groupCount[name]
            numSub = 0.07*total

            metagroups=defaultdict(list)
            metagroupsCount=defaultdict(lambda:0)
            for g in groups:
                if '_' in g:
                    mg = g[g.find('_')]
                else:
                    mg =g
                metagroups[mg].append(g)
                metagroupsCount[mg] += groupsCount[g]


            counts = [(name,metagroupsCount[name]) for name in metagroups]
            shuffle(counts)
            counts.sort(key=lambda x: x[1])

            test=[]
            testCount=0
            valid=[]
            validCount=0
            train=[]
            trainCount=0

            mI=0
            while testCount<numSub or validCount<numSub:
                probTrain = 0.33#+0.75*(float(mI)/len(metagroups))
                if random.random()<probTrain:
                   train += metagroups[counts[mI][0]]
                   trainCount += metagroupsCount[counts[mI][0]]
                else:
                    toValid = random.random()<0.5
                    if testCount>=numSub or toValid:
                        valid += metagroups[counts[mI][0]]
                        validCount += metagroupsCount[counts[mI][0]]
                    else:
                        test += metagroups[counts[mI][0]]
                        testCount += metagroupsCount[counts[mI][0]]
                mI+=1
            for i in range(mI,len(metagroups)):
                train += metagroups[counts[i][0]]
                trainCount += metagroupsCount[counts[i][0]]

            return train, trainCount, valid, validCount, test, testCount
        
        trainTable, trainCountTable, validTable, validCountTable, testTable, testCountTable = split(groupsWithTable,groupCount)
        trainPara, trainCountPara, validPara, validCountPara, testPara, testCountPara = split(groupsWithPara,groupCount)
        trainWithout, trainCountWithout, validWithout, validCountWithout, testWithout, testCountWithout = split(groupsWithout,groupCount)

        print('trainCountTable:{},\tvalidCountTable:{}\ttestCountTable:{}'.format(trainCountTable,validCountTable,testCountTable))
        print('trainCountPara:{},\tvalidCountPara:{}\ttestCountPara:{}'.format(trainCountPara,validCountPara,testCountPara))
        print('trainCountWithout:{},\tvalidCountWithout:{}\ttestCountWithout:{}'.format(trainCountWithout,validCountWithout,testCountWithout))
        trainCountTotal = trainCountTable+trainCountPara+trainCountWithout
        validCountTotal = validCountTable+validCountPara+validCountWithout
        testCountTotal = testCountTable+testCountPara+testCountWithout
        print('trainCountTotal:{},\tvalidCountTotal:{}\ttestCountTotal:{}'.format(trainCountTotal,validCountTotal,testCountTotal))


        ret={'train':{}, 'valid':{}, 'test':{}}
        #if simpleDataset:
        for groupName in validWithout:
            ret['valid'][groupName]=groupImages[groupName]
        for groupName in testWithout:
            ret['test'][groupName]=groupImages[groupName]
        for groupName in trainWithout:
            ret['train'][groupName]=groupImages[groupName]
        fileName='simple_train_valid_test_split.json'
        print('simple train: {}, valid: {}, test: {}'.format(len(ret['train']), len(ret['valid']), len(ret['test'])))
        with open(fileName, 'w') as out:
            out.write(json.dumps(ret,indent=4, sort_keys=True))
        #else:



        ret={'train':{}, 'valid':{}, 'test':{}}
        for groupName in validWithout+validTable+validPara:
            ret['valid'][groupName]=groupImages[groupName]
        for groupName in testWithout+testTable+testPara:
            ret['test'][groupName]=groupImages[groupName]
        for groupName in trainWithout+trainTable+trainPara:
            ret['train'][groupName]=groupImages[groupName]
        fileName='train_valid_test_split.json'
        print('train: {}, valid: {}, test: {}'.format(len(ret['train']), len(ret['valid']), len(ret['test'])))
        with open(fileName, 'w') as out:
            out.write(json.dumps(ret,indent=4, sort_keys=True))

if saveall:
    with open('all.json','w') as out:
        out.write(json.dumps(imageGroups,indent=4, sort_keys=True))
