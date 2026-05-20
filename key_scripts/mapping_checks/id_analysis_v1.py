import pandas as pd

def export_aggregated_data(input_csv, output_csv, group_by_col, agg_col, pivot_col):
    """
    This function reads a csv file, groups, aggregates, and pivots the data, 
    and then exports the results to a new csv file.
    
    :param input_csv: str, path to the input csv file
    :param output_csv: str, path to the output csv file
    :param group_by_col: str, name of the column to group by
    :param agg_col: str, name of the column to aggregate
    :param pivot_col: str, name of the column to pivot
    
    :return: None
    """
    # Read the data from the input CSV file
    data = pd.read_csv(input_csv)
    
    # Group by 'group_by_col' and 'pivot_col' and count distinct 'agg_col'
    result = data.groupby([group_by_col, pivot_col])[agg_col].nunique().reset_index(name=f'distinct_{agg_col}_count')
    
    # Pivot the table
    pivot_result = result.pivot_table(index=group_by_col, columns=pivot_col, values=f'distinct_{agg_col}_count', fill_value=0).reset_index()
    
    # Export the results to a new CSV file
    pivot_result.to_csv(output_csv, index=False)
    print(f"Results exported to {output_csv}")

# Example usage:
export_aggregated_data('./data/entity_cluster_details.csv', 'output_grouping.csv', 'persistentId', 'trusted_id', 'SOURCE_NAME')
