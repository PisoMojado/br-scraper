from bs4 import BeautifulSoup,Comment
import urllib.request
from urllib.error import HTTPError

class BRScraper:
    def __init__(self, server_url="http://www.baseball-reference.com/"):
        self.server_url = server_url

    def parse_tables(self, resource, table_ids=None, verbose=False):
        """
        Given a resource on the baseball-reference server (should consist of
        the url after the hostname and slash), returns a dictionary keyed on
        table id containing arrays of data dictionaries keyed on the header
        columns. table_ids is a string or array of strings that can optionally
        be used to filter out which stats tables to return.
        """
        try:
            soup = self.__try_open_soup(resource)
            tables = soup(is_parseable_table)
        except HTTPError as e:
            tables = []

        return self.__build_dataset_from_table(tables, table_ids, verbose)

    def parse_splits_tables(self, resource, verbose=False):
        """
        The split tables require, ahem, special handling, which this function achieves.
        """
        def is_navigable_split_div(tag):
            return tag.name == "div" and tag.has_attr("class") and "table_wrapper" in tag["class"]

        def contains_table_heading(tag):
            return tag.name == 'div' and tag.has_attr("class") and "section_heading" in tag["class"]

        def is_table_outer_container(tag):
            return tag.name == 'div' and tag.has_attr('class') and "table_outer_container" in tag["class"]

        def is_table_container(tag):
            return tag.name == 'div' and tag.has_attr('class') and "table_container" in tag["class"]
        try:
            soup = self.__try_open_soup(resource)
            table_wrappers = soup(is_navigable_split_div)
        except Exception as e:
            print(e)
            table_wrappers = []

        data = {}
        keys = {}

        # Read through each table, read headers as dictionary keys
        for table_wrapper in table_wrappers:
            if verbose: print ("Processing split table" + table_wrapper["id"])
            split_table_name = table_wrapper.find(contains_table_heading).find("h2")
            comment = table_wrapper.find(text=lambda t: isinstance(t, Comment))
            comment_element = BeautifulSoup(comment,"html.parser").find(is_table_outer_container)
            table = comment_element.find(is_table_container).find(is_parseable_table)
            dataset = self.__build_dataset_from_table([table])
            keys.update((key, split_table_name.string) for key in dataset.keys())
            data.update(dataset)
        data['table_names'] = keys
        return data

    def __build_dataset_from_table(self, tables, table_ids=None, verbose=False):
        def is_parseable_row(tag):
            if not tag.name == "tr": return False
            if not tag.has_attr("class"): return True  # permissive
            return "league_average_table" not in tag["class"] and "stat_total" not in tag["class"]

        data = {}

        if isinstance(table_ids, str): table_ids = [table_ids]
        # Read through each table, read headers as dictionary keys
        for table in tables:
            if table_ids != None and table["id"] not in table_ids: continue
            if verbose: print ("Processing table " + table["id"])
            data[table["id"]] = []
            headers = table.find("thead").find_all("th")
            header_names = []
            for header in headers:
                if header.string == None:
                    base_header_name = u""
                else: base_header_name = header.string.strip()
                if base_header_name in header_names:
                    i = 1
                    header_name = base_header_name + "_" + str(i)
                    while header_name in header_names:
                        i += 1
                        header_name = base_header_name + "_" + str(i)
                    if verbose:
                        if base_header_name == "":
                            print ("Empty header relabeled as %s" % header_name)
                        else:
                            print ("Header %s relabeled as %s" % (base_header_name, header_name))
                else:
                    header_name = base_header_name
                header_names.append(header_name)
            rows = table.find("tbody").find_all(is_parseable_row)
            for row in rows:
                entries = row.find_all(["td","th"])
                entry_data = []
                for entry in entries:
                    if (entry.text == None) or (entry.text == u""):
                        entry_data.append(u"");
                    else:
                        entry_data.append(entry.text.strip())
                if len(entry_data) > 0:
                    data[table["id"]].append(dict(zip(header_names, entry_data)))
        return data

    def __try_open_soup(self, resource):
        # Added this to attempt to fetch data from bref 3 times. Workaround to HTTP Error 502 that would
        # randomly crop up. Looking online it seems that the issue was possibly due to a random load spike
        # from bref's side that would stop us from connecting and crash the DataGenerator.py function from 
        # running
        attempts = 0
        while attempts < 3:
            try:
                return BeautifulSoup(urllib.request.urlopen(self.server_url + resource), "html.parser")
            except HTTPError as e:
                attempts += 1
                print("HTTP Error {}".format(e.args))
                raise e

def is_parseable_table(tag):
    if not tag.has_attr("class"): return False
    return tag.name == "table" and "stats_table" in tag["class"] and "sortable" in tag["class"]

