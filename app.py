import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
from rapidfuzz import fuzz
import numpy as np
from io import BytesIO
import re

def process_sub_descriptions(main_desc, sub_descs):
    """Combine main description with sub-descriptions in a clean format"""
    if not sub_descs:
        return main_desc
    
    # Clean up sub-descriptions and combine with main description
    clean_subs = [sub.strip().strip('-~*').strip() for sub in sub_descs]
    full_desc = [main_desc] + clean_subs if main_desc else clean_subs
    return ' | '.join(filter(None, full_desc))

def extract_structured_data(text):
    """Extract data with properly formatted descriptions"""
    lines = text.split('\n')
    structured_data = []
    current_section = None
    current_item = None
    sub_descriptions = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and headers/footers
        if (not line or 
            "Champion is a registered trademark" in line or
            "Buyer:" in line or 
            "Date:" in line or 
            "Page" in line):
            continue
            
        # Check for section headers
        if any(section in line for section in [
            'Construction', 'Exterior', 'Windows', 'Electrical', 'Cabinets', 
            'Kitchen', 'Appliances', 'Interior', 'Plumbing/Heating', 'Primary Bath',
            'Hall Bath', 'Utility Room', 'Floor Covering', 'Countertop'
        ]):
            # Save previous item if exists
            if current_item:
                current_item['Description'] = process_sub_descriptions(
                    current_item['Description'], sub_descriptions
                )
                structured_data.append(current_item)
                current_item = None
                sub_descriptions = []
            
            current_section = line.strip()
            continue
        
        # Check if line is a sub-description
        if line.strip().startswith(('-', '~', '**', '..')):
            if current_item:
                sub_descriptions.append(line)
            continue
        
        # Skip header rows
        if "Feature" in line and "Option" in line:
            continue
        
        # Try to extract main item data
        feature_match = re.match(r'^([A-Z][A-Z0-9/\s]+(?:\s*&\s*[A-Z]+)*)', line)
        option_match = re.search(r'(OP\d{6})', line)
        
        if feature_match:
            # Save previous item if exists
            if current_item:
                current_item['Description'] = process_sub_descriptions(
                    current_item['Description'], sub_descriptions
                )
                structured_data.append(current_item)
            
            # Reset for new item
            sub_descriptions = []
            feature = feature_match.group(1).strip()
            
            # Initialize new item
            current_item = {
                'Section': current_section or 'Miscellaneous',
                'Feature': feature,
                'Option': '',
                'Variant': '',
                'Description': '',
                'Quantity': '',
                'Price': ''
            }
            
            # Extract option code
            if option_match:
                current_item['Option'] = option_match.group(1)
                line = line.replace(current_item['Option'], '')
            
            # Extract quantity
            qty_match = re.search(r'(\d+\s*(?:EA|LF|SF|D\$))', line)
            if qty_match:
                current_item['Quantity'] = qty_match.group(1).strip()
                line = line.replace(qty_match.group(1), '')
            
            # Extract price
            price_match = re.search(r'(Standard|\d+\.\d{2}|-?\d+,\d+\.\d{2})', line)
            if price_match:
                current_item['Price'] = price_match.group(1).strip()
                line = line.replace(price_match.group(1), '')
            
            # Extract variant
            variants = ['Nickel', 'White', 'Brown', 'Matte', 'Expresso', 
                       'Toasted Almond', 'Linen Ruffle', 'Dual Black', 'Flint Rock',
                       'Chandler Oak']
            for variant in variants:
                if variant in line:
                    current_item['Variant'] = variant
                    line = line.replace(variant, '')
                    break
            
            # Clean up description
            description = ' '.join(line.split())
            description = re.sub(r'\s+', ' ', description).strip()
            description = re.sub(r'^[^a-zA-Z0-9]*|[^a-zA-Z0-9]*$', '', description)
            
            if description and not description.isspace():
                current_item['Description'] = description
    
    # Add last item if exists
    if current_item:
        current_item['Description'] = process_sub_descriptions(
            current_item['Description'], sub_descriptions
        )
        structured_data.append(current_item)
    
    return structured_data

# Streamlit UI and remaining code stays the same...
