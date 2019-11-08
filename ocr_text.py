from PIL import Image
from tesserocr import PyTessBaseAPI, PSM
import editdistance, cv2
import numpy as np
import sys, os, json, math
from matchBoxes import matchBoxes
from collections import defaultdict
from forms_annotations import getBBInfo

def _removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

directory = sys.argv[1]
outfile = sys.argv[2]
cropDir = sys.argv[3]
if not os.path.exists(cropDir):
    os.makedirs(cropDir)

threshold = 0.6
threshold_notMatched = 0.05
USE_SIMPLE=False

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
print(groupNames)


with PyTessBaseAPI(psm=PSM.SINGLE_LINE) as api:
    ocr_res={}
    all_ocr_to_ret={}
    for groupName in sorted(groupNames):
        if groupName!='99':
            continue
        print('group {}'.format(groupName))
        files = imageGroups[groupName]
        inGroup={}
        for f in files:
            if 'lock' not in f:
                if 'template' not in f and f[-5:]=='.json':
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    inGroup[f]=read
                elif 'template' in f and f[-5:]=='.json':
                    with open(os.path.join(directory,groupName,f)) as annFile:
                        read = json.loads(annFile.read())
                    template=read
        groupMatches = defaultdict(list)
        notMatched = []
        for f,read in inGroup.items():
            fileName = f[:-5]
            matchPairs = matchBoxes(template,read)
            matchedIds = []
            for tId, id in matchPairs:
                groupMatches[tId].append( (fileName,id) )
                matchedIds.append(id)
            imagePath = os.path.join(directory,groupName,read['imageFilename'])
            #image = Image.open(imagePath)
            cvImage = cv2.imread(imagePath,0) #grayscale
            #colorIm = cv2.imread(imagePath)
            #print('{}: {} x {}'.format(imagePath,cvImage.shape[0],cvImage.shape[1]))
            for textBB in read['textBBs']:
                id = textBB['id']
                #transform poly to rectangle
                xc,yc,h,w,rot, text,field,blank,nn = getBBInfo(textBB,True)
                h/=2
                w/=2
                tr = ( int(w*math.cos(rot)-h*math.sin(rot) + xc),  int(w*math.sin(rot)+h*math.cos(rot) + yc) )
                tl = ( int(-w*math.cos(rot)-h*math.sin(rot) + xc), int(-w*math.sin(rot)+h*math.cos(rot) + yc) )
                br = ( int(w*math.cos(rot)+h*math.sin(rot) + xc),  int(w*math.sin(rot)-h*math.cos(rot) + yc) )
                bl = ( int(-w*math.cos(rot)+h*math.sin(rot) + xc), int(-w*math.sin(rot)-h*math.cos(rot) + yc) )
                #colorIm[tr[1]-3:tr[1]+3,tr[0]-3:tr[0]+3,0]=255
                #colorIm[tl[1]-3:tl[1]+3,tl[0]-3:tl[0]+3,0]=255
                #colorIm[bl[1]-3:bl[1]+3,bl[0]-3:bl[0]+3,0]=255
                #colorIm[br[1]-3:br[1]+3,br[0]-3:br[0]+3,0]=255
                #yc=int(yc)
                #xc=int(xc)
                #colorIm[yc-3:yc+3,xc-3:xc+3,0:2]=255
                #print('bb: {}  {}  {}  {}'.format(tr,tl,br,bl))
                #crop
                maxX = min(max(tr[0],tl[0],br[0],bl[0]),cvImage.shape[1]-1)
                minX = max(min(tr[0],tl[0],br[0],bl[0]),0)
                maxY = min(max(tr[1],tl[1],br[1],bl[1]),cvImage.shape[0]-1)
                minY = max(min(tr[1],tl[1],br[1],bl[1]),0)
                uH = maxY-minY +1
                uW = maxX-minX +1
                crop = cvImage[minY:maxY+1,minX:maxX+1]
                if crop.shape[0]==0 or crop.shape[1]==0:
                    matchedIds.remove(id)
                    for tId, matches in groupMatches.items():
                        if (fileName,id) in matches:
                            matches.remove( (fileName,id) )
                    continue
                #cv2.imwrite(os.path.join(cropDir,'beforecrop.png'),colorIm)
                #rotate crop
                #final crop
                theta=rot
                M = np.float32( [[math.cos(theta), -math.sin(theta), math.cos(theta)*(-uW/2)-math.sin(theta)*(-uH/2)+w],
                                 [math.sin(theta), math.cos(theta), math.sin(theta)*(-uW/2)+math.cos(theta)*(-uH/2)+h]])
                #M = np.float32( [[math.cos(theta), -math.sin(theta), -uW/2],
                #                 [math.sin(theta), math.cos(theta), (-uH/2)]])
                #M = np.float32( [[math.cos(theta), -math.sin(theta), 0],
                #                 [math.sin(theta), math.cos(theta), 0]] )
                crop = cv2.warpAffine(crop,M,(int(round(2*w)),int(round(2*h))))
                #convert to PIL
                im_pil = Image.fromarray(np.pad(crop,(1,1),mode='reflect'))
                api.SetImage(im_pil)
                api.Recognize()
                text = api.GetUTF8Text()
                #?tesserocr.image_to_text(image)
                #api.AllWordConfidences()
                text = _removeNonAscii(text)


                globalId = '{}-{}-{}'.format(groupName,fileName,id)
                if id not in matchedIds:
                    notMatched.append(globalId)
                cropImagePath = os.path.join(cropDir,globalId+'.png')
                ocr_res[globalId]={
                        'pred': text.strip(),
                        'image': cropImagePath,
                        'root image': fileName
                        }
                #save crop image
                cv2.imwrite(cropImagePath,crop)


        #ensure matches are good; they at least sort of match OCR text
        #if they don't split into different matching groups
        matchedInstances=[]
        for tId, matches in groupMatches.items():
            theseMatch=[]
            for fileName,id in matches:
                globalId = '{}-{}-{}'.format(groupName,fileName,id)
                pred = ocr_res[globalId]['pred']
                addedToMatchings=False
                toAdd=[]
                for i,matchings in enumerate(theseMatch):
                    worstMatch=0
                    for otherId,otherPred in matchings:
                        if min(len(pred),len(otherPred))>0:
                            ed = editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                            worstMatch = max(ed,worstMatch)
                    if worstMatch < threshold:
                        #matchings.append((globalId,pred))
                        toAdd.append(i)
                        #if addedToMatchings:
                        #    print('id {} added to multiple matchings'.format(globalId))
                        addedToMatchings=True
                if not addedToMatchings:
                    theseMatch.append([(globalId,pred)])
                else:
                    theseMatch[toAdd[0]].append((globalId,pred))
                    if len(toAdd)>1:
                        for i in toAdd[1:]:
                            theseMatch[toAdd[0]] += theseMatch[i]
                        for i in toAdd[:0:-1]:
                            del theseMatch[i]
            for matchings in theseMatch:
                matchedInstances.append( [ i[0] for i in matchings ] )



        #select the best (most consistent in matching group) OCR text
        ocr_to_ret = {}
        for matchingIds in matchedInstances:
            scored=[]
            for id in matchingIds:
                cum = 0
                pred = ocr_res[id]['pred']
                for id2 in matchingIds:
                    if id!=id2:
                        otherPred = ocr_res[id2]['pred']
                        if min(len(pred),len(otherPred))>0:
                            cum += editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                        else:
                            cum+=1
                scored.append((cum,id))
            scored.sort(key = lambda a:a[0])
            id = scored[0][1]
            ocr_to_ret[id] = ocr_res[id]
            #if ocr_res[id]['pred'].startswith('SHIP TO'):
            #    print('Top: {}'.format(ocr_res[id]['pred']))
            #    print(scored)
            ocr_to_ret[id]['matches'] = matchingIds


        #merge unmatched instances in based on the similarity of OCR text
        for id in notMatched:
            pred = ocr_res[id]['pred']
            image = ocr_res[id]['root image']
            matchFound = False
            possibleMatches=[]
            if len(pred)>0:
                for otherId, res in ocr_to_ret.items():
                    otherPred = res['pred']
                    otherImage = res['root image']
                    if image!=otherImage and len(otherPred)>0:
                        ed = editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                        if ed<threshold_notMatched:
                            possibleMatches.append(otherId)
                            #res['matches'].append(id)
                            #if matchFound:
                            #    print('id {} added to multiple matchings (2)'.format(id))
                            matchFound=True
            if not matchFound:
                ocr_to_ret[id] = ocr_res[id]
                ocr_to_ret[id]['matches'] = [id]
            else:
                matchesWithSize = [ (mid,len(ocr_to_ret[mid]['matches'])) for mid in possibleMatches]
                matchesWithSize.sort(key = lambda a:a[1],reverse=True)
                #merge them
                res = ocr_to_ret[matchesWithSize[0][0]]
                #if res['pred'].startswith('SHIP TO'):
                #    print('2Top: {}'.format(res['pred']))
                #    print(matchesWithSize)
                res['matches'].append(id)
                for mid, _ in matchesWithSize[1:]:
                    res['matches'] += ocr_to_ret[mid]['matches']
                    del ocr_to_ret[mid]

                scored=[]
                for mid1 in res['matches']:
                    pred = ocr_res[mid1]['pred']
                    cum=0
                    for mid2 in res['matches']:
                        if mid1!=mid2:
                            otherPred = ocr_res[mid2]['pred']
                            if min(len(pred),len(otherPred))>0:
                                cum += editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                            else:
                                cum += 1
                    scored.append((cum,mid1))
                scored.sort(key = lambda a:a[0])
                best_pred = ocr_res[scored[0][1]]['pred']
                res['pred']=best_pred

                
        all_ocr_to_ret.update(ocr_to_ret)


    with open(outfile,'w') as f:
        json.dump(all_ocr_to_ret,f,indent=4)
    print('There are {} results needing checked/corrected/'.format(len(all_ocr_to_ret)))
    with open('./all_ocr.json','w') as f:
        json.dump(ocr_res,f,indent=4)
