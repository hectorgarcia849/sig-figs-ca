"""Extractors: download source files exactly as published and record what was
downloaded. They never open or change the files; that is the transformers' job.

One module per source, plus two they share:
    statcan    Statistics Canada tables
    published  files at a fixed address: Elections Canada's riding boundaries and
               results, Natural Resources Canada's land outline
    files      what every extractor shares: saving downloads, storing releases
    run        runs every source: what "pst extract" calls
"""
