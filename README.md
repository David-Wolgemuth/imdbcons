###Dependencies

Requires **Python 2**.
*Pillow* and *imdb-pie* must be installed.  Both available with pip install.

###Usage

Script can be used to set icon for single folder or icons for all sub-folders within main folder.

-m : Set icons for all sub-folders within main movie folder

`python imdbcons.py -m path/to/movies`

-s :	Set icon for folder of single movie

`python imdbcons.py -s path/to/Inception`

-id : Set icon for folder with a vague title using IMDB id

`python imdbcons.py -id tt0060153 path/to/Batman`
