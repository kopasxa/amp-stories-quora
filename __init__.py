import time
from assets.parser import Parse
import config

for query in config.questions:
    parser = Parse(config.initial_query_for_search + query + "&type=question")
    acticles = parser.search(config.keywords_for_search)

    builder = parser.run_page_builder(acticles)
    time.sleep(config.timeout_page_generate)
