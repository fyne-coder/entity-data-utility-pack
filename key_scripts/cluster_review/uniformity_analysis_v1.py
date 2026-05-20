import os
import pandas as pd
import numpy as np
import logging
import concurrent.futures
import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Constants
DATA_DIR = "data"
INPUT_FILENAME = "entity_records.csv"
CLUSTER_DETAILS_FILENAME = "entity_cluster_details.csv"
UNIFORMITY_SCORE_COLUMN = "Avg Uniformity Score"
URL = "https://example.com/entities/"
ID_COLUMN = "Entity ID"

# Setup logging
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.feature_extraction.text", message="The parameter 'token_pattern' will not be used since 'tokenizer' is not None'")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def custom_tokenizer(s):
    """Custom tokenizer that treats single characters as valid tokens."""
    return s.split()

def add_hyperlink_column(df: pd.DataFrame, url: str, id_col: str) -> pd.DataFrame:
    """Add a new hyperlink column to the dataframe."""
    hyperlinks = [f'=HYPERLINK("{url}{df[id_col].iloc[i]}?tab=Manage+Cluster+Details")' for i in range(len(df))]
    df.insert(0, 'Hyperlink', hyperlinks)
    return df

def load_data(data_dir: str, input_filename: str, cluster_details_filename: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        input_df = pd.read_csv(os.path.join(data_dir, input_filename))
        cluster_details_df = pd.read_csv(os.path.join(data_dir, cluster_details_filename), low_memory=False)
        return input_df, cluster_details_df
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")
        raise

def process_row(row, cluster_details_df, ml_columns):
    """Process a single row from input_df and return the result."""
    entity_id = row["Entity ID"]
    cluster = cluster_details_df[cluster_details_df['persistentId'] == entity_id]
    if cluster.empty:
        return None

    result_row = {"Entity ID": entity_id, UNIFORMITY_SCORE_COLUMN: row[UNIFORMITY_SCORE_COLUMN]}
    for col in ml_columns:
        similarity = calculate_similarity_within_cluster(cluster, col)
        result_row[col] = similarity

    return result_row

def calculate_similarity_within_cluster(cluster: pd.DataFrame, column_name: str) -> float:
    texts = cluster[column_name].astype(str).replace({"nan": "", "None": ""}).values
    try:
        vectorizer = TfidfVectorizer(lowercase=True, tokenizer=custom_tokenizer, stop_words=None).fit(texts)
        vectors = vectorizer.transform(texts).toarray()
        similarity_matrix = cosine_similarity(vectors)
        avg_similarity = (similarity_matrix.sum() - np.trace(similarity_matrix)) / (len(cluster) * (len(cluster) - 1))
    except ValueError as e:
        avg_similarity = 0
    return avg_similarity

def main():
    try:
        input_df, cluster_details_df = load_data(DATA_DIR, INPUT_FILENAME, CLUSTER_DETAILS_FILENAME)
        ml_columns = [col for col in cluster_details_df.columns if col.startswith("ml_")]
        
        # Create the lists of arguments for parallel processing
        rows_list = [row for _, row in input_df.iterrows() if row[UNIFORMITY_SCORE_COLUMN] < 1]
        cluster_details_list = [cluster_details_df] * len(rows_list)
        ml_columns_list = [ml_columns] * len(rows_list)
        
        # Parallel processing of rows with a uniformity score < 1
        with concurrent.futures.ProcessPoolExecutor() as executor:
            results_list = list(executor.map(process_row, rows_list, cluster_details_list, ml_columns_list))

        # Filter out any None values from the results
        results_list = [result for result in results_list if result is not None]
        
        results_df = pd.DataFrame(results_list)
        
        # Add hyperlinks
        results_df = add_hyperlink_column(results_df, URL, ID_COLUMN)

        output_filename = os.path.splitext(INPUT_FILENAME)[0] + "_uniformity_analysis.csv"
        output_path = os.path.join(DATA_DIR, output_filename)
        results_df.to_csv(output_path, index=False)
        logging.info(f"Results saved to: {output_path}")

    except Exception as e:
        logging.error(f"Script execution failed: {str(e)}")

if __name__ == "__main__":
    main()
