import pandas as pd
import dask.dataframe as dd
import multiprocessing
from fuzzywuzzy import fuzz
from dask.diagnostics import ProgressBar
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

def load_data(filepath):
    """
    Load data from the specified file path.
    
    Parameters:
        filepath (str): Path to the file to be loaded.
        
    Returns:
        pd.DataFrame: Loaded data.
    """
    try:
        df = pd.read_csv(filepath)
        logging.info(f"Data loaded successfully from {filepath}.")
        return df
    except FileNotFoundError:
        logging.error(f"File not found: {filepath}.")
        raise
    except pd.errors.EmptyDataError:
        logging.error("No data in file: {filepath}.")
        raise
    except pd.errors.ParserError:
        logging.error(f"Error parsing file: {filepath}.")
        raise

def validate_parameters(df, id_col, blocking_col, additional_cols, threshold):
    """
    Validate parameters against the loaded data.
    
    Parameters:
        df (pd.DataFrame): Loaded data.
        id_col (str): Name of the ID column.
        blocking_col (str): Name of the blocking column.
        additional_cols (list): List of additional columns.
        threshold (int): Fuzzy matching threshold.
        
    Raises:
        ValueError: If validation fails.
    """
    # Validate column names
    for col in [id_col, blocking_col] + additional_cols:
        if col not in df.columns:
            logging.error(f"Column {col} not found in data.")
            raise ValueError(f"Column {col} not found in data.")
    
    # Validate threshold
    if not (0 <= threshold <= 100):
        logging.error(f"Invalid threshold: {threshold}. Must be between 0 and 100.")
        raise ValueError(f"Invalid threshold: {threshold}. Must be between 0 and 100.")
    
    logging.info("Parameters validated successfully.")

def get_column_names(id_col, blocking_col, additional_cols, show_full_name=True):
    """
    Generate column names for the output DataFrame based on specified ID and additional columns.
    
    Parameters:
        id_col (str): Name of the ID column.
        blocking_col (str): Name of the blocking column.
        additional_cols (list): List of additional columns.
        show_full_name (bool, optional): Whether to show full names in the result. Defaults to True.
        
    Returns:
        list: List of column names.
    """
    col_names = ['URL_ID_1', f'{id_col}_1', f'{blocking_col}_1', f'{id_col}_2', f'{blocking_col}_2', f'Score_{additional_cols[0]}']
    col_names.extend([f'Score_{col}' for col in additional_cols[1:]])
    
    if not show_full_name:
        col_names.remove(f'{blocking_col}_1')
        col_names.remove(f'{blocking_col}_2')
    
    return col_names

def find_duplicates(df, config):
    """
    Find duplicates in the data based on fuzzy matching of specified columns.
    
    Parameters:
        df (pd.DataFrame): Data in which to find duplicates.
        config (dict): Configuration dictionary containing parameters.
        
    Returns:
        pd.DataFrame: DataFrame containing detected duplicates.
    """
    duplicates = []
    
    # Extracting parameters from the config dictionary
    blocking_col = config['blocking_col']
    id_col = config['id_col']
    threshold = config.get('threshold')
    show_full_name = config.get('show_full_name')
    url = config.get('url')
    additional_cols = config.get('additional_cols', [])
    
    col_names = get_column_names(id_col, blocking_col, additional_cols, show_full_name)
    
    for _, group in df.groupby(blocking_col):
        for i in range(len(group)):
            for j in range(i+1, len(group)):
                score_1 = fuzz.ratio(group[additional_cols[0]].iloc[i], group[additional_cols[0]].iloc[j])
                
                if score_1 >= threshold:
                    scores_rest = [
                        fuzz.ratio(group[col].iloc[i], group[col].iloc[j])
                        for col in additional_cols[1:]
                    ]
                    hyperlink_formula = f'=HYPERLINK("{url}{group[id_col].iloc[i]}?tab=Manage+Cluster+Details")'
                    
                    # Conditionally populating duplicate_entry based on show_full_name
                    if show_full_name:
                        duplicate_entry = (
                            hyperlink_formula,
                            group[id_col].iloc[i],
                            group[blocking_col].iloc[i],
                            group[id_col].iloc[j],
                            group[blocking_col].iloc[j],
                            score_1,
                            *scores_rest
                        )
                    else:
                        duplicate_entry = (
                            hyperlink_formula,
                            group[id_col].iloc[i],
                            group[id_col].iloc[j],
                            score_1,
                            *scores_rest
                        )

                    duplicates.append(duplicate_entry)
                    
    # Diagnostic print statements
    print("Duplicate Entry Length:", len(duplicates[0]))
    print("Duplicate Entry Values:", duplicates[0])
    print("Column Names Length:", len(col_names))
    print("Column Names Values:", col_names)
    
    # Assertion to ensure lengths match
    assert len(duplicates[0]) == len(col_names), "Data length does not match column length"
    
    return pd.DataFrame(duplicates, columns=col_names)

# Implementing save_data function
def save_data(df, filepath):
    """
    Save data to the specified file path.
    
    Parameters:
        df (pd.DataFrame): Data to be saved.
        filepath (str): Path to the file to be saved.
    """
    try:
        df.to_csv(filepath, index=False)
        logging.info(f"Data saved successfully to {filepath}.")
    except Exception as e:
        logging.error(f"Error saving data to {filepath}: {str(e)}.")
        raise

# Example configuration dictionary
config = {
    "input_filepath": './data/entity_records.csv',
    "output_filepath": './data/entity_analysis_basic.csv',
    "blocking_col": 'Date Of Birth',
    "id_col": 'Entity ID',
    "threshold": 50,
    "show_full_name": False,
    "url": "https://example.com/entities/",
    "additional_cols": ['Full Name', 'Enriched Full Address', 'Source EID']
}

# Example usage
df = load_data(config['input_filepath'])
validate_parameters(df, config['id_col'], config['blocking_col'], config['additional_cols'], config['threshold'])

n_cores = multiprocessing.cpu_count()
ddf = dd.from_pandas(df, npartitions=n_cores)

with ProgressBar():
    col_names = get_column_names(config['id_col'], config['blocking_col'], config['additional_cols'], config['show_full_name'])
    potential_duplicates = ddf.map_partitions(
        find_duplicates, 
        config,
        meta=pd.DataFrame(columns=col_names, dtype='float64')
    ).compute()

save_data(potential_duplicates, config['output_filepath'])
