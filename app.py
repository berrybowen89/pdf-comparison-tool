def extract_structured_data(text):
    """Extract data with proper column structure based on factory spec format"""
    lines = text.split('\n')
    structured_data = []
    current_section = None
    current_item = None
    sub_descriptions = []
    
    def parse_line(line):
        """Parse a line into its component parts based on spec format"""
        parts = {
            'Feature': '',
            'Option': '',
            'Variant': '',
            'Description': '',
            'Quantity': '',
            'Price': ''
        }
        
        # Remove multiple spaces and split line
        line = ' '.join(line.split())
        
        # Extract Option Code (always starts with OP followed by 6 digits)
        option_match = re.search(r'(OP\d{6})', line)
        if option_match:
            parts['Option'] = option_match.group(1)
            line = line.replace(parts['Option'], '').strip()
        
        # Extract Feature (always at start of line, all caps)
        feature_match = re.match(r'^([A-Z][A-Z0-9/\s&]+?)(?=\s|$)', line)
        if feature_match:
            parts['Feature'] = feature_match.group(1).strip()
            line = line[len(parts['Feature']):].strip()
        
        # Extract Quantity (formats like "1 EA", "143 LF", "1,316 SF")
        qty_match = re.search(r'(\d+(?:,\d{3})*\s*(?:EA|LF|SF|D\$))', line)
        if qty_match:
            parts['Quantity'] = qty_match.group(1)
            line = line.replace(parts['Quantity'], '').strip()
        
        # Extract Price (either "Standard" or numeric value)
        price_match = re.search(r'(Standard|-?\d+(?:,\d{3})*\.\d{2})', line)
        if price_match:
            parts['Price'] = price_match.group(1)
            line = line.replace(parts['Price'], '').strip()
        
        # Extract Variant (specific material/color options)
        variants = [
            'Nickel', 'White', 'Brown', 'Matte', 'Expresso', 
            'Toasted Almond', 'Linen Ruffle', 'Dual Black', 'Flint Rock',
            'Chandler Oak'
        ]
        for variant in variants:
            if variant in line:
                parts['Variant'] = variant
                line = line.replace(variant, '').strip()
                break
        
        # Remaining text is Description
        parts['Description'] = line.strip()
        
        return parts
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and headers/footers
        if (not line or 
            "Champion is a registered trademark" in line or
            "Buyer:" in line or 
            "Date:" in line or 
            "Page" in line or
            "Feature Option Variant Description" in line):
            continue
        
        # Identify section headers
        if any(section in line for section in [
            'Construction', 'Exterior', 'Windows', 'Electrical', 'Cabinets', 
            'Kitchen', 'Appliances', 'Interior', 'Plumbing/Heating', 'Primary Bath',
            'Hall Bath', 'Utility Room', 'Floor Covering', 'Countertop'
        ]):
            if current_item and sub_descriptions:
                current_item['Description'] = ' | '.join([current_item['Description']] + sub_descriptions)
            current_section = line.strip()
            sub_descriptions = []
            continue
        
        # Handle sub-descriptions (lines starting with -, ~, etc.)
        if line.strip().startswith(('-', '~', '**', '..')):
            sub_text = line.strip().strip('-~*').strip()
            sub_descriptions.append(sub_text)
            continue
        
        # Skip if line doesn't have enough content
        if len(line.split()) < 2:
            continue
        
        # Parse main content line
        parsed = parse_line(line)
        
        # Only process if we have either a Feature or Option code
        if parsed['Feature'] or parsed['Option']:
            if current_item and sub_descriptions:
                current_item['Description'] = ' | '.join([current_item['Description']] + sub_descriptions)
                sub_descriptions = []
            
            current_item = {
                'Section': current_section or 'Miscellaneous',
                **parsed
            }
            
            # Format quantity if present
            if current_item['Quantity']:
                current_item['Quantity'] = current_item['Quantity'].strip()
            
            # Format price if present
            if current_item['Price']:
                # Convert numeric prices to standard format
                if current_item['Price'] != 'Standard':
                    try:
                        price = float(current_item['Price'].replace(',', ''))
                        current_item['Price'] = f"{price:,.2f}"
                    except ValueError:
                        pass
            
            structured_data.append(current_item)
    
    # Handle any remaining sub-descriptions for last item
    if current_item and sub_descriptions:
        current_item['Description'] = ' | '.join([current_item['Description']] + sub_descriptions)
    
    return structured_data

# Update the display formatting
def format_dataframe(df):
    """Apply consistent formatting to the dataframe"""
    # Ensure columns are in correct order
    column_order = ['Section', 'Feature', 'Option', 'Variant', 'Description', 'Quantity', 'Price']
    df = df[column_order]
    
    # Clean up empty values
    df = df.fillna('')
    
    # Format quantity column
    df['Quantity'] = df['Quantity'].apply(lambda x: str(x).strip())
    
    # Format price column
    def format_price(price):
        if pd.isna(price) or price == '':
            return ''
        if price == 'Standard':
            return price
        try:
            return f"{float(str(price).replace(',', '')):,.2f}"
        except:
            return price
    
    df['Price'] = df['Price'].apply(format_price)
    
    return df

# Update Streamlit display
def display_results(results_df):
    """Display results with proper formatting"""
    formatted_df = format_dataframe(results_df)
    
    st.dataframe(
        formatted_df,
        column_config={
            "Section": st.column_config.TextColumn("Section", width=120),
            "Feature": st.column_config.TextColumn("Feature", width=150),
            "Option": st.column_config.TextColumn("Option Code", width=100),
            "Variant": st.column_config.TextColumn("Variant", width=100),
            "Description": st.column_config.TextColumn("Description", width=400),
            "Quantity": st.column_config.TextColumn("Qty", width=80),
            "Price": st.column_config.TextColumn("Price", width=100)
        },
        use_container_width=True,
        hide_index=True
    )
