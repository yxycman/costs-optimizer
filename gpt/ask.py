#!/usr/bin/env python3

import os
import google.generativeai as genai


def query_gpt(service, table_head, tabulated_data):
    """
    Query GPT
    """
    print("Querying the GEMINI 1.5 FLASH")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    request = f"provide only cost optimization suggestions for AWS {service} service using {table_head} as column names and {tabulated_data} as table data"
    response = model.generate_content(request)
    print(response.text)
