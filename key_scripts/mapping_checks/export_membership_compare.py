import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Function to load data from a CSV file efficiently
def load_data(source):
    dtypes = {'entityId': 'category', 'persistentId': 'category'}
    return pd.read_csv(source, usecols=['entityId', 'persistentId'], dtype=dtypes)

# Load the data from two different exports.
df1 = load_data('export_1.csv')
df2 = load_data('export_2.csv')

unique_persistent_ids1 = set(df1['persistentId'].unique())
unique_persistent_ids2 = set(df2['persistentId'].unique())
all_pids = list(unique_persistent_ids1.union(unique_persistent_ids2))

# Function to classify persistentId
def classify_persistent_id(pid):
    in_first = pid in unique_persistent_ids1
    in_second = pid in unique_persistent_ids2
    entities1 = set(df1[df1['persistentId'] == pid]['entityId']) if in_first else set()
    entities2 = set(df2[df2['persistentId'] == pid]['entityId']) if in_second else set()
    
    if in_first and not in_second:
        return pid, "exists in export_1 and not in export_2"
    elif in_second and not in_first:
        return pid, "exists in export_2 and not in export_1"
    elif entities1 != entities2:
        if len(entities1) != len(entities2):
            return pid, "exists in both but different number of EntityIDs"
        return pid, "exists in both but different EntityIDs"
    # Skip the condition where entity IDs are the same in both sets
    return None

# Use ThreadPoolExecutor to parallelize the classification
with ThreadPoolExecutor(max_workers=16) as executor:
    results = list(tqdm(executor.map(classify_persistent_id, all_pids), total=len(all_pids)))

# Filter out None results before creating DataFrame
filtered_results = [result for result in results if result is not None]

# Create DataFrame from the results
differences_df = pd.DataFrame(filtered_results, columns=['persistentId', 'Category'])

# Write the DataFrame to a CSV file
differences_df.to_csv('persistent_id_differences_with_category.csv', index=False)
