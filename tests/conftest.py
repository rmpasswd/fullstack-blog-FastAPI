#  Plan:
# import all the env values early, then import the packages
# Conduct all the tests  in a session, rather than in a function
# make the async enginer, build the tables in Base model, yield to perform all the actual tests, then drop the tables.



import os

from collections.abc import AsyncGenerator

os.environ["DATABASE_URL"] = ()