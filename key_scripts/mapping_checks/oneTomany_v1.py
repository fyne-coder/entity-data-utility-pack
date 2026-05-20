import pandas as pd

def check_multiple_mappings(filename, field_a, field_b):
    # Load data
    data = pd.read_csv(filename)

    # Group by Field A and count unique values in Field B
    mapping_counts = data.groupby(field_a)[field_b].nunique()

    # Filter Field A values that map to multiple unique Field B values
    multiple_mappings = mapping_counts[mapping_counts > 1]

    # Print results
    if len(multiple_mappings) > 0:
        print(f"Values in '{field_a}' that map to multiple values in '{field_b}':")
        for index, count in multiple_mappings.items():
            print(f"'{index}' maps to {count} unique values in '{field_b}'")
    else:
        print(f"No values in '{field_a}' map to multiple values in '{field_b}'.")

if __name__ == "__main__":
    filename = input("Enter the file name: ")
    field_a = input("Enter Field A: ")
    field_b = input("Enter Field B: ")

    check_multiple_mappings(filename, field_a, field_b)
