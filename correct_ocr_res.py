import cv2
import json
import sys, random
import numpy as np
import readline

def printInst():
    print('1: good')
    print('2: slight error')
    print('3: major error')
    print('4: blank')
    print('5: bad image')

resultFile = sys.argv[1]
outFile = sys.argv[2]

save_every=20

with open(resultFile) as f:
    results = json.load(f)
with open(outFile) as f:
    out = json.load(f)

undone=[]
for r in results:
    done=False
    for o in out:
        if r['image']==o['image']:
            done=True
            break
    if not done:
        undone.append(r)

for i,r in enumerate(undone):
    print('{}  {}/{}'.format(r['image'],i+len(out),len(undon)+len(out)))
    print(': {}'.format(r['pred']))
    im = cv2.imread(r['image'])
    cv2.imshow('im',im)

    readline.insert_text(r['pred'])
    trans = input('> ')
    key = cv2.waitKey()
    print(key)

    r['gt'] = trans

    out.append(r)

    if (i-1)%save_every==0:
        with open(outFile,'w') as f:
            json.dump(out,f)


