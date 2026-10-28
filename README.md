# World of Dissonance Wiki

The World of Dissonance doc, as a searchable website: https://world-of-dissonance.github.io/wiki/

Every hour a GitHub Action downloads the doc's public export, rebuilds the pages and redeploys when something changed.
It only reads the doc; nothing here ever writes back to it. To edit the wiki, edit the doc.

Build locally:

    pip install markdown==3.7 pillow
    python build.py --out site
