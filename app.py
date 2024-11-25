def compare_quotes(quote1_data, quote2_data):
    comparison_prompt = f"""
    Thoroughly compare the attached sales quotes, analyzing both text and tables. Generate a structured JSON response with these sections:

    1. Summary: Key insights and differences between the quotes
    2. LineItemComparison: Markdown table comparing each line item 
       Columns: 
       - LineItem: Description of item
       - Quote1Value: Value from Quote 1 (numeric where applicable)  
       - Quote2Value: Value from Quote 2 (numeric where applicable)
       - MatchStatus: Exact match (✓), Partial match (~), Only in Quote 1 ([1]), Only in Quote 2 ([2]) 
       - Difference: Difference between Quote1Value and Quote2Value (blank if n/a)
    3. TableComparison: Insights from comparing any tables
    4. UniqueItems: List items unique to each quote
    5. Statistics:
       - TotalItems: Total line items compared  
       - ExactMatches: Number of exact matches
       - PartialMatches: Number of partial or fuzzy matches
       - ItemsOnlyQuote1: Number of items only in Quote 1
       - ItemsOnlyQuote2: Number of items only in Quote 2

    Quote 1: {quote1_data}
    Quote 2: {quote2_data}
    """
    
    response = st.session_state.anthropic_client.messages.create(
        model="claude-3-opus-20240229", 
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": comparison_prompt
        }]
    )
    
    return response.content[0].text

# In your existing code, replace the comparison logic with:
if st.button("Compare Quotes") and st.session_state.quote1 and st.session_state.quote2:
    # ...
    try:  
        # ...
        comparison_result = compare_quotes(st.session_state.quote1['content'], st.session_state.quote2['content'])
        comparison_json = json.loads(comparison_result)
        
        # Display results
        st.markdown("### Comparison Summary")
        st.markdown(comparison_json['Summary']) 
        
        st.markdown("### Line Item Comparison")
        st.markdown(comparison_json['LineItemComparison'])
        
        if comparison_json['TableComparison']:
            st.markdown("### Table Comparison")
            st.markdown(comparison_json['TableComparison'])
        
        st.markdown("### Unique Items")
        st.markdown(comparison_json['UniqueItems'])
        
        st.markdown("### Comparison Statistics")
        st.json(comparison_json['Statistics'])
        
        # ...
    except Exception as e:
        # ...
