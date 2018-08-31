from labeler import labelImage
from filelock import FileLock, FileLockException
import os
import sys
import json
import timeit
import grp

iains_groups=['136','14','142','144','145','146','146_1','153','153_1','153_2','155','158','159','16','163','171','172','173','174','182','187','189','193','194','197','199','200','29','30','34','34_1','35','35_1','39','4','42','46','46_1','46_2','5','52','53','53_1','58','58_1','6','60','60_1','60_2','60_3','61','62','62_1','65','68','69','70','71','71_1','72','75_1','78','79','8','81','81_1','86','86_1','88','89','89_1','89_2','93','96','98']
#groupId = grp.getgrnam("pairing").gr_gid
if len(sys.argv)<2:
    print 'usage: '+sys.argv[0]+' directory (startingGroup)'
    exit()

directory = sys.argv[1]
if len(sys.argv)>2:
    startHere = sys.argv[2]
    going=False
else:
    startHere=None
    going=True

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
    imageTemplate=None
    for f in files:
        if imageTemplate is None and f[-4:]=='.jpg':
            imageTemplate = files[0]

        if 'template' in f and f[-5:]=='.json':
            print 'found template for group '+groupName
            template = os.path.join(directory,groupName,f)

    if template is not None and startHere is None and groupName not in iains_groups:
        continue

    if groupName in iains_groups:
        print "this is in Iain's groups. Remove when finished with template, then set all to nf?"

    nfTemplate = os.path.join(directory,groupName,'template'+groupName+'.json.nf')
    nfExists = os.path.exists(nfTemplate)

    print 'group '+groupName+', template image: '+imageTemplate                   
    outFile=os.path.join(directory,groupName,'template'+groupName+'.json')
    lock = FileLock(outFile, timeout=None)
    try:
        lock.acquire()
        texts=fields=pairs=samePairs=horzLinks=groups=page_corners=page_cornersActual=None
        if template is not None or nfExists:
            if template is not None:
                f=open(template)
            elif nfExists:
                f=open(nfTemplate)
            read = json.loads(f.read())
            f.close()
            texts=read['textBBs']
            fields=read['fieldBBs']
            pairs=read['pairs']
            samePairs=read['samePairs']
            #for i in len(samePairs):
            #    if samePairs[i][-1][0]=='f':
            groups=read['groups']
            imageTemplate=read['imageFilename']
            if 'page_corners' in read:
                page_corners=read['page_corners']
            if 'actualPage_corners' in read:
                page_cornersActual=read['actualPage_corners']
            if 'labelTime' in read:
                labelTime=read['labelTime']
                startTime = timeit.default_timer()
            else:
                labelTime=None
            if 'horzLinks' in read:
                horzLinks = read['horzLinks']
        else:
            labelTime=0
            startTime = timeit.default_timer()
        texts,fields,pairs,samePairs,horzLinks,groups,corners,actualCorners,complete,r,c = labelImage(os.path.join(directory,groupName,imageTemplate),texts,fields,pairs,samePairs,horzLinks,groups,None,page_corners,page_cornersActual)
        if labelTime is not None:
            labelTime+=timeit.default_timer()-startTime
        if len(texts)==0 and len(fields)==0:
            break
        if not complete:
            outFile+='.nf'
        with open(outFile,'w') as out:
            out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "horzLinks":horzLinks, "groups":groups, "page_corners":corners, "imageFilename":imageTemplate, "labelTime": labelTime}))
        #os.chown(outFile,-1,groupId)
        lock.release()
        lock=None
        if not complete:
            exit()
        elif nfExists:
            os.remove(nfTemplate)
    except FileLockException as e:
        print 'template locked, moving to next group'
        lock=None
        continue
