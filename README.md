# auto render queue
a simple, lightweight render queuing tool/batch renderer for Blender, that acts as a wrapper around the Blender CLI.

## philosophy
alas, most solutions for doing something as rudimentary as this are either paid, or extremely convoluted. this is a simple solution that allows you to queue up a bunch of renders, and then render them in the background. human greed has once again done the thing it does best, and made a simple solution extremely out of reach for the average user - so, this is the simple solution after spending 3 hours or so that hopefully will save you some time.

## how to use?
1. go to [releases](https://github.com/sudotman/BlenderOpenRenderQueue/releases) and download the latest version
2. run the executable
3. select the `blender.exe` executable if not automatically found
4. add blend files to the queue
5. click 'start render'

or

1. clone the repository
2. run `pip install -r requirements.txt`
3. run `python render_queue.py`
4. (optional) run `pyinstaller --onefile render_queue.py` to build an executable

## contributing
if you have any suggestions, please open an issue or submit a pull request.

## license
this project is licensed under the MIT license. see the LICENSE file for details.

## how it looks
the below is the UI:

![UI](https://raw.githubusercontent.com/sudotman/sudotman/refs/heads/main/demos/smallerprojects/demo.png)