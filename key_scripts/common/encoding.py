def log_decoding_errors(input_file_path, output_file_path):
    # Open the output file
    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        # Open the input file in binary mode
        with open(input_file_path, 'rb') as file:
            line_number = 1
            for line in file:
                try:
                    # Try to decode each line
                    line.decode('utf-8')
                except UnicodeDecodeError as e:
                    # If there's a decoding error, write details to the output file
                    output_file.write(f"Decoding issue at line {line_number}: {line}\n")
                    output_file.write(f"Error details: {e}\n\n")
                line_number += 1

# Specify the input and output file paths
input_file_path = './files/source40.csv'
output_file_path = 'decoding_errors.txt'

# Execute the function
log_decoding_errors(input_file_path, output_file_path)

print(f"Decoding errors have been logged to {output_file_path}")

