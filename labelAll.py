from labeler import labelImage
from filelock import FileLock, FileLockException
import os
import sys
import json
import signal
import timeit
import grp
#import Tkinter
#import tkMessageBox

NUM_PER_GROUP=2
lock=None
#groupId = grp.getgrnam("pairing").gr_gid

def exitGracefully(sig, frame):
    global lock
    if lock is not None:
        lock.release()
        exit()
signal.signal(signal.SIGINT, exitGracefully)

def combineFields(gtFields,tempFields):
    toRemove=[]
    maxId=0
    for i in range(len(tempFields)):
        if tempFields[i]['type']=='fieldCol' or tempFields[i]['type']=='fieldRow':
            toRemove.append(i)
        else:
            maxId = max(maxId,int(tempFields[i]['id'][1:]))
    toRemove.sort(reverse=True)
    for i in toRemove:
        del tempFields[i]
    newId=maxId
    for bb in gtFields:
        bb['id']='f'+str(newId)
        newId+=1
    print('combining {} and {}'.format(len(gtFields),len(tempFields)))
    return gtFields+tempFields

if len(sys.argv)<2:
    print 'usage: '+sys.argv[0]+' directory [startingGroup] [startingImage] [n(dont load horz links)]/[t (add template, skipping tables)]'
    exit()

directory = sys.argv[1]
progressOnly=False
addOnly=False
if len(sys.argv)>2:
    if sys.argv[2][0]=='-':
        progressOnly=True
    elif sys.argv[2][0]=='+':
        addOnly=True
    else:
        startHere = sys.argv[2]
        going=False
else:
    startHere=None
    going=True
if len(sys.argv)>3:
    startHereImage = sys.argv[3]
    goingImage=False
else:
    startHereImage=None
    goingImage=True

skipHLinks=False
applyTemplate=False
if len(sys.argv)>4:
    if sys.argv[4][0]=='n':
        skipHLinks=True
    elif sys.argv[4][0]=='t':
        applyTemplate=True

if directory[-1]!='/':
    directory=directory+'/'
rr=directory[directory[:-1].rindex('/')+1:-1]
imageGroups={}
groupNames=[]
for root, dirs, files in os.walk(directory):
    #print 'root: '+root
    if root[-1]=='/':
        root=root[:-1]
    groupName = root[root.rindex('/')+1:]
    if rr==groupName:
        continue
    imageGroups[groupName]=sorted(files)
    groupNames.append(groupName)

if progressOnly:
    numTemplateDone=0
    numDoneTotal=0
    numTotal=0
    numTimed=0
    timeTotal=0
    numTempTimed=0
    timeTemp=0
    if len(sys.argv[2])>1:
        doTime=True
    else:
        doTime=False
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        imagesInGroup=0
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
                                timeTemp+=read['labelTime']
                elif f[-5:]=='.json':
                    numDoneTotal+=1
                    if doTime:
                        with open(os.path.join(directory,groupName,f)) as annFile:
                            read = json.loads(annFile.read())
                            if 'labelTime' in read and read['labelTime'] is not None:
                                numTimed+=1
                                timeTotal+=read['labelTime']

        numTotal += min(imagesInGroup,NUM_PER_GROUP)
    print('Templates: {}/{}  {}'.format(numTemplateDone,len(groupNames),float(numTemplateDone)/len(groupNames)))
    print('Images:    {}/{}  {}'.format(numDoneTotal,numTotal,float(numDoneTotal)/numTotal))
    if doTime:
        timeTotal/=numTimed
        timeTemp/=numTempTimed
        print (' Templates take {} secs, or {} minutes   ({} samples)'.format(timeTemp,timeTemp/60,numTempTimed))
        print ('Alignment takes {} secs, or {} minutes   ({} samples)'.format(timeTotal,timeTotal/60,numTimed))
    exit()
elif addOnly:
    import matplotlib.image as mpimg
    count=0
    for groupName in sorted(groupNames):
        files = imageGroups[groupName]
        for f in files:
            if f[-5:]=='.json' and 'templa' not in f:
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
    exit()
groupIndex=-1
groupsDone=[False]*len(groupNames)
for groupName in sorted(groupNames):
    groupIndex+=1
    files = imageGroups[groupName]
    if not going:
        if startHere==groupName:
            going=True
        else:
            continue
    template = None
    numImages=0
    numDone=0
    for f in files:
        if 'template' in f and f[-5:]=='.json':
            template = os.path.join(directory,groupName,f)
        elif f[-4:]=='.jpg':
            numImages+=1
        elif f[-5:]=='.json':
            numDone+=1
    numImages = min(numImages,NUM_PER_GROUP)
    if numDone>=numImages:
        groupsDone[groupIndex]=True
        #continue

    #print 'group '+groupName+', template image: '+imageTemplate                   
    #templateFile=os.path.join(directory,groupName,template)
    lock = FileLock(template, timeout=None)
    try:
        lock.acquire()
        textsT=fieldsT=pairsT=samePairsT=horzLinksT=groupsT=cornersT=cornersActualT=None
        if template is not None:
            with open(template) as f:
                read = json.loads(f.read())
                textsT=read['textBBs']
                fieldsT=read['fieldBBs']
                pairsT=read['pairs']
                samePairsT=read['samePairs']
                groupsT=read['groups']
                cornersT=read['page_corners']
                if 'horzLinks' in read  and not skipHLinks:
                    horzLinksT=read['horzLinks']
                #cornersActualT=read['actualPage_corners']
                imageTemplate=read['imageFilename']
        else:
            template = os.path.join(directory,groupName,'template'+groupName+'.json')
            #tkMessageBox.showinfo("Template", "A template doesn't exist for group "+groupName+", creating one")
            print '!!!!!!!!!!!!!!!!!!!!!!!!!'
            print "A template doesn't exist for group "+groupName+", creating one"
            timeStart = timeit.default_timer()
            textsT,fieldsT,pairsT,samePairsT,horzLinksT,groupsT,cornersT, actualCornersT, complete, height, width = labelImage(os.path.join(directory,groupName,files[0]),textsT,fieldsT,pairsT,samePairsT,horzLinksT,groupsT,None,cornersT,cornersActualT)
            timeElapsed = timeit.default_timer()-timeStart
            if (len(textsT)==0 and len(fieldsT)==0):
                lock.release()
                lock=None
                exit()
            else:
                if not complete:
                     template+='.nf'
                with open(template,'w') as out:
                    out.write(json.dumps({"textBBs":textsT, "fieldBBs":fieldsT, "pairs":pairsT, "samePairs":samePairsT, "horzLinks":horzLinksT, "groups":groupsT, "page_corners":cornersT, "imageFilename":files[0], "labelTime":timeElapsed, "height":height, "width":width}))
                if not complete:
                    lock.release()
                    lock=None
                    exit()

        countInGroup=0
        for f in files:
            ind = f.rfind('.')
            if f[ind:]=='.jpg' or f[ind:]=='.png' or f[ind:]=='.jpeg':
                countInGroup+=1
                if countInGroup>NUM_PER_GROUP:
                    break
                if not goingImage:
                    if f==startHereImage:
                        goingImage=True
                    else:
                        continue
                name=f[:ind]
                gtFileName = os.path.join(directory,groupName,name+'.json')
                gtFileNameExists = os.path.exists(gtFileName)
                if gtFileNameExists and startHereImage is None:
                    continue
                nfGtFileNameExists = os.path.exists(gtFileName+'.nf')
                
                texts=fields=pairs=samePairs=horzLinks=groups=page_corners=page_cornersActual=None
                if f == imageTemplate:
                    page_corners=page_cornersActual=cornersT
                if gtFileNameExists or nfGtFileNameExists:
                    if gtFileNameExists:
                        gtF = open(gtFileName)
                    elif nfGtFileNameExists:
                        gtF = open(gtFileName+'.nf')
                    read = json.loads(gtF.read())
                    texts=read['textBBs']
                    fields=read['fieldBBs']
                    pairs=read['pairs']
                    samePairs=read['samePairs']
                    groups=read['groups']
                    if 'horzLinks' in read and not skipHLinks:
                        horzLinks=read['horzLinks']
                    if 'page_corners' in read and 'actualPage_corners' in read:
                        page_corners=read['page_corners']
                        page_cornersActual=read['actualPage_corners']
                    if 'labelTime' in read:
                        labelTime = read['labelTime']
                    else:
                        labelTime = None
                    assert f==read['imageFilename']
                    print 'g:'+groupName+', image: '+f+', gt found'
                    if applyTemplate:
                        texts+=textsT
                        fields = combineFields(fields,fieldsT)
                        pairs=pairsT
                        samePairs=samePairsT
                        groups=groupsT
                        horzLinks=horzLinksT
                    if labelTime is not None:
                        timeStart = timeit.default_timer()
                    texts,fields,pairs,samePairs,horzLinks,groups,corners,actualCorners,complete,height,width = labelImage(os.path.join(directory,groupName,f),texts,fields,pairs,samePairs,horzLinks,groups,None,page_corners,page_cornersActual)
                    if labelTime is not None:
                        labelTime += timeit.default_timer()-timeStart
                    gtF.close()
                else:
                    print 'g:'+groupName+', image: '+f+', from template'
                    timeStart = timeit.default_timer()
                    texts,fields,pairs,samePairs,horzLinks,groups,corners,actualCorners,complete,height,width = labelImage(os.path.join(directory,groupName,f),textsT,fieldsT,pairsT,samePairsT,horzLinksT,groupsT,cornersT,page_corners,page_cornersActual)
                    labelTime = timeit.default_timer()-timeStart

                if len(texts)==0 and len(fields)==0:
                    lock.release()
                    lock=None
                    exit()
                if not complete:
                    gtFileName+='.nf'
                with open(gtFileName,'w') as out:
                    out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "horzLinks":horzLinks, "groups":groups, "page_corners":corners, "actualPage_corners":actualCorners, "imageFilename":f, "labelTime": labelTime, "height":height, "width":width}))
                    if complete and (startHere is None or startHere!=groupName):
                        if countInGroup==numImages:
                            groupsDone[groupIndex]=True
                            print groupName+' progress:['+('X'*numImages)+'] COMPLETE!'
                            print 'Overall group progress:['+''.join(['X' if x else '.' for x in groupsDone])+']'
                        else:
                            print groupName+' progress:['+('X'*countInGroup)+('.'*(numImages-countInGroup))+']'
                skipHLinks=False
                #os.chown(gtFileName,-1,groupId)
                if not complete:
                    lock.release()
                    lock=None
                    exit()
                elif nfGtFileNameExists:
                    os.remove(gtFileName+'.nf')
        lock.release()
        lock=None
    except FileLockException as e:
        print 'template locked for group '+groupName+', moving to next group'
        lock=None
        continue
