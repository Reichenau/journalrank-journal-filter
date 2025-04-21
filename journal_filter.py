import os
import pandas as pd

OUTPUT_FILENAME = "filtered_journals.xlsx"

def filter_journals_by_criteria(whitelist_levels, in_rsci):
    """
    Фильтрует журналы по заданным критериям
    
    Args:
        whitelist_levels (list): Список уровней белого списка для фильтрации
        in_rsci (bool): Фильтр по включению в RSCI (True - включенные, 
                       False - не включенные, None - все)
        
    Returns:
        str: Имя файла с отфильтрованными журналами или None в случае ошибки
    """
    source_file1 = "vak_rsci_journals.xlsx"
    source_file2 = "vak_rsci_journals_alt.xlsx"
    if not os.path.exists(source_file1) and not os.path.exists(source_file2):
        return None
    
    source_filename = source_file1
    if not os.path.exists(source_filename):
        source_filename = source_file2
    
    df = pd.read_excel(source_filename)
    filtered_df = df.copy()
    
    if whitelist_levels:
        mask = filtered_df["Уровень"].isin(whitelist_levels)
        filtered_df = filtered_df[mask]
    
    if in_rsci is not None:
        filter_value = "Да" if in_rsci else "Нет"
        mask = filtered_df["В RSCI"] == filter_value
        filtered_df = filtered_df[mask]
    
    try:
        filtered_df.to_excel(OUTPUT_FILENAME, index=False)
        return OUTPUT_FILENAME
    except Exception:
        return None 