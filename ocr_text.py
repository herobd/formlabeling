from PIL import Image
from tesserocr import PyTessBaseAPI, PSM
import editdistance, cv2
import numpy as np
import sys, os, json, math
from matchBoxes import matchBoxes
from collections import defaultdict
from forms_annotations import getBBInfo

def _removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

def compareSize(s1,s2):
    hDiff = abs(s1[0]-s2[0])
    wDiff = abs(s1[1]-s2[1])
    hA = max(45,(s1[0]+s2[0])/2)
    wA = max(100,(s1[1]+s2[1])/2)

    wMul = min(5,wA/100)

    return 0.5*hDiff/hA + wMul*wDiff/wA

def compareLoc(aFrom,aTo,bFrom,bTo):
    aDist = math.sqrt((aFrom[0]-aTo[0])**2 + (aFrom[1]-aTo[1])**2)
    bDist = math.sqrt((bFrom[0]-bTo[0])**2 + (bFrom[1]-bTo[1])**2)
    aAngle = math.atan2(aFrom[1]-aTo[1],aFrom[0]-aTo[0])
    bAngle = math.atan2(bFrom[1]-bTo[1],bFrom[0]-bTo[0])

    return abs(aDist-bDist)/100 + (0 if abs(aAngle-bAngle)<0.35 else abs(aAngle-bAngle)-0.35)


def checkDup(ocr_matched):
    for id, res in ocr_matched.items():
        group=id[:id.find('-')]
        if res is not None:
            for i,mid in enumerate(res['matches']):
                assert(group==mid[:mid.find('-')])
                assert(mid not in res['matches'][i+1:])
                rooti = ocr_res[mid]['root image']
                assert(rooti not in [ocr_res[mid2]['root image'] for mid2 in res['matches'][i+1:]])

directory = sys.argv[1]
outfile = sys.argv[2]
cropDir = sys.argv[3]
if not os.path.exists(cropDir):
    os.makedirs(cropDir)

threshold = 0.7
threshold_notMatched = 0.06
sizeThreshold = 0.15
merge_pred_length=8
match_thresh_ed=0.5
match_thresh_size=0.07
match_thresh_loc=0.06
combScoreThreshold2=0.25
reAdd_threshold=0.25
USE_SIMPLE=False
ED_EMPTY=0.33
TRACK='152-100587124_00357-t10'

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
    all_ocr_res={}
    all_ocr_matched={}
    for groupName in sorted(groupNames):
        #if groupName!='152':
        #    continue
        #if groupName!='99' and groupName!='1' and groupName!='125_2' and groupName!='77':
        #    continue
        #if int(groupName[:groupName.find('_')])>25
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
        bbSize = {}
        bbLoc = {}
        neighbors = {}
        ocr_res = {}
        for f,read in inGroup.items():
            fileName = f[:-5]
            matchPairs = matchBoxes(template,read)
            pairs = read['pairs']+read['samePairs']
            matchedIds = []
            for tId, id in matchPairs:
                groupMatches[tId].append( (fileName,id) )
                matchedIds.append(id)
                globalId = '{}-{}-{}'.format(groupName,fileName,id)
                if globalId==TRACK:
                    print('{} is part of group match {}'.format(TRACK,tId))
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
                        'root image': fileName,
                        'text':True
                        }
                bbSize[globalId] = (h,w)
                bbLoc[globalId] = (xc,yc)
                #neighbors[globalId] = ['{}-{}-{}'.format(groupName,fileName,p[0]) for p in read['samePairs'] if p[1]==id] + ['{}-{}-{}'.format(groupName,fileName,p[1]) for p in read['samePairs'] if p[0]==id]
                neighbors[globalId] = ['{}-{}-{}'.format(groupName,fileName,p[0]) for p in pairs if p[1]==id] + ['{}-{}-{}'.format(groupName,fileName,p[1]) for p in pairs if p[0]==id]
                #save crop image
                cv2.imwrite(cropImagePath,crop)

            for fieldBB in read['fieldBBs']:
                id = fieldBB['id']
                #transform poly to rectangle
                xc,yc,h,w,rot, text,field,blank,nn = getBBInfo(fieldBB,True)
                h/=2
                w/=2
                globalId = '{}-{}-{}'.format(groupName,fileName,id)
                if id not in matchedIds:
                    notMatched.append(globalId)
                ocr_res[globalId]={
                        'pred':'',
                        'image':'FIELD',
                        'root image':'FIELD',
                        'text':False
                        }
                bbSize[globalId] = (h,w)
                bbLoc[globalId] = (xc,yc)
                neighbors[globalId] = ['{}-{}-{}'.format(groupName,fileName,p[0]) for p in pairs if p[1]==id] + ['{}-{}-{}'.format(groupName,fileName,p[1]) for p in pairs if p[0]==id]

        #check neighbors
        for id, ns in neighbors.items():
            toRemove=[]
            for n in ns:
                if n not in ocr_res:
                    toRemove.append(n)
            for n in toRemove:
                ns.remove(n)

        #ensure matches are good; they at least sort of match OCR text and are same size
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
                    worstMatchSize=0
                    for otherId,otherPred in matchings:
                        if min(len(pred),len(otherPred))>0:
                            ed = editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                            worstMatch = max(ed,worstMatch)
                        worstMatchSize = max(worstMatchSize,compareSize(bbSize[globalId],bbSize[otherId]))
                    if globalId==TRACK:
                        print('worstMatch:{}, worstMatchSize:{}, for theseMatch:{}'.format(worstMatch,worstMatchSize,theseMatch))
                    if worstMatch < threshold and worstMatchSize < sizeThreshold:
                        if globalId==TRACK:
                            print('{} was matched'.format(TRACK))
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
                if len(matchings)>1:
                    matchedInstances.append( [ i[0] for i in matchings ] )
                else:
                    notMatched.append(matchings[0][0])



        #select the best (most consistent in matching group) OCR text
        ocr_matched = {}
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
            ocr_matched[id] = dict(ocr_res[id])
            #if ocr_res[id]['pred'].startswith('SHIP TO'):
            #    print('Top: {}'.format(ocr_res[id]['pred']))
            #    print(scored)
            ocr_matched[id]['matches'] = matchingIds

        #merge unmatched instances in based on the similarity of OCR text
        for id in notMatched:
            pred = ocr_res[id]['pred']
            image = ocr_res[id]['root image']
            matchFound = False
            possibleMatches=[]
            if len(pred)>0:
                for otherId, res in ocr_matched.items():
                    otherPred = res['pred']
                    #otherImage = res['root image']
                    otherImages = [ocr_res[mid]['root image'] for mid in res['matches']]
                    if image not in otherImages and len(otherPred)>0:
                        ed = editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                        if max(len(pred),len(otherPred)) <3:
                            adapt_threshold_notMatched= threshold_notMatched
                        elif max(len(pred),len(otherPred)) <5:
                            adapt_threshold_notMatched= 0.2#threshold_notMatched
                        elif max(len(pred),len(otherPred)) <8:
                            adapt_threshold_notMatched= 0.3#threshold_notMatched
                        elif max(len(pred),len(otherPred)) <12:
                            adapt_threshold_notMatched= 0.5#threshold_notMatched
                        elif max(len(pred),len(otherPred)) <16:
                            adapt_threshold_notMatched= 0.6#threshold_notMatched
                        else:
                            adapt_threshold_notMatched=threshold
                        if ed<adapt_threshold_notMatched:
                            possibleMatches.append( (ed,otherId) )
                            #res['matches'].append(id)
                            #if matchFound:
                            #    print('id {} added to multiple matchings (2)'.format(id))
                            matchFound=True
            if not matchFound:
                ocr_matched[id] = ocr_res[id]
                ocr_matched[id]['matches'] = [id]
                if id==TRACK:
                    print('{}  has NO possible OCR matches'.format(TRACK))
            else:
                if id==TRACK:
                    print('{}  has possible OCR matches'.format(TRACK))

                #if len(pred)>merge_pred_length and len(possibleMatches)>1:
                #    #print('possible merge, {} groups'.format(len(possibleMatches)))
                #    #check if any of the matched groups can be merged (no image intersection)
                #    possibleMerges=[]
                #    for i,(ed,otherId) in enumerate(possibleMatches):
                #        otherImages = [ocr_res[mid]['root image'] for mid in ocr_matched[otherId]['matches']]
                #        for ed2,otherId2 in possibleMatches[i+1:]:
                #            otherImages2 = [ocr_res[mid]['root image'] for mid in ocr_matched[otherId2]['matches']]
                #            if len(set(otherImages).intersection(set(otherImages2)))==0:
                #                print('possible merge')
                #                possibleMerges.append( [otherId,otherId2] )
                #    if len(possibleMerges)>1:
                #        print('Multiple possible merges ({}), skipping'.format(len(possibleMerges)))
                #    else:
                #        firstId= possibleMerges[0][0]
                #        secondId= possibleMerges[0][1]
                #        res=ocr_matched[firstId]
                #        res['matches']+=ocr_matched[secondId]['matches']
                #        scored=[]
                #        for mid1 in res['matches']:
                #            pred = ocr_res[mid1]['pred']
                #            cum=0
                #            for mid2 in res['matches']:
                #                if mid1!=mid2:
                #                    otherPred = ocr_res[mid2]['pred']
                #                    if min(len(pred),len(otherPred))>0:
                #                        cum += editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                #                    else:
                #                        cum += 1
                #            scored.append((cum,mid1))
                #        scored.sort(key = lambda a:a[0])
                #        best_pred = ocr_res[scored[0][1]]['pred']
                #        res['pred']=best_pred
                #    #matchesWithSize = [ (mid,len(ocr_matched[mid]['matches'])) for mid in possibleMatches]
                #    #matchesWithSize.sort(key = lambda a:a[1],reverse=True)
                #    ##merge them
                #    #res = ocr_matched[matchesWithSize[0][0]]
                #    ##if res['pred'].startswith('SHIP TO'):
                #    ##    print('2Top: {}'.format(res['pred']))
                #    ##    print(matchesWithSize)
                #    #res['matches'].append(id)
                #    #for mid, _ in matchesWithSize[1:]:
                #    #    res['matches'] += ocr_matched[mid]['matches']
                #    #    del ocr_matched[mid]

                #    #scored=[]
                #    #for mid1 in res['matches']:
                #    #    pred = ocr_res[mid1]['pred']
                #    #    cum=0
                #    #    for mid2 in res['matches']:
                #    #        if mid1!=mid2:
                #    #            otherPred = ocr_res[mid2]['pred']
                #    #            if min(len(pred),len(otherPred))>0:
                #    #                cum += editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                #    #            else:
                #    #                cum += 1
                #    #    scored.append((cum,mid1))
                #    #scored.sort(key = lambda a:a[0])
                #    #best_pred = ocr_res[scored[0][1]]['pred']
                #    #res['pred']=best_pred
                #add to the best match (by edit distance and location) after merge
                bestScore=999999
                for ed,otherId in possibleMatches:
                    xs = [bbLoc[mid][0] for mid in ocr_matched[otherId]['matches']]
                    ys = [bbLoc[mid][1] for mid in ocr_matched[otherId]['matches']]
                    xMean = np.mean(xs)
                    yMean = np.mean(ys)
                    dist = math.sqrt( (xMean-bbLoc[id][0])**2 + (yMean-bbLoc[id][1])**2)
                    score = ed + max(dist-50,0)/200
                    if score<bestScore:
                        bestScore=score
                        bestOtherId = otherId
                ocr_matched[bestOtherId]['matches'].append(id)

        checkDup(ocr_matched)

        ocrId_to_retId = {}
        for rid,res in ocr_matched.items():
            for mid in res['matches']:
                ocrId_to_retId[mid]=rid

        didSplit=[]
        def GreatMerge():
            #merge existing matching groups based on neighbors matching groups
            remove=[]
            for id, res in ocr_matched.items():
                if res is not None:
                    pred=res['pred']
                    neighborGroups=set()
                    candidateMergeGroups=[]
                    mergeGroupImmediateNeighbors = set()
                    images = set([ocr_res[mid]['root image'] for mid in res['matches']])
                    for fromId in res['matches']:
                        mergeGroupImmediateNeighbors.update(neighbors[fromId])
                    if TRACK in res['matches']:
                        print('Merge looking at {} matching group'.format(TRACK))
                    for fromId in res['matches']:
                        #if fromId==TRACK:
                        #    import pdb;pdb.set_trace()
                        #the neighbors we go to
                        for neighborToId in neighbors[fromId]:
                            if neighborToId in ocrId_to_retId:
                                neighborGroupId = ocrId_to_retId[neighborToId]

                                if neighborGroupId not in neighborGroups and ocr_matched[neighborGroupId] is not None: #if this isn't a group we've alread done
                                    neighborGroups.add(neighborGroupId)
                                    for otherToId in ocr_matched[neighborGroupId]['matches']: #instances in group
                                        if otherToId not in mergeGroupImmediateNeighbors:
                                            innerCandidates=[]
                                            if TRACK in neighbors[otherToId]:
                                                print('{} is possible parallel to {}'.format(TRACK,fromId))
                                            for neighborFromId in neighbors[otherToId]: #could it go back to an instance we need to merge with?
                                                nimages = set([ocr_res[mid]['root image'] for mid in ocr_matched[ocrId_to_retId[neighborFromId]]['matches']])
                                                if neighborFromId in ocr_res and res['text']==ocr_res[neighborFromId]['text'] and len(images.intersection(nimages))==0:
                                                    assert(neighborFromId not in res['matches']) #if it's not alread in our group
                                                    otherPred = ocr_res[neighborFromId]['pred']
                                                    size=compareSize(bbSize[fromId],bbSize[neighborFromId])
                                                    loc=compareLoc(bbLoc[fromId],bbLoc[neighborToId],  bbLoc[neighborFromId],bbLoc[otherToId])
                                                    if len(otherPred)>0 and len(pred)>0:
                                                        ed = editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                                                        ed = min(ed,0.5) # max 50% error, since OCR isn't too reliabl
                                                    else:
                                                        ed = ED_EMPTY
                                                    score = (ed + size*6 + loc*3)/3 #how similar is id->neighborGroupId to neighborId->neighborGroupId?
                                                    if fromId==TRACK or neighborFromId==TRACK:
                                                        print('Merge score {} -> {} , score:{}, ed:{}, size:{}, loc:{}'.format(fromId,neighborFromId,score,ed,size,loc))
                                                    #if score<combScoreThreshold1:
                                                    if size<match_thresh_size and loc<match_thresh_loc:
                                                        innerCandidates.append((score,size,loc,ocrId_to_retId[neighborFromId]))
                                                        assert (id[:id.find('-')] == neighborFromId[:neighborFromId.find('-')])
                                            #the parallel that needs merged to our matching group will only be one of the neighbors, so only keep the best.
                                            if len(innerCandidates)>0:
                                                innerCandidates.sort(key=lambda a:a[0])
                                                candidateMergeGroups.append( innerCandidates[0] )

                            elif fromId==TRACK:
                                print('{} not in ocrId_to_retId?'.format(TRACK))
                    finalScores=defaultdict(lambda:999)
                    m_size = defaultdict(list)
                    m_loc = defaultdict(list)
                    votes=defaultdict(lambda:-1)
                    for score,size,loc,mergeId in candidateMergeGroups:
                        finalScores[mergeId] = min(score,finalScores[mergeId])
                        votes[mergeId] += 1
                        m_size[mergeId].append(size)
                        m_loc[mergeId].append(loc)
                    for mergeId,score in finalScores.items():
                        if (mergeId,id) not in didSplit and (id,mergeId) not in didSplit:
                            score -= 0.05*votes[mergeId] #better score for more consistency among instances
                            if score<combScoreThreshold2:
                                #perform merge
                                remove.append(mergeId)
                                for mid  in ocr_matched[mergeId]['matches']:
                                    if mid not in res['matches']:
                                        res['matches'].append(mid)
                                        ocrId_to_retId[mid]=id
                                ocr_matched[mergeId] = None
                                #print('Merge candidate {}->{}, score: {:.3}, adjusted score: {:.3}, size: m:{:.3}, s:{:.3}, loc m:{:.3}, s:{:.3}'.format(mergeId,id,score,score-0.05*votes[mergeId],np.mean(m_size[mergeId]),np.std(m_size[mergeId]),np.mean(m_loc[mergeId]),np.std(m_loc[mergeId])))
                            #checkDup(ocr_matched)
                        else:
                            print('Rejected remerge: {} and {}'.format(id,mergeId))


            #clean up merges
            for id in remove:
                del ocr_matched[id]

        def getAvgScore(id,ids):
            pred = ocr_res[id]['pred']
            myLoc = bbLoc[id]
            scores=[]
            for otherId in ids:
                print('me:{}  other:{}'.format(id,otherId))
                print('my:{},   other:{}'.format(neighbors[id],neighbors[otherId]))
                otherPred = ocr_res[otherId]['pred']
                size=compareSize(bbSize[id],bbSize[otherId])
                otherLoc = bbLoc[otherId]

                neighborScore=0
                for myNeighbor in neighbors[id]:
                    minScore=1
                    for otherNeighbor in neighbors[otherId]:
                        if ocr_res[myNeighbor]['text'] == ocr_res[otherNeighbor]['text']:
                            nPred = ocr_res[myNeighbor]['pred']
                            otherNPred = ocr_res[otherNeighbor]['pred']
                            size=compareSize(bbSize[myNeighbor],bbSize[otherNeighbor])
                            loc=compareLoc(myLoc,bbLoc[myNeighbor],  otherLoc,bbLoc[otherNeighbor])
                            if len(otherNPred)>0 and len(nPred)>0:
                                ed = editdistance.eval(nPred, otherNPred)/min(len(nPred),len(otherNPred))
                                ed = min(0.5,ed)
                            elif len(otherNPred)==0 and len(nPred)==0:
                                ed = 0.1
                            else:
                                ed = ED_EMPTY
                            score = (ed + size*6 + loc*3)/3
                            print('sizes: {}, {}, locs: {}, {}, {}, {}'.format(bbSize[myNeighbor],bbSize[otherNeighbor],myLoc,bbLoc[myNeighbor],otherLoc,bbLoc[otherNeighbor]))
                            print('{}->{} == {}->{},  score:{}, ed:{}, size:{}, loc:{}'.format(id,myNeighbor,otherId,otherNeighbor,score,ed,size,loc))
                            minScore=min(minScore,score)
                    
                    neighborScore += minScore
                    print('minScore: {}'.format(minScore))
                neighborScore= (neighborScore+max(len(neighbors[otherId])-len(neighbors[id]),0))/max(len(neighbors[id]),len(neighbors[otherId]))
                print('neighbor:{}, len id:{}, len otherId:{}'.format(neighborScore,len(neighbors[id]),len(neighbors[otherId])))
                if len(otherPred)>0 and len(pred)>0:
                    ed = editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                    ed = min(0.5,ed)
                else:
                    ed = ED_EMPTY
                score = (ed + size*6 + neighborScore*3)/3
                print('{}  {}  ed:{}, size:{}, neighborScore:{}'.format(id,otherId,ed,size,neighborScore))
                scores.append(score)
            return np.mean(scores), np.std(scores)

        def addToSplit(mid,openI,new):
            if len(openI)==0:
                new.append(set([mid]))
            else:
                bestScore=99999
                bestStd=0
                for i in openI:
                    score, std_score = getAvgScore(mid,new[i])
                    if score<bestScore:
                        bestScore=score
                        bestI = i
                        bestStd=std_score
                print('bestScore: {} std:{}    {}'.format(bestScore,bestStd,'125_2-004191670_00343-t413' if mid=='125_2-004191670_00343-t413' else ' '))
                print('{} => {}'.format(mid,new[bestI]))
                if bestScore<reAdd_threshold:
                    new[bestI].add(mid)
                else:
                    new.append(set([mid]))
        def getBestSplit(mid,openI,new):
            bestScore=99999
            bestStd=0
            for i in openI:
                score, std_score = getAvgScore(mid,new[i])
                if score<bestScore:
                    bestScore=score
                    bestI = i
                    bestStd=std_score
            print('bestScore: {} std:{}    {}'.format(bestScore,bestStd,' '))
            print('{} => {}'.format(mid,new[bestI]))
            if bestScore<reAdd_threshold:
                return bestI
            else:
                return None
        def GreatSplit():
            toSplit=[]
            for id, res in ocr_matched.items():
                new=[]
                newRoots=[]
                for mid in res['matches']:
                    rooti = ocr_res[mid]['root image']
                    #find which new split we could be put in (no conflicting image)
                    openForMid=[]
                    for i in range(len(new)):
                        if rooti not in newRoots[i]:
                            openForMid.append(i)
                    if len(openForMid)==0:
                        new.append([mid])
                        newRoots.append(set([rooti]))
                    elif len(openForMid)==1:
                        i=openForMid[0]
                        new[i].append(mid)
                        newRoots[i].add(rooti)
                    else:
                        i=getBestSplit(mid,openForMid,new)
                        if i is not None:
                            new[i].append(mid)
                            newRoots[i].add(rooti)
                        else:
                            new.append([mid])
                            newRoots.append(set([rooti]))
                #if len is 1, we don't need to split
                if len(new)>1:
                    toSplit.append( (id,new) )
                else:
                    assert(res['matches']==new[0])

            #actually split them
            for id, new in toSplit:
                res = ocr_matched[id]
                newResults=[]
                for matches in new:
                    newRes = {**res}
                    newRes['matches']=matches

                    #find best pred given new split
                    scored=[]
                    for mid1 in newRes['matches']:
                        pred = ocr_res[mid1]['pred']
                        cum=0
                        for mid2 in newRes['matches']:
                            if mid1!=mid2:
                                otherPred = ocr_res[mid2]['pred']
                                if min(len(pred),len(otherPred))>0:
                                    cum += editdistance.eval(pred, otherPred)/min(len(pred),len(otherPred))
                                else:
                                    cum += 1
                        scored.append((cum,mid1))
                    scored.sort(key = lambda a:a[0])
                    best_pred = ocr_res[scored[0][1]]['pred']
                    newRes['pred']=best_pred
                    newRes['root image']=ocr_res[scored[0][1]]['root image']
                    newRes['image']=ocr_res[scored[0][1]]['image']

                    newResults.append( (scored[0][1],newRes) )

                del ocr_matched[id]
                for i,(newId, res) in enumerate(newResults):
                    ocr_matched[newId]=res
                    for mid in res['matches']:
                        ocrId_to_retId[mid]=newId
                        if mid==TRACK:
                            print('{} got split old:{}, new:{}'.format(TRACK,id,newId))
                    for newId2,res2 in newResults[i+1:]:
                        didSplit.append((newId,newId2))

                #incongruent=[]
                #for i,mid in enumerate(res['matches']):
                #    rooti = ocr_res[mid]['root image']
                #    for mid2 in res['matches'][i+1:]:
                #        rooti2 = ocr_res[mid2]['root image']
                #        if rooti==rooti2:
                #            incongruent.append((mid,mid2))
                ##if mid=='125_2-004191670_00343-t413' or mid2=='125_2-004191670_00343-t413'

                #if len(incongruent)>0:
                #    new=[set(),set()]
                #    for mid,mid2 in incongruent:
                #        if len(new[0])==0:
                #            new[0].add(mid)
                #            new[1].add(mid2)
                #        else:
                #            openFor1=[]
                #            openFor2=[]
                #            for i in range(len(new)):
                #                if mid not in new[i]:
                #                    openFor2.append(i)
                #                if mid2 not in new[i]:
                #                    openFor1.append(i)
                #            addToSplit(mid,openFor1,new)
                #            addToSplit(mid2,openFor2,new)
                                


        GreatMerge()
        GreatSplit()
        GreatMerge()
        GreatSplit()

        #recompute best pred (and match image?)
        #num_matched=[]
        for id,res in ocr_matched.items():
            scored=[]
            #num_matched.append(len(res['matches']))
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
            res['root image']=ocr_res[scored[0][1]]['root image']
            res['image']=ocr_res[scored[0][1]]['image']

        #sizes=[]
        #locs=[]
        #for id,res in ocr_matched.items():
        #    nPair=defaultdict(list)
        #    for i,mid in enumerate(res['matches']):
        #        for neighborId in neighbors[mid]:
        #            #neighborId = mid[:mid.rfind('-')+1]+neighborId
        #            nPair[ocrId_to_retId[neighborId]].append( (bbLoc[mid], bbLoc[neighborId]) )
        #        for mid2 in res['matches'][i+1:]:
        #            size = compareSize(bbSize[mid],bbSize[mid2])
        #            sizes.append(size)
        #    for nId, pairs in nPair.items():
        #        for i,(from1,to1) in enumerate(pairs):
        #            for from2,to2 in pairs[i+1:]:
        #                locs.append( compareLoc(from1,to1,from2,to2) )
        #print('sizes mean: {}, std: {}'.format(np.mean(sizes),np.std(sizes)))
        #print('locs mean: {}, std: {}'.format(np.mean(locs),np.std(locs)))

        #check for over-merge errors
        #median_matched = np.median(num_matched)
        for id,res in ocr_matched.items():
            #assert(len(res['matches'])<=median_matched)
            assert(len(res['matches'])<=len(inGroup))


                
        all_ocr_matched.update(ocr_matched)
        all_ocr_res.update(ocr_res)


    all_ocr_matched = [m for m in all_ocr_matched.values() if m['text']]
    with open(outfile,'w') as f:
        json.dump(all_ocr_matched,f,indent=4)
    print('There are {} results needing checked/corrected/'.format(len(all_ocr_matched)))
    with open('./all_ocr.json','w') as f:
        json.dump(all_ocr_res,f,indent=4)
