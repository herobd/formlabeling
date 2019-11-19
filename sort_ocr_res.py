
import cv2
import json, re
import sys, random
import numpy as np


if len(sys.argv)<8:
    print('usage: python {} resultFile splitFile lexiconFile testvalidOut accurateOut mostlyaccurateOut inaccurateOut'.format(sys.argv[0]))
    exit()

resultFile = sys.argv[1]


with open(resultFile) as f:
    results = json.load(f)

splitFile = sys.argv[2]
with open(splitFile) as f:
    splits = json.load(f)

lexiconFile = sys.argv[3]
with open(lexiconFile) as f:
    lexicon = f.readlines()
    lexicon = set([w.strip() for w in lexicon])


testvalidOut = sys.argv[4]
accurateOut = sys.argv[5]
mostlyaccurateOut = sys.argv[6]
inaccurateOut = sys.argv[7]

#seperate into train and text/valid

#auto check accuracy of train side with comparison to lexicon words
#split train into accurate and inaccurate lists (inaccurate list to provide list to sample from for labeling)


random.shuffle(results)

test_valid_results=[]
accurate_train_results=[]
mostlyaccurate_train_results=[]
inaccurate_train_results=[]

for res in results:
    group = res['matches'][0][:res['matches'][0].find('-')]
    if group in splits['test'] or group in splits['valid']:
        test_valid_results.append(res)
    else:
        pred = res['pred'].lower()
        w_only = re.sub(r'[^\w ]','',pred)
        w_only = re.sub(r'\d','',w_only)
        w_only = re.sub(r' \+',' ',w_only)

        words = w_only.strip().split(' ')

        right = 0
        for word in words:
            if word in lexicon:
                right+=1
        acc = right/len(words)
        if acc>0.96:
            accurate_train_results.append(res)
        elif acc>0.7:
            mostlyaccurate_train_results.append(res)
        else:
            print('{} : {}'.format(w_only,acc))
            inaccurate_train_results.append(res)


print('test+valid: {}, accurate: {}, mostly accurate: {}, inaccurate: {}'.format(len(test_valid_results),len(accurate_train_results),len(mostlyaccurate_train_results),len(inaccurate_train_results)))

with open(testvalidOut,'w') as f:
    json.dump(test_valid_results,f)
with open(accurateOut,'w') as f:
    json.dump(accurate_train_results,f)
with open(mostlyaccurateOut,'w') as f:
    json.dump(mostlyaccurate_train_results,f)
with open(inaccurateOut,'w') as f:
    json.dump(inaccurate_train_results,f)
