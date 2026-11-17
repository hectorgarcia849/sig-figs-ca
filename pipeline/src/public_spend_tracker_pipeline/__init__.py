"""The data pipeline: downloads public spending data, cleans it, and builds the
database the website and API read from.

Steps, in order:
    extract    download source files exactly as published (extract/)
    transform  clean and reshape them into our own tables (transform/)
    build      write the single database file the site serves (build/)
    release    approve a build and export its figures for the site (release/)

common/ holds the settings, paths, logging and web connections every step shares.
cli.py is the pst command that runs them.
"""
