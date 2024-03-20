import pymysql
import pymysql.cursors
import json
import easyocr
import re
import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import io
#import os
#os.environ["GIT_PYTHON_REFRESH"] = "quiet"
import PIL
from PIL import Image
import numpy as np
import cv2
import toml


#-----------------------------------Read and Display Uploaded BizCard---------------------------------------------------

def extract_information(image_bytes):
    reader = easyocr.Reader(['en'])
    image = Image.open(image_bytes)
    np_image = np.array(image)
    # Numpy array image
    results = reader.readtext(np_image, detail=0)

    # Join all recognized text strings into a single string separated by new lines
    all_text = "\n".join(results)
    st.text(all_text)

    extracted_info = {
        "Company Name": "",
        "Card Holder Name": "",
        "Designation": "",
        "Mobile Number": "",
        "Email Address": "",
        "Website URL": "",
        "Area": "",
        "City": "",
        "State": "",
        "Pin Code": ""
    }
    for i, line in enumerate(results):

        if i == 0:
            extracted_info["Card Holder Name"] = line.strip()
        elif i == 1:
            extracted_info["Designation"] = line.strip()
        elif "@" in line and ".com" in line:
            extracted_info["Email Address"] = line.strip()
        elif line.endswith(".com") or line.startswith("www"):
            extracted_info["Website URL"] = line.strip()
        if "TamilNadu" or "TamiINadu" in line:
            extracted_info["State"] = "TamilNadu"
        pin_code_search = re.search(r'6\d{5}', line)
        if pin_code_search:
            extracted_info["Pin Code"] = pin_code_search.group()
        if ',' in line:
            area_city_line = line.replace('TamilNadu', '').strip()
            area_city = area_city_line.split(',')
            if len(area_city) == 2:
                extracted_info["Area"], extracted_info["City"] = area_city[0].strip(), area_city[1].strip()
        only_digits = re.sub(r'\D', '', line)
        if len(only_digits) == 10: #Mobile phone format
            if not extracted_info["Mobile Number"]:
                extracted_info["Mobile Number"] = only_digits
        if results:
            extracted_info["Company Name"] = results[-1].strip()

    return extracted_info

#-----------------------------------Move BiZCard Data to SQL and Update-------------------------------------------------
# Connect to the database
cnx = pymysql.connect(user='root',
                      password='Password',
                      host='127.0.0.1',
                      database='bizCard_db')
cursor = cnx.cursor()

# # SQL command to create the table if it doesn't exist
# create_table_command = """
# CREATE TABLE IF NOT EXISTS BizCards (
#     CompanyName VARCHAR(255),
#     CardHolderName VARCHAR(255),
#     Designation VARCHAR(255),
#     MobileNumber VARCHAR(255),
#     EmailAddress VARCHAR(255) NOT NULL,
#     WebsiteURL VARCHAR(255),
#     Area VARCHAR(255),
#     City VARCHAR(255),
#     State VARCHAR(255),
#     PinCode VARCHAR(255),
#     PRIMARY KEY (`EmailAddress`)
# );
# """
#
# # Executing the command
# cursor.execute(create_table_command)
# cnx.commit()
# # Close the cursor and connection when done
# cursor.close()
# cnx.close()
#-----------------------------------Insert data to SQL table------------------------------------------------------------
def insert_bizcard(info):
    try:
        sql = '''
        INSERT INTO BizCards (CompanyName, CardHolderName, Designation, MobileNumber, EmailAddress, WebsiteURL, Area, City, State, PinCode)
        VALUES (%(CompanyName)s, %(CardHolderName)s, %(Designation)s, %(MobileNumber)s, %(EmailAddress)s, %(WebsiteURL)s, %(Area)s, %(City)s, %(State)s, %(PinCode)s);
        '''
        cursor.execute(sql, info)
        cnx.commit()
    except pymysql.err.IntegrityError:
        st.write("Record with this Email Address already exists.")
    finally:
        cursor.close()
        cnx.close()
#-----------------------------------Update data to SQL table------------------------------------------------------------
def update_bizcard(info):
    sql = '''
    UPDATE BizCards
    SET CompanyName = %(CompanyName)s,
        CardHolderName = %(CardHolderName)s,
        Designation = %(Designation)s,
        MobileNumber = %(MobileNumber)s,
        WebsiteURL = %(WebsiteURL)s,
        Area = %(Area)s,
        City = %(City)s,
        State = %(State)s,
        PinCode = %(PinCode)s
    WHERE EmailAddress = %(EmailAddress)s;
    '''
    cursor.execute(sql, info)
    cnx.commit()
    cursor.close()
#-----------------------------------Delete data to SQL table------------------------------------------------------------
def delete_bizcard(email_address):
    sql = "DELETE FROM BizCards WHERE EmailAddress = %s;"
    cursor.execute(sql, (email_address,))
    cnx.commit()
    cursor.close()

#-----------------------------------User Upload BizCard-----------------------------------------------------------------
st.set_page_config(layout='wide')
st.title("BizCardX: Extracting Business Card Data with OCR - Palaniappan Kannan")

# Create two columns in Streamlit UI
col1, col2 = st.columns(2)
# Initialize extracted_info with default values
extracted_info = {
    "Company Name": "",
    "Card Holder Name": "",
    "Designation": "",
    "Mobile Number": "",
    "Email Address": "",
    "Website URL": "",
    "Area": "",
    "City": "",
    "State": "",
    "Pin Code": ""
}
# Users to upload business card
with col1:
    st.header("Upload your business card")
    uploaded_file = st.file_uploader("Choose a business card image file", type=['png', 'jpg'])

    # Display the uploaded image
    if uploaded_file is not None:
        image_bytes = io.BytesIO(uploaded_file.read())
        image = Image.open(image_bytes)
        st.image(image, caption='Uploaded Business Card', use_column_width=True)

        # Update extracted_info with extracted data
        extracted_info.update(extract_information(image_bytes))

        # Display extracted data
        st.write("Extracted Information:")
        for key, value in extracted_info.items():
            st.text(f"{key}: {value}")

with col2:
    st.header("Edit Business Card Information")

    editable_info = {
        "CompanyName": st.text_input("Company Name", value=extracted_info.get("Company Name", "")),
        "CardHolderName": st.text_input("Card Holder Name", value=extracted_info.get("Card Holder Name", "")),
        "Designation": st.text_input("Designation", value=extracted_info.get("Designation", "")),
        "MobileNumber": st.text_input("Mobile Number", value=extracted_info.get("Mobile Number", "")),
        "EmailAddress": st.text_input("Email Address", value=extracted_info.get("Email Address", ""), disabled=True),
        "WebsiteURL": st.text_input("Website URL", value=extracted_info.get("Website URL", "")),
        "Area": st.text_input("Area", value=extracted_info.get("Area", "")),
        "City": st.text_input("City", value=extracted_info.get("City", "")),
        "State": st.text_input("State", value=extracted_info.get("State", "")),
        "PinCode": st.text_input("Pin Code", value=extracted_info.get("Pin Code", ""))
    }

    # Create a new row of columns for the buttons inside col2
    button_col1, button_col2, button_col3 = st.columns(3)

    with button_col1:
        if st.button('Insert Data'):
            insert_bizcard(editable_info)
            st.success("Data inserted successfully.")

    with button_col2:
        if st.button('Update Data'):
            update_bizcard(editable_info)
            st.success("Data updated successfully.")

    with button_col3:
        if st.button('Delete Record'):
            delete_bizcard(editable_info["EmailAddress"])
            st.success("Record deleted successfully.")


