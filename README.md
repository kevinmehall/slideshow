Slideshow generator
===================

This is a simple python script that generates a slideshow video from a series of still photos

It takes an input file listing the photo slides, and pipes its output through FFMPEG

Input files are a series of lines encoded in the following format

`/path/to/photo.jpeg[<TAB>Subtitle[<TAB>Panning Options]]

If specified, the panning options are specified as `start_zoom:start_x:start_y:end_zoom:end_x:end_y`

Example: `1:0.5:0.5:0.85:0.4:0.4`

More documentation to come...
