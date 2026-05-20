import pandas as pd

def count_unique_persistent_ids_with_single_linkedin_record(file_path):
    # Load the CSV file
    df = pd.read_csv(file_path)
    
    # Filter entries where 'source_dataset_name' is 'linkedin'
    linkedin_entries = df[df['source_dataset_name'].str.lower() == 'linkedin']
    
    # Group by 'persistentId' and count entries
    persistent_count = linkedin_entries.groupby('persistentId').size()
    
    # Filter groups to find those with exactly one record
    single_entry_persistent_ids = persistent_count[persistent_count == 1]
    
    # Count the number of unique persistent IDs with exactly one LinkedIn record
    unique_count = len(single_entry_persistent_ids)
    
    return f'Number of unique PersistentIDs with exactly one LinkedIn record: {unique_count}'

# Run the function using the correct file name
result = count_unique_persistent_ids_with_single_linkedin_record('entity_data.csv')
print(result)
