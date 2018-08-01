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

