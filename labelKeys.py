from labeler import labelImage
import os
import sys
import json

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
            if startHere is None:
                continue
            else:
                template = os.path.join(directory,groupName,f)

    texts=fields=pairs=samePairs=groups=page_corners=None
    if template is not None:
        with open(template) as f:
            read = json.loads(f.read())
            texts=read['textBBs']
            fields=read['fieldBBs']
            pairs=read['pairs']
            samePairs=read['samePairs']
            #for i in len(samePairs):
            #    if samePairs[i][-1][0]=='f':
            groups=read['groups']
            page_corners=read['page_corners']
            imageTemplate=read['imageFilename']
    print 'group '+groupName+', template image: '+imageTemplate                   
    texts,fields,pairs,samePairs,groups,corners = labelImage(os.path.join(directory,groupName,imageTemplate),texts,fields,pairs,samePairs,groups,page_corners)
    if len(texts)==0 and len(fields)==0:
        break
    outFile=os.path.join(directory,groupName,'template'+groupName+'.json')
    if len(texts)+len(fields)+len(corners)>0:
        with open(outFile,'w') as out:
            out.write(json.dumps({"textBBs":texts, "fieldBBs":fields, "pairs":pairs, "samePairs":samePairs, "groups":groups, "page_corners":corners, "imageFilename":imageTemplate}))
