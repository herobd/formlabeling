from collections import defaultdict

def matchBoxes(template,target):
    #match id and most neighbors
    matches=[]
    templateFields = template['fieldBBs']
    templateTexts = template['textBBs']
    templatePairs = template['pairs']+template['samePairs']
    targetFields = target['fieldBBs']
    targetTexts = target['textBBs']
    targetPairs = target['pairs']+target['samePairs']

    templateNeighbors=defaultdict(set)
    templateNeighborsF=defaultdict(set)
    for pair in templatePairs:
        if pair[1][0]=='t':
            templateNeighbors[pair[0]].add(pair[1])
        elif pair[1][0]=='f':
            templateNeighborsF[pair[0]].add(pair[1])
        else:
            print('error')
            import pdb;pdb.set_trace()
        if pair[0][0]=='t':
            templateNeighbors[pair[1]].add(pair[0])
        elif pair[0][0]=='f':
            templateNeighborsF[pair[1]].add(pair[0])
        else:
            print('error')
            import pdb;pdb.set_trace()

    targetNeighbors=defaultdict(set)
    targetNeighborsF=defaultdict(set)
    for pair in targetPairs:
        if pair[1][0]=='t':
            targetNeighbors[pair[0]].add(pair[1])
        elif pair[1][0]=='f':
            targetNeighborsF[pair[0]].add(pair[1])
        else:
            print('error')
            import pdb;pdb.set_trace()
        if pair[0][0]=='t':
            targetNeighbors[pair[1]].add(pair[0])
        elif pair[0][0]=='f':
            targetNeighborsF[pair[1]].add(pair[0])
        else:
            print('error')
            import pdb;pdb.set_trace()

    targetById = {}
    for textBB in targetTexts:
        targetById[textBB['id']] = textBB

    for textBB in templateTexts:
        tempId = textBB['id']

        if tempId in targetById:
            a = templateNeighbors[tempId]
            b = targetNeighbors[tempId]
            if len(a)>0 or len(b)>0:
                iou = len(a.intersection(b))/len(b.union(a))
            else:
                iou = 1

            a = templateNeighborsF[tempId]
            b = targetNeighborsF[tempId]
            if len(a)>0 or len(b)>0:
                iouFields = len(a.intersection(b))/len(b.union(a))
            else:
                iouFields = 1

            if iou>=0.80 and iouFields>0.1:
                matches.append((tempId,tempId))
    targetByIdF = {}
    for fieldBB in targetFields:
        targetByIdF[fieldBB['id']] = fieldBB

    for fieldBB in templateFields:
        tempId = fieldBB['id']

        if tempId in targetById:
            a = templateNeighborsF[tempId]
            b = targetNeighborsF[tempId]
            if len(a)>0 or len(b)>0:
                iou = len(a.intersection(b))/len(b.union(a))
            else:
                iou = 1

            a = templateNeighbors[tempId]
            b = targetNeighbors[tempId]
            if len(a)>0 or len(b)>0:
                iouFields = len(a.intersection(b))/len(b.union(a))
            else:
                iouFields = 1

            if iou>=0.80 and iouFields>0.1:
                matches.append((tempId,tempId))
    return matches

