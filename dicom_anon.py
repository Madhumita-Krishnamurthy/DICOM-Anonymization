#importing libraries
import zipfile
import os
import pydicom
import pandas as pd
import shutil
import re
from io import BytesIO
from pydicom.tag import Tag
from pydicom.uid import generate_uid
from pydicom.datadict import dictionary_VR

'''
1. Opening the files in the given folder
2. Copying the files in new folder "updated_dcm_files"
3. Adding the patient names as the file name without extension (Eg: Test1)
'''

# Define base path
base_folder = 'F:/set2_anon'

# Remove base folder if it exists
if os.path.exists(base_folder):
    shutil.rmtree(base_folder)

# Recreate the base folder and output subfolder
os.makedirs(os.path.join(base_folder, 'updated_dcm_files'), exist_ok=True)

# Now define paths
source_folder = 'F:/set2_a'
output_folder = os.path.join(base_folder, 'updated_dcm_files')

os.makedirs(output_folder, exist_ok=True) # Create output directory if it doesn't exist

# Loop through each file in the source folder
for filename in os.listdir(source_folder):
    if filename.endswith('.dcm'):
        # Full path of the source and destination file
        src_path = os.path.join(source_folder, filename)
        dst_path = os.path.join(output_folder, filename)

        # Copy and rename the file
        shutil.copyfile(src_path, dst_path)

        # Read the copied DICOM file
        ds = pydicom.dcmread(dst_path)

        # Set PatientID to the new filename (without .dcm extension)
        patient_id = os.path.splitext(filename)[0]
        ds.PatientID = patient_id

        # Overwrite the file with updated PatientID
        ds.save_as(dst_path)

print("All DICOM files renamed, copied, and updated with new PatientID in:", output_folder)

'''
1. Open the "updated_dcm_files" folder and check the number of files present.
2. Open a new excel file and generate unique_id for that many number of files with a prefix starting from NIRT_DS01_00001 in increasing order.
3. Now, the excel sheet must have three columns in total, namely,
   a.original_file_name, b.original_patient_id, c. unique_id
'''

def extract_number(filename):
    match = re.search(r'\d+', filename)
    return int(match.group()) if match else -1

# List and sort DICOM files
files = sorted(
    [f for f in os.listdir(output_folder) if f.endswith('.dcm')],
    key=extract_number
)

# Generate patient_ids (your custom IDs)
patient_ids = [f"NIRT_DS01_{i:05d}" for i in range(1, len(files) + 1)]

# Extract PatientID from DICOM metadata
unique_ids = []
for f in files:
    dcm_path = os.path.join(output_folder, f)
    try:
        ds = pydicom.dcmread(dcm_path, stop_before_pixels=True)
        unique_ids.append(ds.PatientID if 'PatientID' in ds else "Unknown")
    except Exception as e:
        print(f"Failed to read {f}: {e}")
        unique_ids.append("ReadError")

# Create DataFrame
df = pd.DataFrame({
    "original_file_name": files,
    "original_patient_id": unique_ids,
    "unique_id": patient_ids
})

# Save to Excel
excel_path = 'F:/set2_anon/patient_ids.csv'
df.to_csv(excel_path, index=False)

print(f"Excel file saved at {excel_path}")


#Rename the file name and patient_id of the DICOM file as in the unique_id in the .csv file

# Load the CSV
csv_path = 'F:/set2_anon/patient_ids.csv'
df = pd.read_csv(csv_path)

# Loop through each row to update PatientID and rename file
for index, row in df.iterrows():
    old_filename = row['original_file_name']       # Original filename
    new_patient_id = row['unique_id']     # New PatientID and new filename (without .dcm)
    new_filename = new_patient_id + '.dcm'

    old_path = os.path.join(output_folder, old_filename)
    new_path = os.path.join(output_folder, new_filename)

    if os.path.exists(old_path):
        try:
            # Read the DICOM file
            ds = pydicom.dcmread(old_path)

            # Update PatientID
            ds.PatientID = new_patient_id

            # Save the file with the new name (overwrite if needed)
            ds.save_as(new_path)

            # Remove old file if the filename has changed
            if old_path != new_path:
                os.remove(old_path)

            print(f"Updated and renamed: {old_filename} -> {new_filename}")

        except Exception as e:
            print(f"Error updating {old_filename}: {e}")
    else:
        print(f"File not found: {old_filename}")


#Anonymize the files by removing the metadata
# Tags required for display
REQUIRED_TAGS = {
    Tag(0x7FE0, 0x0010),  # Pixel Data
    Tag(0x0028, 0x0010),  # Rows
    Tag(0x0028, 0x0011),  # Columns
    Tag(0x0028, 0x0100),  # Bits Allocated
    Tag(0x0028, 0x0101),  # Bits StoredS
    Tag(0x0028, 0x0102),  # High Bit
    Tag(0x0028, 0x0103),  # Pixel Representation
    Tag(0x0028, 0x0004),  # Photometric Interpretation
    Tag(0x0028, 0x0002),  # Samples per Pixel
    Tag(0x0008, 0x0016),  # SOP Class UID
    Tag(0x0002, 0x0010),  # Transfer Syntax UID (file_meta)
}

# Blank value generator
def blank_value(vr):
    return {
        'SQ': pydicom.sequence.Sequence(),
        'OB': b'', 'OW': b'', 'OF': b'', 'UN': b'',
        'US': 0, 'SS': 0, 'UL': 0, 'SL': 0, 'FL': 0, 'FD': 0,'UI': ''
    }.get(vr, '')

# Anonymize and retain only essential tags
def anonymize(filepath, outpath):
    ds = pydicom.dcmread(filepath)

    for elem in ds.iterall():
        if elem.tag not in REQUIRED_TAGS:
            elem.value = blank_value(elem.VR)

    if hasattr(ds, "file_meta"):
        for elem in ds.file_meta:
            if elem.tag not in REQUIRED_TAGS:
                elem.value = blank_value(elem.VR)

    ds.save_as(outpath)

# Process all DICOMs in a folder
def process_folder(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(input_dir):
        if f.lower().endswith(".dcm"):
            input_path = os.path.join(input_dir, f)
            output_path = os.path.join(output_dir, f)
            anonymize(input_path, output_path)
            print(f"Anonymized: {f}")

# === Set your paths here ===
anon_output_folder = os.path.join(base_folder, 'anon_dcm_files')
process_folder(output_folder, anon_output_folder)