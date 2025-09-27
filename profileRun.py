import cProfile
#
import pstats
from pstats import SortKey


name = 'restats_opt'
if input("Run game?\n>").lower() == "y":
    import main
    cProfile.run('main.run()', name)
p = pstats.Stats(name)

#p.print_stats()
p.sort_stats("tottime").print_stats(500)
