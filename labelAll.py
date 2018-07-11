from labeler import labelImage
from filelock import FileLock, FileLockException
import os
import sys
import json
#import Tkinter
#import tkMessageBox

NUM_PER_GROUP=10

if len(sys.argv)<2:
    print 'usage: '+sys.argv[0]+' directory (startingGroup) (startingImage)'
    exit()

directory = sys.argv[1]
if len(sys.argv)>2:
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


for groupName in sorted(groupNames):
    files = imageGroups[groupName]
    if not going:
        if startHere==groupName:
            going=True
        else:
            continue
    template = None
    for f in files:
        if 'template' in f and f[-5:]=='.json':
            template = os.path.join(directory,groupName,f)


    #print 'group '+groupName+', template image: '+imageTemplate                   
    #templateFile=os.path.join(directory,groupName,template)
    lock = FileLock(template, timeout=None)
    try:
        lock.acquire()
        textsT=fieldsT=pairsT=samePairsT=groupsT=cornersT=cornersActualT=None
        if template is not None:
            with open(template) as f:
                read = json.loads(f.read())
                textsT=read['textBBs']
                fieldsT=read['fieldBBs']
                pairsT=read['pairs']
                samePairsT=read['samePairs']
                groupsT=read['groups']
                cornersT=read['page_corners']
                #cornersActualT=read['actualPage_corners']
                imageTemplate=read['imageFilename']
        else:
            template = os.path.join(directory,groupName,'template'+groupName+'.json')
            #tkMessageBox.showinfo("Template", "A template doesn't exist for group "+groupName+", creating one")
            print '!!!!!!!!!!!!!!!!!!!!!!!!!'
            print "A template doesn't exist for group "+groupName+", creating one"
            textsT,fieldsT,pairsT,samePairsT,groupsT,cornersT, actualCornersT = labelImage(os.path.join(directory,groupName,files[0]),textsT,fieldsT,pairsT,samePairsT,groupsT,None,cornersT,cornersActualT)
            if len(textsT)==0 and len(fieldsT)==0:
                lock.release()
                exit()
            else:
                 with open(template,'w') as out:
                     out.write(json.dumps({"textBBs":textsT, "fieldBBs":fieldsT, "pairs":pairsT, "samePairs":samePairsT, "groups":groupsT, "page_corners":cornersT, "imageFilename":files[0]}))

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
                if os.path.exists(gtFileName) and startHereImage is None:
                    continue
                texts=fields=pairs=samePairs=groups=page_corners=page_cornersActual=None
                try:
                    with open(gtFileName) as gtF:
                        read = json.loads(gtF.read())
                        texts=read['textBBs']
                        fields=read['fieldBBs']
                        pairs=read['pairs']
                        samePairs=read['samePairs']
                        groups=read['groups']
                        if 'page_corners' in read and 'actualPage_corners' in read:
                            page_corners=read['page_corners']
                            page_cornersActual=read['actualPage_corners']
                        assert f==read['imageFilename']
                        print 'g:'+groupName+', image: '+f+', gt found'
                        texts,fields,pairs,samePairs,groups,corners,actualCorners = labelImage(os.path.join(directory,groupName,f),texts,fields,pairs,samePairs,groups,None,page_corners,page_cornersActual)
                except IOError as e:
                    if e.errno == 2:
                        print 'g:'+groupName+', image: '+f+', from template'
                        texts,fields,pairs,samePairs,groups,corners,actualCorners = labelImage(os.path.join(directory,groupName,f),textsT,fieldsT,pairsT,samePairsT,groupsT,cornersT)
                    else:
                        raise

                if len(texts)==0 and len(fields)==0:
                    lock.release()
                    exit()
                if len(texts)+len(fields)+len(corners)>0:
                    with open(gtFileName,'w') as out:
                        out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "groups":groups, "page_corners":corners, "actualPage_corners":actualCorners, "imageFilename":f}))
        lock.release()
        lock=None
    except FileLockException as e:
        print 'template locked for group '+groupName+', moving to next group'
        lock=None
        continue
