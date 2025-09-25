import cProfile
import main
import pstats
from pstats import SortKey

if input("Run game?\n>").lower() == "y":
    cProfile.run('main.run()', 'restats')
p = pstats.Stats('restats')

#p.print_stats()
p.sort_stats("cumtime").print_stats(100)
