import time
from assets.parser import Parse
import config

parser = Parse()
acticles = parser.search(config.keywords_for_search)
print(acticles)
#builder = parser.run_page_builder(acticles)