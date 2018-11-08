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
NUM_CHECKS=2
USE_SIMPLE=True
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
    print 'usage: '+sys.argv[0]+' directory [startingGroup] [startingImage] [n(dont load horz links)]/[t (add template, skipping tables)] [C:checking]'
    exit()

directory = sys.argv[1]
progressOnly=False
addOnly=False
checking=False
if sys.argv[-1][0]=='C':
    checking=True
    myName=sys.argv[-1][1:]
    if len(myName)==0:
        myName=raw_input("Enter name: ")
    print 'CHECKING '+myName
if len(sys.argv)>2:
    if sys.argv[2][0]=='-':
        progressOnly=True
    elif sys.argv[2][0]=='+':
        addOnly=True
    elif  sys.argv[2][0]=='C':
        going=True
        startHere=None
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

if USE_SIMPLE:
    with open(os.path.join(directory,'simple_train_valid_test_split.json')) as f:
        simpleSplit = json.load(f)
    simpleFiles = dict(simpleSplit['train'].items()+ simpleSplit['test'].items()+ simpleSplit['valid'].items())
    #print(simpleFiles)

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
    if not USE_SIMPLE or groupName in simpleFiles:
        imageGroups[groupName]=sorted(files)
        groupNames.append(groupName)

if progressOnly or addOnly:
    print 'removed, use scandata.py'
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
    templateNF = None
    numImages=0
    numDone=0
    unfinished=[]
    for f in files:
        if 'template' in f and f[-5:]=='.json':
            template = os.path.join(directory,groupName,f)
        elif 'template' in f and f[-8:]=='.json.nf':
            templateNF = os.path.join(directory,groupName,f)
        elif f[-4:]=='.jpg':
            if not checking:
                numImages+=1
        elif f[-5:]=='.json':
            numDone+=1
            if checking:
                numImages+=1
        elif f[-8:]=='.json.nf':
            unfinished.append(f[0:-8]+'.jpg')
    if not checking:
        numImages = min(numImages,NUM_PER_GROUP)
    if numDone>=numImages:
        groupsDone[groupIndex]=True
        if startHere is None and not checking:
            #import pdb; pdb.set_trace()
            continue

    #print 'group '+groupName+', template image: '+imageTemplate                   
    #templateFile=os.path.join(directory,groupName,template)
    lock = FileLock(template, timeout=None)
    try:
        lock.acquire()
        textsT=fieldsT=pairsT=samePairsT=horzLinksT=groupsT=cornersT=cornersActualT=None
        if template is not None:
            with open(template) as f:
                read = json.loads(f)
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
            if checking:
                continue
            print '!!!!!!!!!!!!!!!!!!!!!!!!!'
            labelTime = None
            if templateNF is not None:
                with open(templateNF) as f:
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
                    if 'labelTime' in read:
                        labelTime = read['labelTime']
                print "There is an incomplete template for group "+groupName+", editing it"
            else:
                print "A template doesn't exist for group "+groupName+", creating one"
                imageTemplate=files[0]
            print '!!!!!!!!!!!!!!!!!!!!!!!!!'
            template = os.path.join(directory,groupName,'template'+groupName+'.json')
            #tkMessageBox.showinfo("Template", "A template doesn't exist for group "+groupName+", creating one")
            timeStart = timeit.default_timer()
            textsT,fieldsT,pairsT,samePairsT,horzLinksT,groupsT,cornersT, actualCornersT, complete, height, width = labelImage(os.path.join(directory,groupName,imageTemplate),textsT,fieldsT,pairsT,samePairsT,horzLinksT,groupsT,None,cornersT,cornersActualT)
            timeElapsed = timeit.default_timer()-timeStart + (labelTime if labelTime is not None else 0)
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
        
        for f in unfinished+files:
            ind = f.rfind('.')
            if f[ind:]=='.jpg' or f[ind:]=='.png' or f[ind:]=='.jpeg':
                countInGroup+=1
                if countInGroup>NUM_PER_GROUP and (startHereImage is None or goingImage) and not checking:
                    break
                if not goingImage:
                    if f==startHereImage:
                        goingImage=True
                    else:
                        continue
                name=f[:ind]
                gtFileName = os.path.join(directory,groupName,name+'.json')
                gtFileNameExists = os.path.exists(gtFileName)
                if gtFileNameExists and startHereImage is None and not checking:
                    continue
                nfGtFileNameExists = os.path.exists(gtFileName+'.nf')
                checkedBy = []
                
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
                    if 'checkedBy' in read:
                        checkedBy = read['checkedBy']
                    
                    if checking and (len(checkedBy)>=NUM_CHECKS or myName in checkedBy):
                        continue
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
                    if complete and checking:
                        checkedBy.append(myName)
                else:
                    if checking:
                        continue
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
                    out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "horzLinks":horzLinks, "groups":groups, "page_corners":corners, "actualPage_corners":actualCorners, "imageFilename":f, "labelTime": labelTime, "height":height, "width":width, "checkedBy":checkedBy}))
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
