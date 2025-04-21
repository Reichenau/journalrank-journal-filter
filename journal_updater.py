import pandas as pd
import requests
from bs4 import BeautifulSoup 
import os
import concurrent.futures
import pickle
import tempfile
import io
import sys

JOURNALS_URL = "https://journalrank.rcsi.science/ru/record-sources/"
THREADS = 32
OUTPUT_FILENAME = "vak_rsci_journals.xlsx"  
CACHE_DIR = "cache"

if not os.path.exists(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
    except Exception:
        CACHE_DIR = tempfile.gettempdir()

JOURNALS_CACHE_FILE = os.path.join(CACHE_DIR, "journals_cache.pkl")


class SilentOutput:
    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def __enter__(self):
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


def download_page(url, params=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            return response.text
        return None
    except Exception:
        return None


def parse_journals(html):
    soup = BeautifulSoup(html, 'html.parser')
    journals_on_page = soup.select('.list-group-item')
    
    if not journals_on_page:
        return [], 0
    
    total_pages = 1
    pagination = soup.select('.pagination .page-item .page-link')
    if pagination:
        try:
            page_numbers = []
            for page in pagination:
                text = page.text.strip()
                if text.isdigit():
                    page_numbers.append(int(text))
            if page_numbers:
                total_pages = max(page_numbers)
        except Exception:
            pass
    
    journals_list = []
    
    for element in journals_on_page:
        title_element = element.select_one('.tx-uppercase')
        if not title_element:
            continue
        
        title = title_element.text.strip()
        
        link = None
        if title_element.name == 'a':
            link = title_element.get('href')
        else:
            links = element.select('a')
            for a_link in links:
                href = a_link.get('href')
                if href and ('/record/' in href or '/journal/' in href):
                    link = href
                    break
        
        if link:
            if link.startswith('/'):
                link = "https://journalrank.rcsi.science" + link
            elif not link.startswith('http'):
                link = "https://journalrank.rcsi.science/" + link
        
        issn_elements = element.select('.tx-dark')
        issn_list = []
        if issn_elements:
            for issn in issn_elements:
                issn_list.append(issn.text.strip())
        issn = ", ".join(issn_list) if issn_list else "Н/Д"
        
        publisher_element = element.select_one('.tx-gray-500')
        publisher = "Н/Д"
        if publisher_element:
            publisher = publisher_element.text.strip()
        
        info_dict = {
            'Название': title,
            'ISSN': issn,
            'Ссылка': link,
            'Издатель': publisher
        }
        
        journals_list.append(info_dict)
    
    return journals_list, total_pages


def load_page(page_num, url, params):
    params_copy = params.copy()
    params_copy["page"] = page_num
    
    html = download_page(url, params_copy)
    if not html:
        return []
    
    journals, _ = parse_journals(html)
    return journals


def load_all_journals(params, journal_type):
    all_journals = []
    
    first_page = download_page(JOURNALS_URL, params)
    if not first_page:
        return []
    
    journals_on_first_page, total_pages = parse_journals(first_page)
    all_journals.extend(journals_on_first_page)
    
    if total_pages <= 1:
        return all_journals
    
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=THREADS
    ) as executor:
        tasks = {}
        for page_number in range(2, total_pages + 1):
            task = executor.submit(
                load_page, page_number, JOURNALS_URL, params
            )
            tasks[task] = page_number
        
        for task in concurrent.futures.as_completed(tasks):
            try:
                journals_on_page = task.result()
                all_journals.extend(journals_on_page)
            except Exception:
                pass
    
    return all_journals


def get_journal_level(url):
    if not url:
        return "Н/Д"
    
    html = download_page(url)
    if not html:
        return "Н/Д"
    
    soup = BeautifulSoup(html, 'html.parser')
    
    level_element = soup.select_one('.level-circle.level-value')
    if level_element:
        level_text = level_element.text.strip()
        if level_text.isdigit():
            level = level_text
        else:
            digits = ""
            for char in level_text:
                if char.isdigit():
                    digits += char
            if digits:
                level = digits
            else:
                level = "Н/Д"
    else:
        found = False
        for element in soup.select('[class*="level"]'):
            text = element.text.strip()
            digits = ""
            for char in text:
                if char.isdigit():
                    digits += char
            if digits:
                level = digits
                found = True
                break
        
        if not found:
            level = "Н/Д"
    
    return level


def update_journals():
    with SilentOutput():
        vak_params = {
            "adv": "true",
            "vak": "true",
            "per_page": 100
        }
        
        rsci_params = {
            "adv": "true",
            "rs": "true",
            "per_page": 100
        }
        
        if os.path.exists(JOURNALS_CACHE_FILE):
            try:
                with open(JOURNALS_CACHE_FILE, "rb") as f:
                    cache = pickle.load(f)
                    vak_journals = cache.get("vak", [])
                    rsci_journals = cache.get("rsci", [])
                    if vak_journals and rsci_journals:
                        pass
                    else:
                        vak_journals = load_all_journals(
                            vak_params, "журналов ВАК"
                        )
                        rsci_journals = load_all_journals(
                            rsci_params, "журналов RSCI"
                        )
                        
                        cache = {"vak": vak_journals, "rsci": rsci_journals}
                        with open(JOURNALS_CACHE_FILE, "wb") as f:
                            pickle.dump(cache, f)
            except Exception:
                vak_journals = load_all_journals(vak_params, "журналов ВАК")
                rsci_journals = load_all_journals(rsci_params, "журналов RSCI")
                
                cache = {"vak": vak_journals, "rsci": rsci_journals}
                try:
                    with open(JOURNALS_CACHE_FILE, "wb") as f:
                        pickle.dump(cache, f)
                except Exception:
                    pass
        else:
            vak_journals = load_all_journals(vak_params, "журналов ВАК")
            rsci_journals = load_all_journals(rsci_params, "журналов RSCI")
            
            cache = {"vak": vak_journals, "rsci": rsci_journals}
            try:
                with open(JOURNALS_CACHE_FILE, "wb") as f:
                    pickle.dump(cache, f)
            except Exception:
                pass
        
        issn_rsci_dict = {}
        for journal in rsci_journals:
            issn_list = journal["ISSN"].split(", ")
            for issn in issn_list:
                if issn != "Н/Д" and issn.strip():
                    issn_rsci_dict[issn.strip()] = journal["Название"]
        
        for journal in vak_journals:
            in_rsci = False
            issn_list = journal["ISSN"].split(", ")
            
            for issn in issn_list:
                issn_clean = issn.strip()
                if issn_clean in issn_rsci_dict:
                    in_rsci = True
                    break
            
            journal["В RSCI"] = "Да" if in_rsci else "Нет"
        
        journals_with_links = []
        for journal in vak_journals:
            if journal.get("Ссылка"):
                journals_with_links.append(journal)
        
        processed = 0
        
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=THREADS
        ) as executor:
            level_tasks = {}
            for journal in journals_with_links:
                task = executor.submit(get_journal_level, journal["Ссылка"])
                level_tasks[task] = journal
            
            for task in concurrent.futures.as_completed(level_tasks):
                journal = level_tasks[task]
                try:
                    level = task.result()
                    journal["Уровень"] = level
                    processed += 1
                except Exception:
                    journal["Уровень"] = "Н/Д"
        
        for journal in vak_journals:
            if "Уровень" not in journal:
                journal["Уровень"] = "Н/Д"
        
        df = pd.DataFrame(vak_journals)
        
        df = df.sort_values(
            by=["В RSCI", "Уровень", "Название"],
            ascending=[False, False, True]
        )
        
        try:
            df.to_excel(OUTPUT_FILENAME, index=False)
            return OUTPUT_FILENAME
        except Exception:
            alt_filename = "vak_rsci_journals_alt.xlsx"
            try:
                df.to_excel(alt_filename, index=False)
                return alt_filename
            except Exception:
                return None
    
    return OUTPUT_FILENAME 