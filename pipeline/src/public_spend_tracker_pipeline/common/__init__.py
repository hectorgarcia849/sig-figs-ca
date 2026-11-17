"""Shared plumbing every pipeline step uses. Nothing here knows about any one step.

settings     tables and governments we use, folders, connection settings
paths        where every data file lives
logs         logging to the screen and a log file per run
http_client  web connections that retry brief server problems
"""
