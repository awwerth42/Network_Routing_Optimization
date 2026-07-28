import sys
import os
import pandas as pd

def main():
    # Ensure both arguments are provided
    if len(sys.argv) < 3:
        print("Usage: python process_csv.py <base_name> <num_files>")
        sys.exit(1)

    base_name = sys.argv[1]
    num_files = int(sys.argv[2])

    dataframes = []

    # Read each CSV file
    for i in range(1, num_files + 1):
        filename = f"{base_name}{i}.csv"
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)
        
        # Read file assuming no header row
        df = pd.read_csv(filename, header=None)
        dataframes.append(df)

    # Construct the output DataFrame
    output_df = pd.DataFrame()
    
    # Column 1: Identical to the first input file
    output_df[0] = dataframes[0].iloc[:, 0]

    # Column 2: Mean of corresponding elements from all input files
    second_columns = pd.concat([df.iloc[:, 1] for df in dataframes], axis=1)
    output_df[1] = second_columns.mean(axis=1)

    # Save output to <base_name>_output.csv
    output_filename = f"{base_name}_output.csv"
    output_df.to_csv(output_filename, index=False, header=False)
    
    print(f"Successfully processed {num_files} files into '{output_filename}'.")

if __name__ == "__main__":
    main()
