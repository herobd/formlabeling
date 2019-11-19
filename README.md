TODO

Need to revisit these groups to split multiline BBs to be muliple BBs: `10, 100, 101_1, 102_1, 104, 104_1, 105, 105_1, 106, 10_1, 11`

# Forms project labeling tools
These tools are for annotating form images. They are designed to operate on the same set of files using file locks to prevent stepping on eachothers toes.

The tools are build on matplotlib. Use the left mouse to interact with the matplotlib GUI, use the right mouse button to annotate. Saving is done automatically when the GUI closes (ESC).

## labelKeys.py

Usage: `python labelKeys.py directory-of-image-groups [start-at-group] [C/A/a/D]`

* `C`: checking/review labeled images
* `A`: do all images (in case `USE_SIMPLE` is set)
* `a`: run autochecking, just runs heuristic rules over labled images (see checker.py)
* `D`: double-check, flag to allow additional review over checked images

This creates the template for each form type/group. If no starting group is given it automatically goes to the next group without a template.

## labelAll.py

Usage: `python labelAll.py directory-of-image-groups [start-at-group] [start-at-image]`

This creates annotations for each image, starting with the annotations provided with the template. If not start group or image is provided it automatically goes to the next image.



## scandata.py

This is an auxilary function for collecting statistics, making global changes, and creating the split

Current split stats:

Without: 71, table: 77, para: 137, (both:52)
trainCountTable:181,    validCountTable:16  testCountTable:15
trainCountPara:320, validCountPara:47   testCountPara:29
trainCountWithout:149,  validCountWithout:17    testCountWithout:14
trainCountTotal:650,    validCountTotal:80  testCountTotal:58
simple train: 53, valid: 10, test: 8
train: 209, valid: 41, test: 35

mix split (does not seperate images by group):
mix train: 1299, valid: 162, test: 162 (images)




## Labeling process

This describes the process we used in labeling the NAF dataset in context of using this to label your own dataset.

We first separated the images into groups based on their form type; one group for each type, the group being defined as the images in the same directory. We did this by first running a clustering algorithm on the images (this wasn't me so I can't tell you the details, other than it wasn't too complicated) and then manually sorting out the results. Having these groups was just to speed up labeling and is unnecessary, especially if you don't have a lot of repetition.

We then created a template for each group using `labelKeys.py`. The script walks through the groups directory and opens the first image in each group for labeling.

`labelAll.py` then walks through each image in each group. It places the template labeling on the image so you can align the template and edit the boxes. `labelAll.py` will also first create the template if one does not exits for a group. It opens the next unfinished image (allowing you to pick up where you left off).
`labelAll.py` has a number of parameters set at the top of the file you'll want to adjust:

* `NUM_PER_GROUP` is how many images to label from each group, it will skip to the next group after this many images are labeled. We adjusted this (started at 10, then 5) but settled at 2 by the end of labeling.
* `NUM_CHECKS` is how many independent reviews you want for each image (if you are reviewing the data with `C` flag).
* `USE_SIMPLE` is a flag I used to reduce the set of images we were labeleing, you should change this to False.
* `doTrans` is a flag to start adding transcriptions to the boxes. It expects the bounding box labeling is already done.

If you want to skip doing groups and templates, I think the easy work around would be to put all your images in one group and make a blank/empty template. Then you should be able to run `labelAll.py` without any modifications.

### Controls for labeling:

I apologize that this is not very well done. It was made for my use and the few people I had helping me label the data.

All labeling is done with right clicks. Left clicks can then be used for the matplitlib navigation (zoom, pan, etc).
When you first begin editing an image's label, you will be asked to mark corner points.  First it asks you to mark (right click) where the corners should be (in case of torn, bent corners). These corners are used to do an initial alignment with the template. It then asks for actual corner locations, you can skip this by simply pressing ENTER again.
The colored panel on the right shows both controls and the current mode (magenta box around one of the boxes).

If you are using a template, you'll see that the template will almost never perfectly align to the new image. You have some tools to adjust all the boxes at once to better align the template:

* Arrow keys: move, holding SHIFT will make a bigger step
* , / . (< / >): rotate
* - / = (- / +): scale

You can also use M mode to select a subset of boxes (clicking a box selects/deselects, clicking on no box deselects all). The above global manipulations will now apply only to the selected subset.

In you are in any of the first modes (text/label - Partitioned region) clicking and dragging (right button) will create a box. You can also select a box (click on it) and move it (click center, drag), or adjust it's sides (click side, drag). Holding SHIFT will allow the corners to be moved (boxes are stored as quadrilaterals). You can use 'D' to change a boxes type (press D and then the new type). however it can only switch from field type to field type or text type to text type. (text/label - enumeration are text types, field-row are field types) 

You'll see a faint arrow on each box showing the read direction, you can rotate this with J for easier labeling of rotated text.

When a box is selected, creating a box of the opposite type, or clicking a box of the opposite type, will pair them together (green line). If you wish to pair boxes of the same type, the pair mode (F) will allow this (purple line).
The delete mode (G) will delete any pairing line or box you click on.
Ignore the horz link mode.
Some ease of use things:

* A: undo
* S: redo 
* K: create copy of selected box (below). This is useful for repeated lines of text roughly the same size.


Finishing/closing. When done, pressing ENTER saves the labels and opens the next image.If you work is interrupted, you can use ESC to save an incomplete labeling (will be opened again when running `labelAll.py`).You can also use F12 to close without saving, in case you made some big mistake.

### Review

Running `labelAll.py` with the C flag will prompt for a name and the present labeled images that need reviewed/checked (that haven't been checked under that name). We had each image review by 2 labelers for the NAF dataset.

### Coordinating multiple reviewers

You'll notice it creates a `templateX.json.lock` file when your working. This was to allow multiple labelers (working on the same shared drive) preventing them from working on the same group at the same time. If the program crashes, it may not delete the lock file, in which case you'll need to manually remove it.
