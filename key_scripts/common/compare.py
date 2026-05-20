def find_decoding_issues(file_path, output_path):
    with open(file_path, 'rb') as file:
        lines = file.readlines()

    with open(output_path, 'w', encoding='utf-8') as output_file:
        for i, line in enumerate(lines):
            try:
                line.decode('utf-8')
            except UnicodeDecodeError as e:
                output_file.write(f"Decoding issue at line {i+1}: {line.strip()}\n")
                output_file.write(f"Error: {e}\n\n")

# Paths to the files to check
file1_path = './files/source40.csv'
#file2_path = 'file2.txt'
output_path = 'decoding_issues.txt'

find_decoding_issues(file1_path, output_path)
#find_decoding_issues(file2_path, output_path)

print(f"Decoding issues have been written to {output_path}")
