""" Scrape all of the tunes from tunearch.org, storing their metadata and abc notation """

from urllib import parse
import os
import json
import itertools
import requests
from lxml import html
from unidecode import unidecode

TUNE_FILE_FORMAT = "tunes-{}.json"
# pylint: disable=line-too-long
ORIGINAL_SCRAPE_URL = "http://tunearch.org/w/index.php?title=Special%3AAsk&q=%5B%5BCategory%3ATune%5D%5D&po=%3FIs+also+known+as%3DAlso+known+as%0D%0A%3FTheme+code+index%3DTheme+Code+Index%0D%0A%3FWas+composed+by%3DArranger%2FComposer%0D%0A%3FIt+comes+from%3DCountry%0D%0A%3FHas+genre%3DGenre%0D%0A%3FHas+rhythm%3DRhythm%0D%0A%3FIs+in+the+key+of%3DKey%0D%0A%3FHas+historical+geographical+allegiances%3DHistory%0D%0A&eq=yes&p%5Bformat%5D=json&sort%5B0%5D=Theme_code_index&order%5B0%5D=ASC&sort_num=&order_num=ASC&p%5Blimit%5D=20&p%5Boffset%5D=20&p%5Blink%5D=all&p%5Bsort%5D=Theme_code_index&p%5Bheaders%5D=show&p%5Bmainlabel%5D=Tune&p%5Bintro%5D=&p%5Boutro%5D=&p%5Bsearchlabel%5D=JSON&p%5Bdefault%5D=&eq=yes"
# pylint: enable=line-too-long

def scrape_abc_notation(url):
    """ Gets the abc notation from the provided tunearch tune url """
    response = requests.get(url)
    if response.status_code is not 200:
        response.raise_for_status()

    tree = html.fromstring(response.content)
    content = tree.xpath('//pre/text()')
    # just take the first pre element contents for now
    if len(content) > 0:
        return unidecode(content[0])
    else:
        return "No Score"

def format_tune_entry(tune):
    """ Format a tune entry for archival """
    abc_transcription = scrape_abc_notation(tune['fullurl'])
    print(".", end='', flush=True)
    return {
        'name': tune['fulltext'],
        'url': tune['fullurl'],
        'abc': abc_transcription
    }

def request_tunes_by_theme_code(code, page, num_tunes):
    """ We seem to be throttled by the tune archive """
    url_template = ("http://tunearch.org/w/api.php?action=ask" +
                    "&query=[[Category:Tune]]|[[Theme code index::~{}*]]" +
                    "|offset={}|limit={}&format=json")
    target_url = url_template.format(code, page * num_tunes, num_tunes)
    response = requests.get(target_url)
    if response.status_code is not 200:
        response.raise_for_status()

    tunes_dict = response.json()['query']['results']

    return [format_tune_entry(tune) for tune in tunes_dict.values()]

def request_tunes(page, num_tunes=100):
    """ Download a page of tunes from tunearch as json """
    args = {
        'order_num': ['ASC'],
        'title': ['Special:Ask'],
        'sort[0]': ['Theme_code_index'],
        'order[0]': ['ASC'],
        'p[format]': ['json'],
        'q': ['[[Category:Tune]]'],
        'p[offset]': [str(page*num_tunes)],
        'p[searchlabel]': ['JSON'],
        'eq': ['yes'],
        'p[limit]': [str(num_tunes)]
    }
    query = parse.urlencode(args, doseq=True)
    target_url = "http://tunearch.org/w/index.php?{}".format(query)
    print("Requesting: {}".format(target_url))
    response = requests.get(target_url)
    if response.status_code is not 200:
        response.raise_for_status()

    tunes_dict = response.json()['results']

    return [format_tune_entry(tune) for tune in tunes_dict.values()]

def transcription_is_empty(abc):
    """ Check if an abc transcription is empty """
    return (("No Score" in abc) or
            ("REPLACE THIS LINE WITH THE ABC CODE OF THIS TUNE") in abc)

def request_all_tunes_by_code():
    """ Get all tunes in the tune archive, theme code by theme code :( """
    tunes_per_page = 10
    product = itertools.product(range(1, 8), repeat=4)
    for combo in product:
        code = ''.join([str(digit) for digit in combo])
        tune_file = TUNE_FILE_FORMAT.format(code)
        if os.path.isfile(tune_file):
            continue
        print("REQUESTING TUNES WITH THEME CODES BEGINNING IN {}".format(code))
        all_tunes = []
        for page in range(10):
            page_of_tunes = request_tunes_by_theme_code(code, page, tunes_per_page)
            filtered_page = [tune for tune in page_of_tunes
                             if not transcription_is_empty(tune['abc'])]
            all_tunes.extend(filtered_page)
            print("\nGot {} more tunes, ".format(len(filtered_page)) +
                  "writing {} tunes to file...".format(len(all_tunes)),
                  end='', flush=True)
            with open(tune_file, "w") as outfile:
                outfile.writelines(json.dumps(all_tunes))
            print("  Finished.")
            if len(page_of_tunes) < tunes_per_page:
                print("Presuming that page of {} tunes ".format(len(page_of_tunes)) +
                      "is the last page, quitting.")
                break
            page += 1

def request_all_tunes():
    """ Get all tunes in the tune archive, page by page """
    all_tunes = []
    page = 0
    tunes_per_page = 10
    while True:
        page_of_tunes = request_tunes(page, tunes_per_page)
        filtered_page = [tune for tune in page_of_tunes
                         if not transcription_is_empty(tune['abc'])]
        all_tunes.extend(filtered_page)
        print("\nGot {} more tunes, ".format(len(filtered_page)) +
              "writing {} tunes to file...".format(len(all_tunes)),
              end='', flush=True)
        with open("tunes.json", "w") as outfile:
            outfile.writelines(json.dumps(all_tunes))
        print("  Finished.")
        if len(page_of_tunes) < tunes_per_page:
            print("Presuming that page of {} tunes ".format(len(page_of_tunes)) +
                  "is the last page, quitting.")
            break
        page += 1

def main():
    """ The main executable """
    request_all_tunes_by_code()

if __name__ == '__main__':
    main()
