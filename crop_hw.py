from PIL import Image
from tesserocr import PyTessBaseAPI, PSM
import editdistance, cv2
import numpy as np
import sys, os, json, math
from matchBoxes import matchBoxes
from collections import defaultdict
from forms_annotations import getBBInfo
import random

def _removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

if len(sys.argv)<12:
    print('usage: python {} directory splitFile ocrFile cropDir contextDir train_hw_out train_circle_out train_check_out testvalid_hw_out testvalid_circle_out testvalid_check_out'.format(sys.argv[0]))
    exit()

directory = sys.argv[1]
splitFile = sys.argv[2]
ocrResFile = sys.argv[3]
cropDir = sys.argv[4]
contextDir = sys.argv[5]
train_hw_out = sys.argv[6]
train_circle_out = sys.argv[7]
train_check_out = sys.argv[8]
testvalid_hw_out = sys.argv[9]
testvalid_circle_out = sys.argv[10]
testvalid_check_out = sys.argv[11]

PAD=3

if not os.path.exists(cropDir):
    os.makedirs(cropDir)
if not os.path.exists(contextDir):
    os.makedirs(contextDir)

with open(splitFile) as f:
    splits = json.load(f)

with open(ocrResFile) as f:
    ocr_res_match = json.load(f)
ocr_res={}
for res in ocr_res_match:
    for id in res['matches']:
        ocr_res[id]=res['pred']

#loop

#if USE_SIMPLE:
#    with open(os.path.join(directory,'simple_train_valid_test_split.json')) as f:
#        splitFile = json.load(f)
#else:
#    with open(os.path.join(directory,'train_valid_test_split.json')) as f:
#        splitFile = json.load(f)
#if getStats:
#    if doSplit:
#        simpleFiles = splitFile[doSplit]
#    else:
#        simpleFiles = dict(list(splitFile['train'].items())+ list(splitFile['valid'].items()))
#else:
#    simpleFiles = dict(list(splitFile['train'].items())+ list(splitFile['test'].items())+ list(splitFile['valid'].items()))
imageGroups={}
groupNames=[]
for root, dirs, files in os.walk(directory):
    #print 'root: '+root
    if root[-1]=='/':
        root=root[:-1]
    groupName = root[root.rindex('/')+1:]
    #if rr==groupName:
    #    continue
    #if (not USE_SIMPLE and not getStats) or groupName in simpleFiles:
    imageGroups[groupName]=sorted(files)
    groupNames.append(groupName)
groupNames.remove('groups')
print(groupNames)


with PyTessBaseAPI(psm=PSM.SINGLE_LINE) as api:
    testvalid_hw_map=[]
    testvalid_circle_map=[]
    testvalid_check_map=[]
    train_hw_map=[]
    train_circle_map=[]
    train_check_map=[]
    for groupName in sorted(groupNames):
        #if groupName!='152':
        #    continue
        #if groupName!='99' and groupName!='1' and groupName!='125_2' and groupName!='77':
        #    continue
        #if int(groupName[:groupName.find('_')])>25
        print('group {}'.format(groupName))
        if groupName in splits['train']:
            split='train'
        else:
            split='testvalid'
        files = imageGroups[groupName]
        for f in files:
            if 'lock' not in f:
                if 'template' not in f and f[-5:]=='.json':
                    fileName = f[:-5]
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    read['byId']={}
                    for BB in read['fieldBBs']+read['textBBs']:
                        read['byId'][BB['id']] = BB
                    pairs = read['pairs']+read['samePairs']
                    pairMap=defaultdict(list)
                    for id1,id2 in pairs:
                        if id1 in read['byId'] and id2 in read['byId']:
                            if read['byId'][id2]['type'] != 'fieldRow' and read['byId'][id2]['type'] != 'fieldCol':
                                pairMap[id1].append(id2)
                            if read['byId'][id1]['type'] != 'fieldRow' and read['byId'][id1]['type'] != 'fieldCol':
                                pairMap[id2].append(id1)
                    imagePath = os.path.join(directory,groupName,read['imageFilename'])
                    cvImage = cv2.imread(imagePath,0) #grayscale
                    for fieldBB in read['fieldBBs']:
                        if fieldBB['type'] != 'fieldRow' and fieldBB['type'] != 'fieldCol' and fieldBB['type'] != 'fieldRegion' and fieldBB['type'] != 'graphic' and fieldBB['isBlank']!=3:
                            id = fieldBB['id']
                            #transform poly to rectangle
                            xc,yc,h,w,rot, text,field,blank,nn = getBBInfo(fieldBB,True)
                            h/=2
                            w/=2
                            h+=PAD
                            w+=PAD
                            tr = ( int(w*math.cos(rot)-h*math.sin(rot) + xc),  int(w*math.sin(rot)+h*math.cos(rot) + yc) )
                            tl = ( int(-w*math.cos(rot)-h*math.sin(rot) + xc), int(-w*math.sin(rot)+h*math.cos(rot) + yc) )
                            br = ( int(w*math.cos(rot)+h*math.sin(rot) + xc),  int(w*math.sin(rot)-h*math.cos(rot) + yc) )
                            bl = ( int(-w*math.cos(rot)+h*math.sin(rot) + xc), int(-w*math.sin(rot)-h*math.cos(rot) + yc) )
                            maxX = min(max(tr[0],tl[0],br[0],bl[0]),cvImage.shape[1]-1)
                            minX = max(min(tr[0],tl[0],br[0],bl[0]),0)
                            maxY = min(max(tr[1],tl[1],br[1],bl[1]),cvImage.shape[0]-1)
                            minY = max(min(tr[1],tl[1],br[1],bl[1]),0)
                            uH = maxY-minY +1
                            uW = maxX-minX +1
                            crop = cvImage[minY:maxY+1,minX:maxX+1]
                            if crop.shape[0]==0 or crop.shape[1]==0:
                                continue
                            theta=rot
                            M = np.float32( [[math.cos(theta), -math.sin(theta), math.cos(theta)*(-uW/2)-math.sin(theta)*(-uH/2)+w],
                                             [math.sin(theta), math.cos(theta), math.sin(theta)*(-uW/2)+math.cos(theta)*(-uH/2)+h]])
                            crop = cv2.warpAffine(crop,M,(int(round(2*w)),int(round(2*h))))

                            if fieldBB['isBlank']==2:
                                with PyTessBaseAPI(psm=PSM.SINGLE_LINE) as api:
                                    im_pil = Image.fromarray(np.pad(crop,(1,1),mode='reflect'))
                                    api.SetImage(im_pil)
                                    api.Recognize()
                                    text = api.GetUTF8Text()
                                    pred = _removeNonAscii(text).strip()
                            else:
                                pred = None

                            label=None
                            for pId in pairMap[id]:
                                xc,yc,h,w,rot, text,field,blank,nn = getBBInfo(read['byId'][pId],True)
                                h/=2
                                w/=2
                                h+=PAD
                                w+=PAD
                                tr = ( int(w*math.cos(rot)-h*math.sin(rot) + xc),  int(w*math.sin(rot)+h*math.cos(rot) + yc) )
                                tl = ( int(-w*math.cos(rot)-h*math.sin(rot) + xc), int(-w*math.sin(rot)+h*math.cos(rot) + yc) )
                                br = ( int(w*math.cos(rot)+h*math.sin(rot) + xc),  int(w*math.sin(rot)-h*math.cos(rot) + yc) )
                                bl = ( int(-w*math.cos(rot)+h*math.sin(rot) + xc), int(-w*math.sin(rot)-h*math.cos(rot) + yc) )
                                maxX = max(maxX, min(max(tr[0],tl[0],br[0],bl[0]),cvImage.shape[1]-1) )
                                minX = min(minX, max(min(tr[0],tl[0],br[0],bl[0]),0) )
                                maxY = max(maxY, min(max(tr[1],tl[1],br[1],bl[1]),cvImage.shape[0]-1) )
                                minY = min(minY, max(min(tr[1],tl[1],br[1],bl[1]),0) )
                                pGlobalId = '{}-{}-{}'.format(groupName,fileName,pId)
                                if pGlobalId in ocr_res:
                                    if label is None:
                                        label = ocr_res[pGlobalId]
                                    else:
                                        label = ''

                            context = cvImage[minY:maxY+1,minX:maxX+1]
                            mask = np.ones(context.shape)
                            points = [[p[0]-minX,p[1]-minY] for p in fieldBB['poly_points']]
                            cv2.fillConvexPoly(mask,np.array(points,dtype=np.int64),0.8)
                            context = np.stack((context*mask,context,context),axis=2)

                            globalId = '{}-{}-{}'.format(groupName,fileName,id)
                            crop_im_path = os.path.join(cropDir,globalId+'.png')
                            context_im_path = os.path.join(contextDir,globalId+'.png')
                            cv2.imwrite(crop_im_path,crop)
                            cv2.imwrite(context_im_path,context)

                            data = {
                                    'id': globalId,
                                    'crop_image': crop_im_path,
                                    'context_image': context_im_path,
                                    'type': fieldBB['type']
                                    } 
                            if label is not None and len(label)>0:
                                data['label']=label
                            if pred is not None:
                                data['pred']=pred
                            if split=='train':
                                if fieldBB['type']=='fieldCircle':
                                    train_circle_map.append(data)
                                elif fieldBB['type']=='fieldCheckBox':
                                    train_check_map.append(data)
                                else:
                                    train_hw_map.append(data)
                            else:
                                if fieldBB['type']=='fieldCircle':
                                    testvalid_circle_map.append(data)
                                elif fieldBB['type']=='fieldCheckBox':
                                    testvalid_check_map.append(data)
                                else:
                                    testvalid_hw_map.append(data)
    random.shuffle(train_hw_map)
    random.shuffle(train_circle_map)
    random.shuffle(train_check_map)
    with open(train_hw_out,'w') as f:
        json.dump(train_hw_map,f,indent=4)
    with open(train_circle_out,'w') as f:
        json.dump(train_circle_map,f,indent=4)
    with open(train_check_out,'w') as f:
        json.dump(train_check_map,f,indent=4)
    with open(testvalid_hw_out,'w') as f:
        json.dump(testvalid_hw_map,f,indent=4)
    with open(testvalid_circle_out,'w') as f:
        json.dump(testvalid_circle_map,f,indent=4)
    with open(testvalid_check_out,'w') as f:
        json.dump(testvalid_check_map,f,indent=4)
    print('There are {} + {} = {} instances to be trascribed'.format(len(testvalid_hw_map),len(train_hw_map),len(testvalid_hw_map)+len(train_hw_map)))
    print('There are {} + {} = {} circle'.format(len(testvalid_circle_map),len(train_circle_map),len(testvalid_circle_map)+len(train_circle_map)))
    print('There are {} + {} = {} check'.format(len(testvalid_check_map),len(train_check_map),len(testvalid_check_map)+len(train_check_map)))
