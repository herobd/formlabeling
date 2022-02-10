import cv2
import json
import sys, random, os
import numpy as np
import readline
import pyperclip
#import gtk
import timeit

if len(sys.argv)>2:
    resultFile = sys.argv[1]
    outFile = sys.argv[2]
else:
    resultFile = 'ocr_train_inaccurate.json'
    outFile = 'corrected_train_inaccurate.json'
if len(sys.argv)>3:
    remove = abs(int(sys.argv[3]))
else:
    remove = None

save_every=20

with open(resultFile) as f:
    results = json.load(f)

if os.path.exists(outFile):
    with open(outFile) as f:
        out = json.load(f)
    if remove is not None:
        out = out[:-remove]
        print(' removed last {}'.format(remove))
    undone=[]
    for r in results:
        done=False
        for o in out:
            if r['image']==o['image']:
                done=True
                break
        if not done:
            undone.append(r)
else:
    out = []
    undone = results

first=True
times=[]
#clipboard = gtk.clipboard_get()
for i,r in enumerate(undone):
    print('{}  {}/{} \t\t[qqq: quit, UNDO:redo last, FULL: show document]'.format(r['image'],i+len(out),len(undone)+len(out)))
    print(': {}'.format(r['pred']))
    im = cv2.imread(r['image'])
    cv2.imshow('im',im)

    if first:
        print('press key...')
        key = cv2.waitKey()
        first=False
    else:
        key = cv2.waitKey(1)
    #readline.insert_text(r['pred'])
    #readline.redisplay()
    pyperclip.copy(r['pred'])
    #clipboard.set_text(r['pred'])
    #clipboard.store()
    tic=timeit.default_timer()
    trans = input('> ')
    toc=timeit.default_timer()
    #print(key)
    if key==27 or trans=='qqq':
        break
    times.append(toc-tic)
    if trans=='UNDO':
        last = out[-1]
        im2 = cv2.imread(last['image'])
        cv2.imshow('im2',im2)
        trans2 = input('2> ')
        last['gt'] = trans2

        trans = input('> ')
    elif trans=='FULL':
        iii = r['matches'][0]
        group,image,line = iii.split('-')
        im2 = cv2.imread(os.path.join('../data/forms/groups',group,'{}.jpg'.format(image)))
        cv2.imshow('im2',im2)
        trans = input('> ')

    r['gt'] = trans

    out.append(r)

    if (i-1)%save_every==0:
        with open(outFile,'w') as f:
            json.dump(out,f)
        print('saved!')
    
with open(outFile,'w') as f:
    json.dump(out,f,indent=4)
print('saved!')
if key!=27 and trans!='qqq':
    print('done!')
else:
    print('closed')

print('mean time: {}'.format(np.mean(times)))
