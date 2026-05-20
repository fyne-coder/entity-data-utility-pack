import glob
import pandas as pd
import logging
import io

# Set up logging
logging.basicConfig(filename='./combine.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def find_error_line(file_path, error_position):
    with open(file_path, 'rb') as file:
        byte_count = 0
        line_number = 0
        while byte_count <= error_position:
            line = file.readline()
            line_number += 1
            byte_count += len(line)
    return line_number

path = './files'
csv_files = glob.glob(path + "/*.csv")

dfs = []
chunk_size = 1000  # Number of lines per chunk

logging.info("Starting the CSV concatenation process.")

for file in csv_files:
    try:
        logging.info(f"Processing file: {file}")
        df = pd.read_csv(file, quotechar='"', escapechar='\\')
        dfs.append(df)
    except UnicodeDecodeError as e:
        error_position = int(str(e).split('position')[1].split(':')[0].strip())  # Extract the position of the error
        line_number = find_error_line(file, error_position)
        logging.error(f"Unicode decode error in file: {file} around line {line_number}. Error: {e}.")
        try:
            df = pd.read_csv(file, quotechar='"', escapechar='\\', encoding='latin1')  # Trying a different encoding
            dfs.append(df)
        except Exception as e:
            logging.error(f"Failed to read file: {file} with alternate encoding. Error: {e}")
    except pd.errors.ParserError as e:
        logging.warning(f"Parser error in file: {file}. Error: {e}. Attempting chunk-wise reading.")
        with open(file, 'r') as f:
            lines = f.readlines()
            header = lines[0]
            for idx in range(1, len(lines), chunk_size):
                chunk = lines[idx:idx+chunk_size]
                try:
                    temp_df = pd.read_csv(io.StringIO(header + '\n'.join(chunk)), quotechar='"', escapechar='\\')
                    dfs.append(temp_df)
                except pd.errors.ParserError as e:
                    logging.warning(f"Error in file: {file} in chunk starting at line {idx}. Error: {e}. Attempting line-by-line parsing.")
                    for line_idx, line in enumerate(chunk, start=1):
                        try:
                            temp_df = pd.read_csv(io.StringIO(header + line), quotechar='"', escapechar='\\')
                            dfs.append(temp_df)
                        except pd.errors.ParserError:
                            logging.error(f"Error in file: {file} on line {line_idx}. Skipping this line.")

# Extract filename of the first CSV without extension and append '_updated'
output_filename = csv_files[0].split('/')[-1].rsplit('.', 1)[0] + '_updated.csv'

# Concatenate and write the dataframes to a new CSV, excluding problematic lines
if dfs:
    big_df = pd.concat(dfs, ignore_index=True)
    big_df.to_csv(output_filename, index=False)
    logging.info(f"Successfully concatenated and saved the cleaned CSV file as {output_filename}.")
else:
    logging.warning("No valid dataframes to concatenate.")

logging.info("CSV concatenation process completed.")
