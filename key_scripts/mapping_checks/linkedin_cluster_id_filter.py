import pandas as pd

def export_filtered_persistent_ids(file_path):
    # Load the CSV file
    df = pd.read_csv(file_path)
    
    # Filter out entries without a LinkedIn URL or with empty LinkedIn URLs
    df_filtered = df[df['LinkedIn_URL'].notna() & (df['LinkedIn_URL'] != '')]
    
    # Group by 'persistentId' and collect all unique 'suggestedClusterId'
    group_by_persistent = df_filtered.groupby('persistentId')['suggestedClusterId'].nunique()
    
    # Identify persistent IDs with more than one unique 'suggestedClusterId'
    persistent_ids_with_varied_suggested = group_by_persistent[group_by_persistent > 1].index
    
    # Filter to get rows with these persistent IDs
    filtered_entries = df[df['persistentId'].isin(persistent_ids_with_varied_suggested)]
    
    # Apply additional filter where 'source_dataset_name' is 'linkedin' and 'suggestedClusterId' equals 'persistentId'
    linkedin_entries = filtered_entries[
        (filtered_entries['source_dataset_name'].str.lower() == 'linkedin') &
        (filtered_entries['suggestedClusterId'] == filtered_entries['persistentId'])
    ]
    
    # Get unique persistent IDs that meet the criteria
    final_persistent_ids = linkedin_entries['persistentId'].unique()
    
    # Export these persistent IDs to a CSV file
    pd.Series(final_persistent_ids).to_csv('final_unique_persistentIDs.csv', index=False, header=['PersistentID'])
    
    return 'Exported final unique PersistentIDs to final_unique_persistentIDs.csv'

# Run the function using the correct file name
result = export_filtered_persistent_ids('entity_data.csv')
