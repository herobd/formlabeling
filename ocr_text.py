from PIL import Image
from tesserocr import PyTessBaseAPI, PSM

#7 = Treat the image as a single text line.




#loop

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
        simpleFiles = dict(list(splitFile['train'].items())+ list(splitFile['valid'].items()))
else:
    simpleFiles = dict(list(splitFile['train'].items())+ list(splitFile['test'].items())+ list(splitFile['valid'].items()))
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



with PyTessBaseAPI(psm=PSM.PSM_SINGLE_LINE) as api:
    for groupName in sorted(groupNames):
        if groupName=='121':
            continue
        files = imageGroups[groupName]
        usedGroup=False
        imageFiles=[]
        info=[]
        for f in files:
            if 'lock' not in f:
                if 'template' not in f and f[-5:]=='.json':
                    if not usedGroup:
                        numGroupsUsed+=1
                        usedGroup=True
                    numImagesUsed+=1
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())

                    imagePath = ?
                    image = Image.open(imagePath)
                    api.SetImage(image)
                    api.Recognize()
                    text = api.GetUTF8Text()
                    #?tesserocr.image_to_text(image)
                    #api.AllWordConfidences()
                    
