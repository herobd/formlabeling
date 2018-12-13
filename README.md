TODO

Need to revisit these groups to split multiline BBs to be muliple BBs: `10, 100, 101_1, 102_1, 104, 104_1, 105, 105_1, 106, 10_1, 11`

# Forms project labeling tools
These tools are for annotating form images. They are designed to operate on the same set of files using file locks to prevent stepping on eachothers toes.

The tools are build on matplotlib. Use the left mouse to interact with the matplotlib GUI, use the right mouse button to annotate. Saving is done automatically when the GUI closes (ESC).

## labelKeys.py

Usage: `python labelKeys.py directory-of-image-groups [start-at-group]`

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
