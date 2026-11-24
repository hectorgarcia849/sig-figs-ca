"""Extractors: download source files exactly as published and record what was
downloaded. They never open or change the files; that is the transformers' job.

One module per source, plus two they share:
    statcan    Statistics Canada tables
    elections  Elections Canada files (riding boundaries, election results)
    files      what every extractor shares: saving downloads, storing releases
    run        runs every source: what "pst extract" calls
"""
