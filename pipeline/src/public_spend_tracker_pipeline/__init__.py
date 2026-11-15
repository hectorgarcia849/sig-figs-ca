"""The data pipeline: downloads public spending data, cleans it, and builds the
database the website and API read from.

Steps, in order:
    extract    download source files exactly as published (extract/)
    transform  clean and reshape them into our own tables (coming next)
    build      write the single database file the site serves (coming next)
"""
